"""Deterministic, SQLite-backed depot and handler dispatch engine."""

import re
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import text

from app.extensions import db
from app.models import Assignment, Depot, Handler, QueueEntry, Report, RoutingDecision
from services.queue_service import QueueService

from .priority import PRIORITY_RANK, determine_priority
from .routing_table import DEPOTS, get_route_distances, sorted_depots

# Compatibility export for Phase 3 callers.
DispatchAudit = RoutingDecision


class DispatchEngine:
    """Assign validated reports to the nearest eligible depot and handler."""

    def __init__(self, queue_service: QueueService | None = None):
        self.queue_service = queue_service or QueueService()

    def initialize(self) -> None:
        """Create dispatch tables and seed the deterministic depot roster."""
        db.create_all()
        if Depot.query.count() == 0:
            db.session.add_all(
                [
                    Depot(depot_id=depot.depot_id, name=depot.name, capacity=depot.capacity)
                    for depot in DEPOTS
                ]
            )
        if Handler.query.count() == 0:
            db.session.add_all(
                [
                    Handler(
                        handler_id=handler_id,
                        name=name,
                        depot_id=depot_id,
                        assigned_categories=categories,
                        maximum_capacity=capacity,
                        current_workload=0,
                        available=True,
                    )
                    for handler_id, name, depot_id, categories, capacity in [
                        ("H01", "Anita Rao", "D01", ["Mechanical", "Tyre"], 3),
                        ("H02", "Bharat Kumar", "D01", ["Accident", "Electrical"], 2),
                        ("H03", "Chitra Das", "D02", ["Mechanical", "Fuel"], 3),
                        ("H04", "Dev Shah", "D02", ["Tyre", "Electrical"], 2),
                        ("H05", "Esha Nair", "D03", ["Accident", "Fuel"], 2),
                        ("H06", "Farhan Ali", "D03", ["Mechanical", "Electrical"], 2),
                        ("H07", "Gita Menon", "D04", ["Tyre", "Fuel"], 2),
                        ("H08", "Hari Singh", "D04", ["Accident", "Electrical"], 2),
                        ("H09", "Isha Jain", "D05", ["Mechanical", "Tyre", "Fuel"], 3),
                        ("H10", "Jai Patel", "D05", ["Accident", "Electrical"], 3),
                    ]
                ]
            )
        db.session.commit()

    def dispatch_report(self, report: dict) -> dict:
        """Dispatch one validated report, or place it in a deterministic queue."""
        self.initialize()
        self._validate_report_input(report)
        report_id = str(report.get("report_id") or uuid4())
        submission_time = self._submission_time(report)
        priority_result = determine_priority(
            report["category"],
            emergency=bool(report.get("emergency", False)),
            severe_accident=bool(report.get("severe_accident", False)),
            dangerous_electrical_fault=bool(
                report.get("dangerous_electrical_fault", False)
            ),
        )
        route_key = report["identifier"][13]
        distances = get_route_distances(route_key)

        if not db.session().in_transaction():
            db.session.connection().execute(text("BEGIN IMMEDIATE"))
        existing = RoutingDecision.query.filter_by(report_id=report_id).first()
        if existing is not None:
            raise ValueError(f"Report {report_id} already has an active assignment.")

        if distances is None:
            result = self._queue_report(
                report,
                report_id,
                route_key,
                {},
                priority_result,
                submission_time,
                "correction_queue",
                "Unknown route key; sent to central correction queue.",
            )
        else:
            result = self._assign_or_queue(
                report, report_id, route_key, distances, priority_result, submission_time
            )
        db.session.flush()
        return result

    def retry_assignment(self, report: Report) -> dict:
        """Retry a queued accepted report after capacity or availability changes."""
        self.initialize()
        db.session.rollback()
        db.session.connection().execute(text("BEGIN IMMEDIATE"))
        report = db.session.get(Report, report.report_id)
        if report.validation_status != "accepted":
            raise ValueError("Rejected reports cannot be assigned.")
        existing = RoutingDecision.query.filter_by(report_id=report.report_id).first()
        if existing is None:
            raise ValueError(f"Report {report.report_id} has no routing decision to retry.")
        if existing.assignment_status == "assigned":
            raise ValueError(f"Report {report.report_id} already has an active assignment.")
        queue_entry = QueueEntry.query.filter_by(report_id=report.report_id).first()
        if queue_entry is not None:
            db.session.delete(queue_entry)
        db.session.delete(existing)
        db.session.flush()
        return self.dispatch_report(
            {
                "report_id": report.report_id,
                "identifier": report.identifier,
                "category": report.classification_category,
                "validated": True,
                "emergency": report.emergency,
                "severe_accident": report.severe_accident,
                "dangerous_electrical_fault": report.dangerous_electrical_fault,
                "submission_timestamp": report.submission_timestamp,
            }
        )

    def _assign_or_queue(self, report, report_id, route_key, distances, priority_result, submission_time):
        for depot, _distance in sorted_depots(route_key):
            eligible = (
                Handler.query.filter_by(depot_id=depot.depot_id, available=True)
                .order_by(Handler.handler_id)
                .all()
            )
            depot_load = Assignment.query.filter_by(
                depot_id=depot.depot_id, status="assigned"
            ).count()
            if depot_load >= depot.capacity:
                continue
            handler = next(
                (
                    candidate
                    for candidate in eligible
                    if report["category"] in (candidate.assigned_categories or [])
                    and candidate.current_workload < candidate.maximum_capacity
                ),
                None,
            )
            if handler is None:
                continue
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            handler.current_workload += 1
            decision = self._decision(
                report, report_id, route_key, distances, priority_result,
                submission_time, "assigned", depot.depot_id, handler.handler_id,
                priority_result["reason"],
            )
            db.session.add(decision)
            db.session.add(
                Assignment(
                    report_id=report_id,
                    depot_id=depot.depot_id,
                    handler_id=handler.handler_id,
                    status="assigned",
                    assigned_at=now,
                    reason=priority_result["reason"],
                )
            )
            return self._result(decision, distances, priority_result["reason"])

        return self._queue_report(
            report,
            report_id,
            route_key,
            distances,
            priority_result,
            submission_time,
            "waiting",
            "All eligible depots or handlers are unavailable/full; escalated to waiting queue.",
        )

    def _queue_report(
        self, report, report_id, route_key, distances, priority_result, submission_time, status, reason
    ):
        decision = self._decision(
            report, report_id, route_key, distances, priority_result,
            submission_time, status, None, None, f"{priority_result['reason']} {reason}",
        )
        db.session.add(decision)
        self.queue_service.enqueue(
            report_id,
            priority_result["priority"],
            PRIORITY_RANK[priority_result["priority"]],
            reason,
            submission_time,
            status=status,
        )
        return self._result(decision, distances, decision.reason)

    @staticmethod
    def _decision(
        report, report_id, route_key, distances, priority_result, submission_time,
        status, depot_id, handler_id, reason
    ):
        return RoutingDecision(
            report_id=report_id,
            identifier=report["identifier"],
            route_key=route_key,
            distance_lookup=distances,
            selected_depot_id=depot_id,
            selected_handler_id=handler_id,
            priority=priority_result["priority"],
            assignment_timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
            submission_timestamp=submission_time,
            assignment_status=status,
            reason=reason,
        )

    @staticmethod
    def _result(decision, distances, reason):
        return {
            "report_id": decision.report_id,
            "route_key": decision.route_key,
            "distance_lookup": distances,
            "selected_depot": decision.selected_depot_id,
            "selected_handler": decision.selected_handler_id,
            "priority": decision.priority,
            "assignment_timestamp": decision.assignment_timestamp.isoformat(),
            "assignment_status": decision.assignment_status,
            "reason": reason,
        }

    @staticmethod
    def _submission_time(report):
        value = report.get("submission_timestamp")
        if isinstance(value, datetime):
            return value.replace(tzinfo=None)
        return datetime.now(timezone.utc).replace(tzinfo=None)

    @staticmethod
    def _validate_report_input(report):
        if not isinstance(report, dict):
            raise ValueError("Report must be a dictionary.")
        if not report.get("validated") and not (
            isinstance(report.get("validation"), dict)
            and report["validation"].get("accepted") is True
        ):
            raise ValueError("Dispatch accepts only a validated report.")
        if not isinstance(report.get("identifier"), str) or not re.fullmatch(
            r"BUS[0-9]{4}-ROUTE[A-Z][0-9]{2}", report["identifier"]
        ):
            raise ValueError("Validated report has an invalid bus identifier.")
        if report.get("category") not in {
            "Mechanical", "Tyre", "Accident", "Fuel", "Electrical"
        }:
            raise ValueError("Validated report has an unsupported category.")
