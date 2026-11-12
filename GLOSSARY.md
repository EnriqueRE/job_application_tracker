# Job Application Tracker

A personal, single-user tracker for a job search: the opportunities pursued, where each one stands, and the material needed to prepare for interviews.

## Language

### Pipeline

**Application**:
One job opportunity being pursued at one Organization, from first being saved through to its outcome.
_Avoid_: Job, vacancy, opportunity, posting

**Organization**:
A company, recruiter, recruiting firm, or job portal that an Application is with.
_Avoid_: Company (when the kind is not known), employer

**Application Event**:
A dated entry in an Application's timeline (applied, screening, interview, follow-up, rejection, note, …).
_Avoid_: Activity, log entry, history item

**Pipeline Status**:
The stage an Application is currently in. It is derived from the most recent status-bearing Application Event unless a Status Override is in effect.
_Avoid_: State, stage

**Status Override**:
A Pipeline Status set by hand that events no longer replace until the override is cleared.

**Application Notes**:
General remarks about an Application that are not interview preparation, such as referrals, salary hints and logistics.
_Avoid_: Notes (unqualified), comments

### Interview preparation

**Job Description**:
The posting text as it was captured for an Application, kept because the original posting often disappears. Each Application has at most one. It holds only the posting itself, not Application metadata such as status or URL.
_Avoid_: JD file, posting, vacancy text

**Interview Notes**:
The candidate's own preparation material for an Application, such as questions to ask, talking points and interviewer names. It is kept apart from the Job Description and from Application Notes.
_Avoid_: Prep notes, notes (unqualified)
