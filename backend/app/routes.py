"""Flask API routes for reports, dispatch, and operational analytics."""

from datetime import datetime, timezone
from uuid import uuid4

from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

from automata.classifier import classify_issue
from automata.regex_validator import compare_validators
from dispatch.dispatch_engine import DispatchEngine
from dispatch.priority import determine_priority
from dispatch.routing_table import DEPOTS, DISTANCE_TABLE

from .extensions import db
from .models import (
    Assignment,
    Depot,
    Handler,
    Report,
    RoutingDecision,
    StatusHistory,
)


api = Blueprint("api", __name__)
engine = DispatchEngine()


def _iso(value):
    return value.isoformat() if value else None


def _report_json(report):
    return {
        "report_id": report.report_id,
        "reporter_details": report.reporter_details,
        "identifier": report.identifier,
        "issue_code": report.issue_code,
        "description": report.description,
        "emergency": report.emergency,
        "severe_accident": report.severe_accident,
        "dangerous_electrical_fault": report.dangerous_electrical_fault,
        "dfa_valid": report.dfa_valid,
        "regex_valid": report.regex_valid,
        "validators_agree": report.validators_agree,
        "validation_status": report.validation_status,
        "validation_reason": report.validation_reason,
        "classification_category": report.classification_category,
        "classification_reason": report.classification_reason,
        "priority": report.priority,
        "current_status": report.current_status,
        "submission_timestamp": _iso(report.submission_timestamp),
    }


def _decision_json(decision):
    return {
        "report_id": decision.report_id,
        "route_key": decision.route_key,
        "distance_lookup": decision.distance_lookup,
        "selected_depot": decision.selected_depot_id,
        "selected_handler": decision.selected_handler_id,
        "priority": decision.priority,
        "assignment_timestamp": _iso(decision.assignment_timestamp),
        "submission_timestamp": _iso(decision.submission_timestamp),
        "assignment_status": decision.assignment_status,
        "reason": decision.reason,
    }


def _error(message, status):
    return jsonify({"error": message}), status


@api.get("/health")
def health_check():
    return jsonify({"status": "ok", "service": "city-bus-breakdown-tracker"})


@api.post("/reports")
def create_report():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _error("Request body must be a JSON object.", 400)
    if not isinstance(payload.get("identifier"), str):
        return _error("identifier is required and must be a string.", 400)

    report_id = str(payload.get("report_id") or uuid4())
    if db.session.get(Report, report_id) is not None:
        return _error(f"Report {report_id} already exists.", 409)
    submitted_at = datetime.now(timezone.utc).replace(tzinfo=None)
    comparison = compare_validators(payload["identifier"])
    dfa_result = comparison["dfa"]
    regex_result = comparison["regex"]
    validation_ok = (
        bool(dfa_result["accepted"])
        and bool(regex_result["accepted"])
        and bool(comparison["agree"])
    )
    validation_reason = (
        "DFA and regex validators agree and accept the identifier."
        if validation_ok
        else comparison["validation_message"]
    )
    classification = {"category": None, "valid": False, "reason": None}
    priority_result = {"priority": None, "reason": ""}
    if validation_ok:
        classification = classify_issue(payload.get("issue_code"), payload.get("description"))
        if classification["valid"]:
            priority_result = determine_priority(
                classification["category"],
                emergency=bool(payload.get("emergency", False)),
                severe_accident=bool(payload.get("severe_accident", False)),
                dangerous_electrical_fault=bool(
                    payload.get("dangerous_electrical_fault", False)
                ),
            )
        else:
            validation_ok = False
            validation_reason = classification["reason"]

    report = Report(
        report_id=report_id,
        original_request=payload,
        reporter_details=payload.get("reporter_details", {}),
        identifier=payload["identifier"],
        issue_code=payload.get("issue_code"),
        description=payload.get("description"),
        emergency=bool(payload.get("emergency", False)),
        severe_accident=bool(payload.get("severe_accident", False)),
        dangerous_electrical_fault=bool(payload.get("dangerous_electrical_fault", False)),
        dfa_valid=bool(dfa_result["accepted"]),
        regex_valid=bool(regex_result["accepted"]),
        validators_agree=bool(comparison["agree"]),
        validation_status="accepted" if validation_ok else "rejected",
        validation_reason=validation_reason,
        classification_category=classification["category"],
        classification_reason=classification["reason"],
        priority=priority_result["priority"],
        current_status="Pending" if validation_ok else "Rejected",
        submission_timestamp=submitted_at,
    )
    try:
        db.session.add(report)
        db.session.add(
            StatusHistory(
                report_id=report_id,
                old_status=None,
                new_status=report.current_status,
                changed_at=submitted_at,
                reason=validation_reason,
            )
        )
        if not validation_ok:
            db.session.commit()
            return jsonify({"report": _report_json(report), "assignment": None}), 422

        db.session.flush()
        dispatch_result = engine.dispatch_report(
            {
                "report_id": report_id,
                "identifier": report.identifier,
                "category": report.classification_category,
                "validated": True,
                "emergency": report.emergency,
                "severe_accident": report.severe_accident,
                "dangerous_electrical_fault": report.dangerous_electrical_fault,
                "submission_timestamp": submitted_at,
            }
        )
        if dispatch_result["assignment_status"] == "assigned":
            report.current_status = "Assigned"
            db.session.add(
                StatusHistory(
                    report_id=report_id,
                    old_status="Pending",
                    new_status="Assigned",
                    changed_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    reason=dispatch_result["reason"],
                )
            )
        db.session.commit()
        return jsonify(
            {
                "report": _report_json(report),
                "assignment": dispatch_result,
            }
        ), 201
    except ValueError as exc:
        db.session.rollback()
        return _error(str(exc), 409)
    except IntegrityError:
        db.session.rollback()
        return _error(f"Report {report_id} already has an active assignment.", 409)
    except Exception:
        db.session.rollback()
        raise


