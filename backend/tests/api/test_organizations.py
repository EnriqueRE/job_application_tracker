"""Organizations API: list/search, create, read, update, archive and restore."""

from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tracker.services import ApplicationService


def create(client: TestClient, **fields: Any) -> dict[str, Any]:
    body = {"name": "Acme", "organization_type": "company", **fields}
    response = client.post("/api/organizations", json=body)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


def names(response: Any) -> list[str]:
    assert response.status_code == 200, response.text
    return [organization["name"] for organization in response.json()]


def test_created_organization_is_returned_with_all_its_fields(client: TestClient) -> None:
    response = client.post(
        "/api/organizations",
        json={
            "name": "Acme",
            "organization_type": "recruiting_firm",
            "industry": "Staffing",
            "location": "Madrid",
            "priority": 5,
            "website_url": "https://acme.example",
            "career_url": "https://acme.example/jobs",
            "contact_url": "https://acme.example/contact",
            "notes": "Met them at a meetup",
        },
    )

    assert response.status_code == 201
    created = response.json()
    assert created["id"] > 0
    assert created == {
        "id": created["id"],
        "name": "Acme",
        "organization_type": "recruiting_firm",
        "industry": "Staffing",
        "location": "Madrid",
        "priority": 5,
        "website_url": "https://acme.example",
        "career_url": "https://acme.example/jobs",
        "contact_url": "https://acme.example/contact",
        "notes": "Met them at a meetup",
        "archived_at": None,
        "created_at": created["created_at"],
        "updated_at": created["updated_at"],
    }
    assert client.get(f"/api/organizations/{created['id']}").json() == created


def test_optional_fields_default_when_omitted(client: TestClient) -> None:
    created = create(client, name="Globex")

    assert created["priority"] == 3
    assert created["industry"] is None
    assert created["notes"] is None


def test_list_is_ordered_by_name_and_searchable_by_name(client: TestClient) -> None:
    create(client, name="Globex")
    create(client, name="acme")
    create(client, name="Initech", organization_type="recruiter")

    assert names(client.get("/api/organizations")) == ["acme", "Globex", "Initech"]
    assert names(client.get("/api/organizations", params={"q": "GLOB"})) == ["Globex"]
    assert names(client.get("/api/organizations", params={"organization_type": "recruiter"})) == [
        "Initech"
    ]


def test_name_is_required_and_type_must_be_a_known_value(client: TestClient) -> None:
    missing_name = client.post("/api/organizations", json={"organization_type": "company"})
    blank_name = client.post(
        "/api/organizations", json={"name": "   ", "organization_type": "company"}
    )
    bad_type = client.post("/api/organizations", json={"name": "Acme", "organization_type": "x"})

    assert missing_name.status_code == 422
    assert blank_name.status_code == 422
    assert bad_type.status_code == 422


def test_priority_outside_zero_to_five_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/organizations", json={"name": "Acme", "organization_type": "company", "priority": 9}
    )

    assert response.status_code == 422


def test_duplicate_organization_is_a_conflict(client: TestClient) -> None:
    create(client, name="Acme")

    response = client.post(
        "/api/organizations", json={"name": " ACME ", "organization_type": "company"}
    )

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_patch_changes_only_the_given_fields(client: TestClient) -> None:
    created = create(client, name="Acme", industry="Retail", location="Madrid")

    response = client.patch(
        f"/api/organizations/{created['id']}", json={"name": "Acme Corp", "location": None}
    )

    assert response.status_code == 200
    updated = response.json()
    assert updated["name"] == "Acme Corp"
    assert updated["location"] is None
    assert updated["industry"] == "Retail"


def test_patch_cannot_blank_the_name(client: TestClient) -> None:
    created = create(client)

    for name in ("", None):
        response = client.patch(f"/api/organizations/{created['id']}", json={"name": name})
        assert response.status_code == 422


def test_unknown_organization_is_not_found(client: TestClient) -> None:
    assert client.get("/api/organizations/999999").status_code == 404
    assert client.patch("/api/organizations/999999", json={"notes": "x"}).status_code == 404
    assert client.post("/api/organizations/999999/archive").status_code == 404
    assert client.post("/api/organizations/999999/restore").status_code == 404


def test_archived_organizations_are_hidden_from_the_list_until_restored(
    client: TestClient,
) -> None:
    acme = create(client, name="Acme")
    create(client, name="Globex")

    archived = client.post(f"/api/organizations/{acme['id']}/archive")

    assert archived.status_code == 200
    assert archived.json()["archived_at"] is not None
    assert names(client.get("/api/organizations")) == ["Globex"]
    assert names(client.get("/api/organizations", params={"include_archived": True})) == [
        "Acme",
        "Globex",
    ]

    restored = client.post(f"/api/organizations/{acme['id']}/restore")

    assert restored.status_code == 200
    assert restored.json()["archived_at"] is None
    assert names(client.get("/api/organizations")) == ["Acme", "Globex"]


def test_archiving_an_organization_with_active_applications_is_blocked(
    client: TestClient, db_session: Session
) -> None:
    acme = create(client, name="Acme")
    ApplicationService(db_session).create(organization_id=acme["id"], role="Backend Engineer")

    response = client.post(f"/api/organizations/{acme['id']}/archive")

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Acme has 1 active Application; archive them before archiving the Organization"
    }
    assert client.get(f"/api/organizations/{acme['id']}").json()["archived_at"] is None
