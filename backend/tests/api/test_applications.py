"""Applications API: CRUD, filters, status counts, due soon, archive/restore."""

from datetime import date
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tracker.api.applications import get_today
from tracker.domain import ApplicationEventType, Organization, OrganizationType
from tracker.services import ApplicationService, OrganizationService


@pytest.fixture
def acme(db_session: Session) -> Organization:
    return OrganizationService(db_session).create(
        name="Acme Corp", organization_type=OrganizationType.COMPANY
    )


def create(client: TestClient, organization: Organization, **fields: Any) -> dict[str, Any]:
    response = client.post(
        "/api/applications",
        json={"organization_id": organization.id, "role": "Engineer", **fields},
    )
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def test_created_application_is_returned_with_its_organization_and_markdown_texts(
    client: TestClient, acme: Organization
) -> None:
    created = create(
        client,
        acme,
        role="Backend Engineer",
        applied_at="2026-11-01",
        job_description="# JD",
        interview_notes="- ask about on-call",
        application_notes="Referred by Ana",
    )

    response = client.get(f"/api/applications/{created['id']}")

    assert response.status_code == 200
    detail = response.json()
    assert detail["role"] == "Backend Engineer"
    assert detail["applied_at"] == "2026-11-01"
    assert detail["current_status"] == "saved"
    assert detail["status_overridden"] is False
    assert detail["job_description"] == "# JD"
    assert detail["interview_notes"] == "- ask about on-call"
    assert detail["application_notes"] == "Referred by Ana"
    assert detail["organization"] == {
        "id": acme.id,
        "name": "Acme Corp",
        "organization_type": "company",
    }
    assert detail["events"] == []
    assert detail["archived_at"] is None


def test_patch_changes_only_the_given_fields(client: TestClient, acme: Organization) -> None:
    created = create(client, acme, role="Engineer", location="Madrid", interview_notes="old")

    response = client.patch(
        f"/api/applications/{created['id']}",
        json={"interview_notes": "## Round 1\n\nWent well", "next_action_at": "2026-11-20"},
    )

    assert response.status_code == 200
    detail = response.json()
    assert detail["interview_notes"] == "## Round 1\n\nWent well"
    assert detail["next_action_at"] == "2026-11-20"
    assert detail["role"] == "Engineer"
    assert detail["location"] == "Madrid"


def test_patch_can_clear_optional_fields_but_not_the_role(
    client: TestClient, acme: Organization
) -> None:
    created = create(client, acme, location="Madrid")
    url = f"/api/applications/{created['id']}"

    assert client.patch(url, json={"location": None}).json()["location"] is None
    assert client.patch(url, json={"role": None}).status_code == 422


def test_pipeline_status_cannot_be_patched(client: TestClient, acme: Organization) -> None:
    created = create(client, acme)

    response = client.patch(f"/api/applications/{created['id']}", json={"current_status": "offer"})

    assert response.status_code == 422


def test_detail_includes_the_application_event_timeline_oldest_first(
    client: TestClient, db_session: Session, acme: Organization
) -> None:
    created = create(client, acme)
    service = ApplicationService(db_session)
    service.add_event(created["id"], ApplicationEventType.APPLIED, notes="via site")
    service.add_event(created["id"], ApplicationEventType.SCREENING)

    detail = client.get(f"/api/applications/{created['id']}").json()

    assert detail["current_status"] == "screening"
    assert [(e["event_type"], e["resulting_status"], e["notes"]) for e in detail["events"]] == [
        ("applied", "applied", "via site"),
        ("screening", "screening", None),
    ]


def roles(response: Any) -> list[str]:
    assert response.status_code == 200, response.text
    return [application["role"] for application in response.json()]


@pytest.fixture
def globex(db_session: Session) -> Organization:
    return OrganizationService(db_session).create(
        name="Globex", organization_type=OrganizationType.RECRUITER
    )


def test_list_filters_by_organization_name_and_role_case_insensitively(
    client: TestClient, acme: Organization, globex: Organization
) -> None:
    create(client, acme, role="Backend Engineer")
    create(client, acme, role="Data Analyst")
    create(client, globex, role="Senior BACKEND Developer")

    assert sorted(roles(client.get("/api/applications", params={"role": "backend"}))) == [
        "Backend Engineer",
        "Senior BACKEND Developer",
    ]
    assert sorted(roles(client.get("/api/applications", params={"organization": "acme"}))) == [
        "Backend Engineer",
        "Data Analyst",
    ]
    assert roles(
        client.get("/api/applications", params={"organization": "ACME", "role": "end"})
    ) == ["Backend Engineer"]


def test_list_filters_by_any_of_several_pipeline_statuses(
    client: TestClient, db_session: Session, acme: Organization
) -> None:
    service = ApplicationService(db_session)
    create(client, acme, role="Saved one")
    applied = create(client, acme, role="Applied one")
    service.add_event(applied["id"], ApplicationEventType.APPLIED)
    offer = create(client, acme, role="Offer one")
    service.add_event(offer["id"], ApplicationEventType.OFFER)

    response = client.get("/api/applications", params={"status": ["applied", "offer"]})

    assert sorted(roles(response)) == ["Applied one", "Offer one"]
    assert client.get("/api/applications", params={"status": "bogus"}).status_code == 422


def test_list_sorts_by_applied_date_newest_first_with_undated_last_by_default(
    client: TestClient, acme: Organization
) -> None:
    create(client, acme, role="Undated")
    create(client, acme, role="Older", applied_at="2026-10-01")
    create(client, acme, role="Newer", applied_at="2026-11-01")

    assert roles(client.get("/api/applications")) == ["Newer", "Older", "Undated"]
    assert roles(
        client.get("/api/applications", params={"sort": "applied_at", "order": "asc"})
    ) == [
        "Older",
        "Newer",
        "Undated",
    ]


