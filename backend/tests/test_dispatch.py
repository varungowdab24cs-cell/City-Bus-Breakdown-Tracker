from datetime import datetime

import pytest

from app import create_app
from app.extensions import db
from dispatch.dispatch_engine import DispatchAudit, DispatchEngine, Handler
from services.queue_service import WaitingQueueEntry


@pytest.fixture
def engine():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "FRONTEND_ORIGIN": "http://localhost:5173",
        }
    )
    with app.app_context():
        dispatch_engine = DispatchEngine()
        dispatch_engine.initialize()
        yield dispatch_engine
        db.session.remove()


def report(report_id="R1", identifier="BUS1234-ROUTEA12", category="Mechanical", **flags):
    return {
        "report_id": report_id,
        "identifier": identifier,
        "category": category,
        "validated": True,
        "submission_timestamp": datetime(2026, 1, 1, 12, 0),
        **flags,
    }


def test_nearest_depot_and_handler_are_selected(engine):
    result = engine.dispatch_report(report())

    assert result["selected_depot"] == "D01"
    assert result["selected_handler"] == "H01"
    assert result["assignment_status"] == "assigned"


def test_unvalidated_report_is_rejected(engine):
    invalid = report()
    invalid["validated"] = False

    with pytest.raises(ValueError, match="validated report"):
        engine.dispatch_report(invalid)


def test_unknown_route_goes_to_correction_queue(engine):
    result = engine.dispatch_report(report(identifier="BUS1234-ROUTEF12"))

    assert result["assignment_status"] == "correction_queue"
    assert result["selected_depot"] is None
    assert WaitingQueueEntry.query.filter_by(report_id="R1").one().status == "correction_queue"


def test_unavailable_handler_uses_next_eligible_handler(engine):
    Handler.query.filter_by(handler_id="H01").one().available = False
    db.session.commit()

    result = engine.dispatch_report(report())

    assert result["selected_depot"] == "D05"
    assert result["selected_handler"] == "H09"


def test_full_nearest_depot_uses_next_nearest(engine):
    for index in range(3):
        engine.dispatch_report(report(f"F{index}", f"BUS123{index}-ROUTEA12"))

    result = engine.dispatch_report(report("F3", "BUS9999-ROUTEA12", "Mechanical"))

    assert result["selected_depot"] == "D05"


def test_all_eligible_capacity_full_goes_to_waiting_queue(engine):
    for index in range(20):
        engine.dispatch_report(report(f"W{index}", f"BUS{index:04d}-ROUTEA12"))

    result = engine.dispatch_report(report("W20", "BUS9999-ROUTEA12"))

    assert result["assignment_status"] == "waiting"
    assert WaitingQueueEntry.query.filter_by(report_id="W20").one().priority == "Normal"


def test_priority_override_and_queue_order(engine):
    critical = engine.dispatch_report(
        report("C1", "BUS1234-ROUTEF12", "Accident", severe_accident=True)
    )
    normal = engine.dispatch_report(
        report("N1", "BUS1235-ROUTEF12", "Fuel")
    )

    assert critical["priority"] == "Critical"
    assert normal["priority"] == "Normal"
    assert [entry.report_id for entry in engine.queue_service.pending()] == ["C1", "N1"]


def test_duplicate_assignment_is_rejected(engine):
    engine.dispatch_report(report())

    with pytest.raises(ValueError, match="already has"):
        engine.dispatch_report(report())


def test_audit_records_route_distances_and_decision(engine):
    engine.dispatch_report(report())
    audit = DispatchAudit.query.filter_by(report_id="R1").one()

    assert audit.route_key == "A"
    assert audit.distance_lookup["D01"] == 2
    assert audit.assignment_status == "assigned"
    assert audit.selected_handler_id == "H01"
