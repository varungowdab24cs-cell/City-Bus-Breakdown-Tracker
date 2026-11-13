"""Phase 7 comprehensive tests using isolated temporary SQLite databases."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import os
import tempfile

import pytest

from app import create_app
from app.extensions import db
from automata.classifier import classify_issue
from automata.dfa import ACCEPTING_STATE, validate_bus_identifier
from automata.regex_validator import compare_validators, validate_with_regex
from dispatch.dispatch_engine import DispatchEngine, Handler
from services.queue_service import WaitingQueueEntry


@pytest.fixture
def isolated_app():
    handle, database_path = tempfile.mkstemp(prefix="phase7-", suffix=".db")
    os.close(handle)
    application = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "FRONTEND_ORIGIN": "http://localhost:5173",
        }
    )
    yield application
    with application.app_context():
        db.session.remove()
        db.engine.dispose()
    os.remove(database_path)


@pytest.fixture
def dispatch_engine(isolated_app):
    with isolated_app.app_context():
        yield DispatchEngine()


def dispatch_report(report_id="P7-1", identifier="BUS1234-ROUTEA12", category="Mechanical", **flags):
    return {
        "report_id": report_id,
        "identifier": identifier,
        "category": category,
        "validated": True,
        "submission_timestamp": datetime(2026, 1, 1, 12, 0),
        **flags,
    }


def test_p7_01_dfa_accepts_valid_identifier():
    result = validate_bus_identifier("BUS1234-ROUTEA12")
    assert result["accepted"] is True
    assert result["final_state"] == ACCEPTING_STATE


def test_p7_02_regex_accepts_valid_identifier():
    assert validate_with_regex("BUS1234-ROUTEA12")["accepted"] is True


def test_p7_03_dfa_regex_equivalence():
    comparison = compare_validators("BUS1234-ROUTEA12")
    assert comparison["agree"] is True
    assert comparison["dfa"]["accepted"] == comparison["regex"]["accepted"]


@pytest.mark.parametrize(
    ("code", "category"),
    [
        ("MECH", "Mechanical"),
        ("TYRE", "Tyre"),
        ("ACC", "Accident"),
        ("FUEL", "Fuel"),
        ("ELEC", "Electrical"),
    ],
)
def test_p7_04_all_five_categories(code, category):
    result = classify_issue(code, "description is not used when code is valid")
    assert result["valid"] is True
    assert result["category"] == category


def test_p7_05_conflicting_classification_uses_priority():
    result = classify_issue(description="Collision caused battery, engine, tyre and fuel damage.")
    assert result["category"] == "Accident"


def test_p7_06_unknown_classification_code_is_rejected():
    result = classify_issue("UNKNOWN", "engine failure")
    assert result["valid"] is False
    assert result["category"] is None


def test_p7_07_unknown_routing_key_enters_correction_queue(dispatch_engine):
    result = dispatch_engine.dispatch_report(
        dispatch_report(identifier="BUS1234-ROUTEF12")
    )
    assert result["assignment_status"] == "correction_queue"
    assert result["selected_depot"] is None


def test_p7_08_nearest_depot_is_selected(dispatch_engine):
    result = dispatch_engine.dispatch_report(dispatch_report())
    assert result["selected_depot"] == "D01"
    assert result["distance_lookup"]["D01"] == 2


def test_p7_09_depot_capacity_overflow_uses_next_depot(dispatch_engine):
    for index in range(3):
        dispatch_engine.dispatch_report(dispatch_report(f"P7-DEPOT-{index}"))
    result = dispatch_engine.dispatch_report(dispatch_report("P7-DEPOT-3"))
    assert result["selected_depot"] == "D05"


def test_p7_10_handler_unavailability_uses_next_eligible_depot(dispatch_engine):
    Handler.query.filter_by(handler_id="H01").one().available = False
    db.session.commit()
    result = dispatch_engine.dispatch_report(dispatch_report())
    assert result["selected_handler"] == "H09"
    assert result["selected_depot"] == "D05"


def test_p7_11_handler_capacity_overflow_uses_next_handler(dispatch_engine):
    handler = Handler.query.filter_by(handler_id="H01").one()
    handler.current_workload = handler.maximum_capacity
    db.session.commit()
    result = dispatch_engine.dispatch_report(dispatch_report())
    assert result["selected_handler"] == "H09"


def test_p7_12_all_depots_unavailable_enters_waiting_queue(dispatch_engine):
    for handler in Handler.query.all():
        handler.available = False
    db.session.commit()
    result = dispatch_engine.dispatch_report(dispatch_report())
    assert result["assignment_status"] == "waiting"
    assert WaitingQueueEntry.query.filter_by(report_id="P7-1").one().status == "waiting"


def test_p7_13_emergency_is_critical(dispatch_engine):
    result = dispatch_engine.dispatch_report(dispatch_report(emergency=True))
    assert result["priority"] == "Critical"


def test_p7_14_queue_order_is_priority_then_submission_time(dispatch_engine):
    for handler in Handler.query.all():
        handler.available = False
    db.session.commit()
    dispatch_engine.dispatch_report(dispatch_report("P7-NORMAL"))
    dispatch_engine.dispatch_report(
        dispatch_report("P7-CRITICAL", category="Accident", severe_accident=True)
    )
    assert [entry.report_id for entry in dispatch_engine.queue_service.pending()] == [
        "P7-CRITICAL",
        "P7-NORMAL",
    ]


def test_p7_15_duplicate_assignment_is_prevented(dispatch_engine):
    dispatch_engine.dispatch_report(dispatch_report())
    with pytest.raises(ValueError, match="already has"):
        dispatch_engine.dispatch_report(dispatch_report())


def test_p7_16_invalid_report_is_stored_rejected_and_not_dispatched(isolated_app):
    client = isolated_app.test_client()
    response = client.post(
        "/api/reports",
        json={
            "reporter_details": {"name": "Test"},
            "identifier": "BUS123-ROUTEA12",
            "issue_code": "MECH",
            "description": "Malformed identifier",
        },
    )
    body = response.get_json()
    assert response.status_code == 422
    assert body["report"]["validation_status"] == "rejected"
    assert body["assignment"] is None
    assert client.get(f"/api/reports/track/{body['report']['report_id']}").get_json()[
        "routing_decision"
    ] is None


def test_p7_17_status_transitions_are_enforced(isolated_app):
    client = isolated_app.test_client()
    report_id = client.post(
        "/api/reports",
        json={
            "reporter_details": {"name": "Test"},
            "identifier": "BUS1234-ROUTEA12",
            "issue_code": "MECH",
            "description": "Engine issue",
        },
    ).get_json()["report"]["report_id"]
    assert client.patch(
        f"/api/reports/{report_id}/status", json={"status": "In Progress"}
    ).status_code == 200
    assert client.patch(
        f"/api/reports/{report_id}/status", json={"status": "Resolved"}
    ).status_code == 200
    assert client.patch(
        f"/api/reports/{report_id}/status", json={"status": "Assigned"}
    ).status_code == 409


def test_p7_18_database_persists_report_after_restart(isolated_app):
    client = isolated_app.test_client()
    report_id = client.post(
        "/api/reports",
        json={
            "reporter_details": {"name": "Persisted"},
            "identifier": "BUS1234-ROUTEA12",
            "issue_code": "MECH",
            "description": "Persistent engine issue",
        },
    ).get_json()["report"]["report_id"]
    database_uri = isolated_app.config["SQLALCHEMY_DATABASE_URI"]
    with isolated_app.app_context():
        db.session.remove()
        db.engine.dispose()
    restarted = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": database_uri,
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "FRONTEND_ORIGIN": "http://localhost:5173",
        }
    )
    assert restarted.test_client().get(f"/api/reports/{report_id}").status_code == 200
    with restarted.app_context():
        db.session.remove()
        db.engine.dispose()


def test_p7_19_resolution_releases_handler_capacity(isolated_app):
    client = isolated_app.test_client()
    report_id = client.post(
        "/api/reports",
        json={
            "reporter_details": {"name": "Capacity"},
            "identifier": "BUS1234-ROUTEA12",
            "issue_code": "MECH",
            "description": "Engine issue",
        },
    ).get_json()["report"]["report_id"]
    assert client.patch(
        f"/api/reports/{report_id}/status", json={"status": "In Progress"}
    ).status_code == 200
    assert client.patch(
        f"/api/reports/{report_id}/status", json={"status": "Resolved"}
    ).status_code == 200
    handler = next(
        item
        for item in client.get("/api/handlers").get_json()["handlers"]
        if item["handler_id"] == "H01"
    )
    assert handler["current_workload"] == 0


def test_p7_20_complete_end_to_end_workflow(isolated_app):
    client = isolated_app.test_client()
    response = client.post(
        "/api/reports",
        json={
            "reporter_details": {"name": "End to end", "phone": "555-0100"},
            "identifier": "BUS1234-ROUTEA12",
            "issue_code": "MECH",
            "description": "Engine overheating",
            "emergency": True,
        },
    )
    body = response.get_json()
    report_id = body["report"]["report_id"]
    analytics = client.get("/api/analytics").get_json()
    tracked = client.get(f"/api/reports/track/{report_id}").get_json()
    assert response.status_code == 201
    assert body["report"]["dfa_valid"] is True
    assert body["report"]["regex_valid"] is True
    assert body["report"]["validators_agree"] is True
    assert body["report"]["classification_category"] == "Mechanical"
    assert body["report"]["priority"] == "Critical"
    assert body["assignment"]["selected_depot"] == "D01"
    assert tracked["routing_decision"]["route_key"] == "A"
    assert analytics["total_reports"] == 1


def test_p7_21_concurrent_duplicate_assignment_has_one_winner(isolated_app):
    """Two request threads may race, but the unique report ID permits one assignment."""
    client = isolated_app.test_client()
    for handler in client.get("/api/handlers").get_json()["handlers"]:
        client.patch(
            f"/api/handlers/{handler['handler_id']}",
            json={"available": False},
        )
    report_id = client.post(
        "/api/reports",
        json={
            "report_id": "P7-CONCURRENT",
            "reporter_details": {"name": "Concurrent"},
            "identifier": "BUS1234-ROUTEA12",
            "issue_code": "MECH",
            "description": "Concurrent assignment",
        },
    ).get_json()["report"]["report_id"]
    client.patch("/api/handlers/H01", json={"available": True})

    def assign():
        with isolated_app.app_context():
            return isolated_app.test_client().post(f"/api/reports/{report_id}/assign").status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = list(executor.map(lambda _: assign(), range(2)))
    assert sorted(statuses) == [200, 409]
