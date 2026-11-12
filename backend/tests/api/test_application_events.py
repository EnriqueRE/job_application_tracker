"""Application Events and Status Override API: the timeline drives the Pipeline Status."""

from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tracker.domain import OrganizationType
from tracker.services import ApplicationService, OrganizationService


@pytest.fixture
def application_id(db_session: Session) -> int:
    acme = OrganizationService(db_session).create(
        name="Acme", organization_type=OrganizationType.COMPANY
    )
    return ApplicationService(db_session).create(organization_id=acme.id, role="Engineer").id


def add_event(client: TestClient, application_id: int, **body: Any) -> dict[str, Any]:
    response = client.post(f"/api/applications/{application_id}/events", json=body)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


def test_adding_an_event_derives_the_pipeline_status(
    client: TestClient, application_id: int
) -> None:
    result = add_event(
        client,
        application_id,
        event_type="applied",
        occurred_at="2026-11-01T09:30:00Z",
        notes="Via the careers page",
    )

    assert result["application"] == {
        "id": application_id,
        "current_status": "applied",
        "status_overridden": False,
    }
    event = result["event"]
    assert event["event_type"] == "applied"
    assert event["resulting_status"] == "applied"
    assert event["notes"] == "Via the careers page"
    assert event["occurred_at"].startswith("2026-11-01T09:30:00")
    assert event["application_id"] == application_id


def test_a_status_override_survives_new_events_until_cleared(
    client: TestClient, application_id: int
) -> None:
    add_event(client, application_id, event_type="applied")

    response = client.put(
        f"/api/applications/{application_id}/status-override", json={"status": "rejected"}
    )
    assert response.status_code == 200, response.text
    assert response.json() == {
        "id": application_id,
        "current_status": "rejected",
        "status_overridden": True,
    }

    result = add_event(client, application_id, event_type="screening")
    assert result["event"]["resulting_status"] == "screening"
    assert result["application"]["current_status"] == "rejected"
    assert result["application"]["status_overridden"] is True

    response = client.delete(f"/api/applications/{application_id}/status-override")
    assert response.status_code == 200, response.text
    assert response.json() == {
        "id": application_id,
        "current_status": "screening",
        "status_overridden": False,
    }


def test_clearing_an_override_without_status_bearing_events_falls_back_to_saved(
    client: TestClient, application_id: int
) -> None:
    add_event(client, application_id, event_type="note", notes="Found it on LinkedIn")
    client.put(f"/api/applications/{application_id}/status-override", json={"status": "offer"})

    response = client.delete(f"/api/applications/{application_id}/status-override")

    assert response.json()["current_status"] == "saved"


def test_deleting_the_latest_status_bearing_event_falls_back_to_the_previous_one(
    client: TestClient, application_id: int
) -> None:
    add_event(client, application_id, event_type="applied")
    interview = add_event(client, application_id, event_type="interview_scheduled")["event"]
    add_event(client, application_id, event_type="note")

    response = client.delete(f"/api/applications/{application_id}/events/{interview['id']}")

    assert response.status_code == 200, response.text
    assert response.json() == {
        "id": application_id,
        "current_status": "applied",
        "status_overridden": False,
    }
    events = client.get(f"/api/applications/{application_id}/events").json()
    assert [event["event_type"] for event in events] == ["applied", "note"]


def test_editing_an_event_re_derives_the_pipeline_status(
    client: TestClient, application_id: int
) -> None:
    add_event(client, application_id, event_type="applied")
    latest = add_event(client, application_id, event_type="screening", notes="Phone call")["event"]

    response = client.patch(
        f"/api/applications/{application_id}/events/{latest['id']}",
        json={"event_type": "rejected"},
    )

    assert response.status_code == 200, response.text
    result = response.json()
    assert result["application"]["current_status"] == "rejected"
    assert result["event"]["event_type"] == "rejected"
    assert result["event"]["resulting_status"] == "rejected"
    assert result["event"]["notes"] == "Phone call"


def test_editing_only_an_events_notes_leaves_the_status_alone(
    client: TestClient, application_id: int
) -> None:
    applied = add_event(client, application_id, event_type="applied")["event"]

    response = client.patch(
        f"/api/applications/{application_id}/events/{applied['id']}",
        json={"notes": "Referral from Ana", "occurred_at": None},
    )

    result = response.json()
    assert result["event"]["notes"] == "Referral from Ana"
    assert result["event"]["event_type"] == "applied"
    assert result["application"]["current_status"] == "applied"


def test_an_unknown_application_is_not_found(client: TestClient) -> None:
    response = client.post("/api/applications/999999/events", json={"event_type": "applied"})

    assert response.status_code == 404
    assert response.json() == {"detail": "Application 999999 was not found"}
    assert (
        client.put("/api/applications/999999/status-override", json={"status": "offer"}).status_code
        == 404
    )


def test_an_event_on_another_applications_timeline_is_not_found(
    client: TestClient, db_session: Session, application_id: int
) -> None:
    other = ApplicationService(db_session).create(
        organization_id=ApplicationService(db_session).get(application_id).organization_id,
        role="Designer",
    )
    event = add_event(client, other.id, event_type="applied")["event"]

    url = f"/api/applications/{application_id}/events/{event['id']}"
    assert client.patch(url, json={"notes": "x"}).status_code == 404
    assert client.delete(url).status_code == 404
    assert client.get(f"/api/applications/{other.id}/events").json()[0]["id"] == event["id"]


def test_an_event_type_cannot_be_cleared(client: TestClient, application_id: int) -> None:
    event = add_event(client, application_id, event_type="applied")["event"]

    response = client.patch(
        f"/api/applications/{application_id}/events/{event['id']}", json={"event_type": None}
    )

    assert response.status_code == 422