@api.get("/reports")
def list_reports():
    reports = Report.query.order_by(Report.submission_timestamp.desc()).all()
    return jsonify({"reports": [_report_json(report) for report in reports]})


@api.get("/reports/<report_id>")
def get_report(report_id):
    report = db.session.get(Report, report_id)
    if report is None:
        return _error("Report not found.", 404)
    return jsonify({"report": _report_json(report)})


@api.get("/reports/track/<report_id>")
def track_report(report_id):
    report = db.session.get(Report, report_id)
    if report is None:
        return _error("Report not found.", 404)
    decision = RoutingDecision.query.filter_by(report_id=report_id).first()
    assignment = Assignment.query.filter_by(report_id=report_id).first()
    history = StatusHistory.query.filter_by(report_id=report_id).order_by(StatusHistory.changed_at).all()
    return jsonify(
        {
            "report": _report_json(report),
            "assignment": {
                "depot_id": assignment.depot_id,
                "handler_id": assignment.handler_id,
                "status": assignment.status,
                "assigned_at": _iso(assignment.assigned_at),
                "reason": assignment.reason,
            }
            if assignment
            else None,
            "routing_decision": _decision_json(decision) if decision else None,
            "status_history": [
                {
                    "old_status": item.old_status,
                    "new_status": item.new_status,
                    "changed_at": _iso(item.changed_at),
                    "reason": item.reason,
                }
                for item in history
            ],
        }
    )


@api.post("/reports/<report_id>/assign")
def assign_report(report_id):
    report = db.session.get(Report, report_id)
    if report is None:
        return _error("Report not found.", 404)
    try:
        result = engine.retry_assignment(report)
        if result["assignment_status"] == "assigned":
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            report.current_status = "Assigned"
            db.session.add(
                StatusHistory(
                    report_id=report_id,
                    old_status="Pending",
                    new_status="Assigned",
                    changed_at=now,
                    reason=result["reason"],
                )
            )
        db.session.commit()
        return jsonify({"report": _report_json(report), "assignment": result})
    except ValueError as exc:
        db.session.rollback()
        return _error(str(exc), 409)
    except IntegrityError:
        db.session.rollback()
        return _error(f"Report {report_id} already has an active assignment.", 409)