def test_list_sorts_by_next_action_date_keeping_undated_last(
    client: TestClient, acme: Organization
) -> None:
    create(client, acme, role="No action")
    create(client, acme, role="Later", next_action_at="2026-12-01")
    create(client, acme, role="Sooner", next_action_at="2026-11-15")

    params = {"sort": "next_action_at", "order": "asc"}
    assert roles(client.get("/api/applications", params=params)) == [
        "Sooner",
        "Later",
        "No action",
    ]
    params["order"] = "desc"
    assert roles(client.get("/api/applications", params=params)) == [
        "Later",
        "Sooner",
        "No action",
    ]


def test_list_sorts_by_updated_date(client: TestClient, acme: Organization) -> None:
    first = create(client, acme, role="First")
    create(client, acme, role="Second")
    client.patch(f"/api/applications/{first['id']}", json={"location": "Remote"})

    assert roles(client.get("/api/applications", params={"sort": "updated_at"})) == [
        "First",
        "Second",
    ]
    assert roles(
        client.get("/api/applications", params={"sort": "updated_at", "order": "asc"})
    ) == ["Second", "First"]
    assert client.get("/api/applications", params={"sort": "role"}).status_code == 422


def test_archived_applications_are_listed_only_on_request_and_can_be_restored(
    client: TestClient, acme: Organization
) -> None:
    create(client, acme, role="Active")
    archived = create(client, acme, role="Old")

    response = client.post(f"/api/applications/{archived['id']}/archive")
    assert response.status_code == 200
    assert response.json()["archived_at"] is not None

    assert roles(client.get("/api/applications")) == ["Active"]
    assert sorted(roles(client.get("/api/applications", params={"include_archived": True}))) == [
        "Active",
        "Old",
    ]

    response = client.post(f"/api/applications/{archived['id']}/restore")
    assert response.status_code == 200
    assert response.json()["archived_at"] is None
    assert sorted(roles(client.get("/api/applications"))) == ["Active", "Old"]


def test_status_counts_cover_every_pipeline_status_and_skip_archived(
    client: TestClient, db_session: Session, acme: Organization
) -> None:
    service = ApplicationService(db_session)
    create(client, acme)
    create(client, acme)
    for event_type in (ApplicationEventType.APPLIED, ApplicationEventType.REJECTED):
        created = create(client, acme)
        service.add_event(created["id"], event_type)
    archived = create(client, acme)
    service.add_event(archived["id"], ApplicationEventType.OFFER)
    client.post(f"/api/applications/{archived['id']}/archive")

    response = client.get("/api/applications/status-counts")

    assert response.status_code == 200
    assert response.json() == [
        {"status": "saved", "count": 2},
        {"status": "applied", "count": 1},
        {"status": "screening", "count": 0},
        {"status": "interview", "count": 0},
        {"status": "technical_interview", "count": 0},
        {"status": "final_interview", "count": 0},
        {"status": "offer", "count": 0},
        {"status": "rejected", "count": 1},
        {"status": "withdrawn", "count": 0},
        {"status": "closed", "count": 0},
        {"status": "no_response", "count": 0},
    ]


TODAY = date(2026, 11, 12)


@pytest.fixture
def fixed_today(client: TestClient) -> date:
    app = client.app
    assert isinstance(app, FastAPI)
    app.dependency_overrides[get_today] = lambda: TODAY
    return TODAY


def test_due_lists_overdue_and_next_seven_days_soonest_first(
    client: TestClient, fixed_today: date, acme: Organization
) -> None:
    create(client, acme, role="Day 8", next_action_at="2026-11-20")
    create(client, acme, role="Day 7", next_action_at="2026-11-19")
    create(client, acme, role="Today", next_action_at="2026-11-12")
    create(client, acme, role="Overdue", next_action_at="2026-11-01")
    create(client, acme, role="No next action")
    archived = create(client, acme, role="Archived overdue", next_action_at="2026-11-02")
    client.post(f"/api/applications/{archived['id']}/archive")

    assert roles(client.get("/api/applications/due")) == ["Overdue", "Today", "Day 7"]


def test_archiving_a_missing_application_is_404(client: TestClient) -> None:
    assert client.post("/api/applications/999999/archive").status_code == 404
    assert client.post("/api/applications/999999/restore").status_code == 404


def test_missing_application_is_404(client: TestClient) -> None:
    assert client.get("/api/applications/999999").status_code == 404
    assert client.patch("/api/applications/999999", json={"role": "x"}).status_code == 404


def test_application_for_a_missing_organization_is_404(client: TestClient) -> None:
    response = client.post("/api/applications", json={"organization_id": 999999, "role": "x"})

    assert response.status_code == 404
    assert "Organization" in response.json()["detail"]


def test_vacancy_url_must_be_an_http_url(client: TestClient, acme: Organization) -> None:
    rejected = client.post(
        "/api/applications",
        json={"organization_id": acme.id, "role": "x", "vacancy_url": "not a url"},
    )
    assert rejected.status_code == 422
    assert rejected.json()["detail"][0]["loc"][-1] == "vacancy_url"

    created = create(client, acme, vacancy_url="https://jobs.example.com/123?ref=li")
    assert created["vacancy_url"] == "https://jobs.example.com/123?ref=li"

    url = f"/api/applications/{created['id']}"
    assert client.patch(url, json={"vacancy_url": "ftp://jobs.example.com"}).status_code == 422
    assert client.patch(url, json={"vacancy_url": None}).json()["vacancy_url"] is None
