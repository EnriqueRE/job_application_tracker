import type { Schemas } from '@/api/client'

type Application = Schemas['ApplicationRead']

let nextId = 1

/** An ApplicationRead as the API returns it, with overridable fields. */
export function makeApplication(fields: Partial<Application> = {}): Application {
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
    ...fields,
  }
}