@api.get("/handlers")
def list_handlers():
    return jsonify(
        {
            "handlers": [
                {
                    "handler_id": handler.handler_id,
                    "name": handler.name,
                    "depot_id": handler.depot_id,
                    "available": handler.available,
                    "maximum_capacity": handler.maximum_capacity,
                    "current_workload": handler.current_workload,
                    "assigned_categories": handler.assigned_categories,
                }
                for handler in Handler.query.order_by(Handler.handler_id).all()
            ]
        }
    )


@api.patch("/handlers/<handler_id>")
def update_handler(handler_id):
    handler = db.session.get(Handler, handler_id)
    if handler is None:
        return _error("Handler not found.", 404)
    payload = request.get_json(silent=True) or {}
    if "available" in payload:
        if not isinstance(payload["available"], bool):
            return _error("available must be boolean.", 400)
        handler.available = payload["available"]
    if "maximum_capacity" in payload:
        capacity = payload["maximum_capacity"]
        if not isinstance(capacity, int) or capacity < handler.current_workload:
            return _error("maximum_capacity must cover current workload.", 400)
        handler.maximum_capacity = capacity
    db.session.commit()
    return jsonify({"handler_id": handler.handler_id, "available": handler.available,
                    "maximum_capacity": handler.maximum_capacity,
                    "current_workload": handler.current_workload})


@api.get("/depots")
def list_depots():
    result = []
    for depot in Depot.query.order_by(Depot.depot_id).all():
        assigned = Assignment.query.filter_by(depot_id=depot.depot_id, status="assigned").count()
        result.append(
            {"depot_id": depot.depot_id, "name": depot.name, "capacity": depot.capacity,
             "current_load": assigned}
        )
    return jsonify({"depots": result})


@api.get("/routing/table")
def routing_table():
    return jsonify({"depots": [depot.__dict__ for depot in DEPOTS], "distances": DISTANCE_TABLE})


@api.get("/routing/decisions")
def routing_decisions():
    decisions = RoutingDecision.query.order_by(RoutingDecision.assignment_timestamp.desc()).all()
    return jsonify({"decisions": [_decision_json(decision) for decision in decisions]})


@api.patch("/reports/<report_id>/status")
def update_report_status(report_id):
    payload = request.get_json(silent=True) or {}
    new_status = payload.get("status")
    valid_statuses = {"Pending", "Assigned", "In Progress", "Resolved"}
    if new_status not in valid_statuses:
        return _error("status must be Pending, Assigned, In Progress, or Resolved.", 400)
    report = db.session.get(Report, report_id)
    if report is None:
        return _error("Report not found.", 404)
    if report.current_status == "Rejected":
        return _error("Rejected reports cannot enter the dispatch status flow.", 409)
    transitions = {
        "Pending": {"Assigned"},
        "Assigned": {"In Progress"},
        "In Progress": {"Resolved"},
        "Resolved": set(),
    }
    if report.current_status not in transitions or new_status not in transitions[report.current_status]:
        return _error(f"Invalid status transition from {report.current_status}.", 409)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    old_status = report.current_status
    report.current_status = new_status
    assignment = Assignment.query.filter_by(report_id=report_id).first()
    if assignment:
        assignment.status = new_status.lower().replace(" ", "_")
        if new_status == "Resolved":
            handler = db.session.get(Handler, assignment.handler_id)
            if handler and handler.current_workload > 0:
                handler.current_workload -= 1
    db.session.add(StatusHistory(report_id=report_id, old_status=old_status,
                                 new_status=new_status, changed_at=now,
                                 reason=payload.get("reason")))
    db.session.commit()
    return jsonify({"report": _report_json(report)})


@api.get("/analytics")
def analytics():
    reports = Report.query.all()
    return jsonify(
        {
            "total_reports": len(reports),
            "by_status": {
                status: sum(report.current_status == status for report in reports)
                for status in ("Pending", "Assigned", "In Progress", "Resolved", "Rejected")
            },
            "by_category": {
                category: sum(report.classification_category == category for report in reports)
                for category in ("Mechanical", "Tyre", "Accident", "Fuel", "Electrical")
            },
            "by_priority": {
                priority: sum(report.priority == priority for report in reports)
                for priority in ("Critical", "High", "Normal")
            },
        }
    )
