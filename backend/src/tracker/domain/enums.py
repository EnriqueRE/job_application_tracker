"""Domain enum values, ported unchanged from JobTrack, and the event-to-status mapping."""

from enum import StrEnum


class OrganizationType(StrEnum):
    """Kinds of Organization an Application can be with."""

    COMPANY = "company"
    RECRUITER = "recruiter"
    RECRUITING_FIRM = "recruiting_firm"
    PORTAL = "portal"


class ApplicationStatus(StrEnum):
    """The Pipeline Status values, in pipeline order."""

    SAVED = "saved"
    APPLIED = "applied"
    SCREENING = "screening"
    INTERVIEW = "interview"
    TECHNICAL_INTERVIEW = "technical_interview"
    FINAL_INTERVIEW = "final_interview"
    OFFER = "offer"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    CLOSED = "closed"
    NO_RESPONSE = "no_response"


class WorkArrangement(StrEnum):
    """Where an Application expects the work to happen."""

    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"
    UNSPECIFIED = "unspecified"


class ApplicationEventType(StrEnum):
    """Kinds of Application Event in an Application's timeline."""

    SAVED = "saved"
    APPLIED = "applied"
    CONTACTED = "contacted"
    SCREENING = "screening"
    INTERVIEW_SCHEDULED = "interview_scheduled"
    INTERVIEW_COMPLETED = "interview_completed"
    TECHNICAL_INTERVIEW = "technical_interview"
    FINAL_INTERVIEW = "final_interview"
    FOLLOW_UP = "follow_up"
    OFFER = "offer"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    CLOSED = "closed"
    NO_RESPONSE = "no_response"
    NOTE = "note"


EVENT_STATUS: dict[ApplicationEventType, ApplicationStatus] = {
    ApplicationEventType.SAVED: ApplicationStatus.SAVED,
    ApplicationEventType.APPLIED: ApplicationStatus.APPLIED,
    ApplicationEventType.SCREENING: ApplicationStatus.SCREENING,
    ApplicationEventType.INTERVIEW_SCHEDULED: ApplicationStatus.INTERVIEW,
    ApplicationEventType.INTERVIEW_COMPLETED: ApplicationStatus.INTERVIEW,
    ApplicationEventType.TECHNICAL_INTERVIEW: ApplicationStatus.TECHNICAL_INTERVIEW,
    ApplicationEventType.FINAL_INTERVIEW: ApplicationStatus.FINAL_INTERVIEW,
    ApplicationEventType.OFFER: ApplicationStatus.OFFER,
    ApplicationEventType.REJECTED: ApplicationStatus.REJECTED,
    ApplicationEventType.WITHDRAWN: ApplicationStatus.WITHDRAWN,
    ApplicationEventType.CLOSED: ApplicationStatus.CLOSED,
    ApplicationEventType.NO_RESPONSE: ApplicationStatus.NO_RESPONSE,
}
"""Pipeline Status an event type implies. Types absent here (contacted, follow_up, note)
leave the Pipeline Status unchanged."""


def status_for_event(event_type: ApplicationEventType) -> ApplicationStatus | None:
    """Return the Pipeline Status an Application Event of this type implies, if any."""
    return EVENT_STATUS.get(event_type)
