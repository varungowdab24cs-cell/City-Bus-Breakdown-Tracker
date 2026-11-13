import os
import tempfile

import pytest

from app import create_app
from app.extensions import db


@pytest.fixture
def app():
    handle, database_path = tempfile.mkstemp(suffix=".db")
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


def valid_payload(**overrides):
    payload = {
        "reporter_details": {"name": "Ravi", "phone": "555-0100"},
        "identifier": "BUS1234-ROUTEA12",
        "issue_code": "MECH",
        "description": "Engine overheating",
        "emergency": False,
    }
    payload.update(overrides)
    return payload


def test_create_report_dispatches_and_can_be_tracked(app):
    client = app.test_client()

    response = client.post("/api/reports", json=valid_payload())
    body = response.get_json()
    report_id = body["report"]["report_id"]

    assert response.status_code == 201
    assert body["report"]["validation_status"] == "accepted"
    assert body["report"]["classification_category"] == "Mechanical"
    assert body["assignment"]["selected_depot"] == "D01"
    assert client.get(f"/api/reports/track/{report_id}").get_json()["status_history"][-1][
        "new_status"
    ] == "Assigned"


def test_rejected_report_is_persisted_and_not_dispatched(app):
    client = app.test_client()

    response = client.post(
        "/api/reports",
        json=valid_payload(identifier="BUS123-ROUTEA12"),
    )
    body = response.get_json()
    report_id = body["report"]["report_id"]

    assert response.status_code == 422
    assert body["report"]["validation_status"] == "rejected"
    assert body["assignment"] is None
    assert client.get(f"/api/reports/track/{report_id}").get_json()["routing_decision"] is None


def test_status_flow_and_operational_endpoints(app):
    client = app.test_client()
    report_id = client.post("/api/reports", json=valid_payload()).get_json()["report"]["report_id"]

    assert client.patch(f"/api/reports/{report_id}/status", json={"status": "In Progress"}).status_code == 200
    assert client.patch(f"/api/reports/{report_id}/status", json={"status": "Resolved"}).status_code == 200
    assert len(client.get(f"/api/reports/track/{report_id}").get_json()["status_history"]) == 4
    assert len(client.get("/api/handlers").get_json()["handlers"]) == 10
    assert len(client.get("/api/depots").get_json()["depots"]) == 5
    assert set(client.get("/api/routing/table").get_json()["distances"]) == set("ABCDE")
    assert client.get("/api/routing/decisions").status_code == 200
    assert client.get("/api/analytics").get_json()["total_reports"] == 1


def test_report_persists_after_application_restart(app):
    client = app.test_client()
    report_id = client.post("/api/reports", json=valid_payload()).get_json()["report"]["report_id"]
    database_uri = app.config["SQLALCHEMY_DATABASE_URI"]
    with app.app_context():
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

    response = restarted.test_client().get(f"/api/reports/{report_id}")
    assert response.status_code == 200
    assert response.get_json()["report"]["report_id"] == report_id
    with restarted.app_context():
        db.session.remove()
        db.engine.dispose()


def test_rejected_report_cannot_be_assigned(app):
    client = app.test_client()
    report_id = client.post(
        "/api/reports", json=valid_payload(identifier="BUS123-ROUTEA12")
    ).get_json()["report"]["report_id"]

    response = client.post(f"/api/reports/{report_id}/assign")

    assert response.status_code == 409
    assert "Rejected" in response.get_json()["error"]


def test_resolution_releases_handler_capacity(app):
    client = app.test_client()
    report_id = client.post("/api/reports", json=valid_payload()).get_json()["report"]["report_id"]
    assigned_handler = client.get("/api/handlers").get_json()["handlers"][0]
    assert assigned_handler["current_workload"] == 1

    client.patch(f"/api/reports/{report_id}/status", json={"status": "In Progress"})
    response = client.patch(
        f"/api/reports/{report_id}/status", json={"status": "Resolved"}
    )

    assert response.status_code == 200
    handlers = client.get("/api/handlers").get_json()["handlers"]
    assert next(item for item in handlers if item["handler_id"] == assigned_handler["handler_id"])[
        "current_workload"
    ] == 0


def test_queued_report_can_be_reassigned_after_handler_recovery(app):
    client = app.test_client()
    handlers = client.get("/api/handlers").get_json()["handlers"]
    for handler in handlers:
        client.patch(
            f"/api/handlers/{handler['handler_id']}",
            json={"available": False},
        )
    report_id = client.post("/api/reports", json=valid_payload()).get_json()["report"]["report_id"]
    assert client.get(f"/api/reports/track/{report_id}").get_json()[
        "routing_decision"
    ]["assignment_status"] == "waiting"

    client.patch("/api/handlers/H01", json={"available": True})
    response = client.post(f"/api/reports/{report_id}/assign")

    assert response.status_code == 200
    assert response.get_json()["assignment"]["selected_handler"] == "H01"
