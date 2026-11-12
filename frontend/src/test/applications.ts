import type { Schemas } from '@/api/client'

type ApplicationDetail = Schemas['ApplicationDetail']
type TimelineEvent = Schemas['ApplicationTimelineEvent']

let nextId = 1

/** An ApplicationDetail as the API returns it, with overridable fields. */
export function makeApplicationDetail(fields: Partial<ApplicationDetail> = {}): ApplicationDetail {
  const id = fields.id ?? nextId++
  return {
    id,
    organization: { id: 1, name: 'Acme', organization_type: 'company' },
    role: 'Backend Engineer',
    location: null,
    work_arrangement: 'unspecified',
    vacancy_source: null,
    vacancy_url: null,
    vacancy_age: null,
    applied_at: null,
    next_action_at: null,
    current_status: 'saved',
    status_overridden: false,
    created_at: '2026-11-01T10:00:00Z',
    updated_at: '2026-11-01T10:00:00Z',
    archived_at: null,
    job_description: null,
    interview_notes: null,
    application_notes: null,
    events: [],
    ...fields,
  }
}

/** An ApplicationTimelineEvent, with overridable fields. */
export function makeTimelineEvent(fields: Partial<TimelineEvent> = {}): TimelineEvent {
  return {
    id: fields.id ?? nextId++,
    event_type: 'note',
    occurred_at: '2026-11-02T09:00:00Z',
    notes: null,
    resulting_status: null,
    created_at: '2026-11-02T09:00:00Z',
    ...fields,
  }
}
