"""OrganizationService: create, read, search, update, archive/restore and delete Organizations."""

import pytest
from sqlalchemy.orm import Session

from tracker.domain import OrganizationType
from tracker.services import (
    DuplicateOrganizationError,
    InvalidValueError,
    NotFoundError,
    OrganizationService,
)


@pytest.fixture
def organizations(db_session: Session) -> OrganizationService:
    return OrganizationService(db_session)


def test_created_organization_has_a_normalized_name_and_defaults(
    organizations: OrganizationService,
) -> None:
    created = organizations.create(name="  DataDog  Inc ", organization_type=OrganizationType.COMPANY)

    fetched = organizations.get(created.id)
    assert fetched.name == "  DataDog  Inc "
    assert fetched.normalized_name == "datadog inc"
    assert fetched.priority == 3
    assert fetched.archived_at is None
    assert fetched.created_at is not None


def test_getting_a_missing_organization_raises_not_found(
    organizations: OrganizationService,
) -> None:
    with pytest.raises(NotFoundError):
        organizations.get(999_999)


def test_same_type_and_normalized_name_is_a_duplicate(organizations: OrganizationService) -> None:
    organizations.create(name="Acme", organization_type=OrganizationType.COMPANY)

    with pytest.raises(DuplicateOrganizationError):
        organizations.create(name=" ACME ", organization_type=OrganizationType.COMPANY)

    # A different type with the same name is a different Organization.
    portal = organizations.create(name="acme", organization_type=OrganizationType.PORTAL)
    assert portal.id is not None


def test_search_matches_name_industry_or_location_and_filters_by_type(
    organizations: OrganizationService,
) -> None:
    datadog = organizations.create(
        name="Datadog", organization_type=OrganizationType.COMPANY, industry="Observability"
    )
    indeed = organizations.create(
        name="Indeed", organization_type=OrganizationType.PORTAL, location="Austin"
    )
    acme = organizations.create(name="Acme", organization_type=OrganizationType.RECRUITER)

    assert organizations.search() == [acme, datadog, indeed]
    assert organizations.search("observ") == [datadog]
    assert organizations.search("AUSTIN") == [indeed]
    assert organizations.search("data") == [datadog]
    assert organizations.search(organization_type=OrganizationType.PORTAL) == [indeed]


def test_renaming_an_organization_renormalizes_its_name(
    organizations: OrganizationService,
) -> None:
    organization = organizations.create(name="Acme", organization_type=OrganizationType.COMPANY)

    updated = organizations.update(organization.id, name="  ACME  Corp", priority=5)

    assert updated.normalized_name == "acme corp"
    assert updated.priority == 5
    assert organizations.search("corp") == [organization]


def test_renaming_onto_an_existing_organization_is_a_duplicate(
    organizations: OrganizationService,
) -> None:
    organizations.create(name="Acme", organization_type=OrganizationType.COMPANY)
    other = organizations.create(name="Globex", organization_type=OrganizationType.COMPANY)

    with pytest.raises(DuplicateOrganizationError):
        organizations.update(other.id, name="acme")


def test_updating_an_unknown_field_is_rejected(organizations: OrganizationService) -> None:
    organization = organizations.create(name="Acme", organization_type=OrganizationType.COMPANY)

    with pytest.raises(InvalidValueError):
        organizations.update(organization.id, normalized_name="hacked")


def test_archived_organizations_are_hidden_until_restored(
    organizations: OrganizationService,
) -> None:
    acme = organizations.create(name="Acme", organization_type=OrganizationType.COMPANY)
    globex = organizations.create(name="Globex", organization_type=OrganizationType.COMPANY)

    organizations.archive(acme.id)

    assert acme.archived_at is not None
    assert organizations.search() == [globex]
    assert organizations.search(include_archived=True) == [acme, globex]

    organizations.restore(acme.id)

    assert acme.archived_at is None
    assert organizations.search() == [acme, globex]


@pytest.mark.parametrize("priority", [-1, 6])
def test_priority_outside_zero_to_five_is_rejected(
    organizations: OrganizationService, priority: int
) -> None:
    with pytest.raises(InvalidValueError):
        organizations.create(
            name="Acme", organization_type=OrganizationType.COMPANY, priority=priority
        )
