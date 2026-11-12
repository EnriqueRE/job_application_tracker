"""Errors raised by the domain services, for the API layer to map to HTTP responses."""


class DomainError(Exception):
    """Base class for errors the services raise on purpose."""


class NotFoundError(DomainError, LookupError):
    """The requested record does not exist (maps to 404)."""


class ConflictError(DomainError):
    """The change clashes with existing data (maps to 409)."""


class DuplicateOrganizationError(ConflictError):
    """An Organization of the same type and normalized name already exists."""


class OrganizationInUseError(ConflictError):
    """The Organization still has Applications: it cannot be deleted, nor archived while any
    of them is active."""


class InvalidValueError(DomainError, ValueError):
    """A field value is outside what the domain allows (maps to 422)."""
