import type { Schemas } from '@/api/client'

type Organization = Schemas['OrganizationRead']

let nextId = 1

/** An OrganizationRead as the API returns it, with overridable fields. */
export function makeOrganization(fields: Partial<Organization> = {}): Organization {
  const id = fields.id ?? nextId++
  return {
    id,
    name: 'Acme',
    organization_type: 'company',
    industry: null,
    location: null,
    priority: 3,
    website_url: null,
    career_url: null,
    contact_url: null,
    notes: null,
    archived_at: null,
    created_at: '2026-11-01T10:00:00Z',
    updated_at: '2026-11-01T10:00:00Z',
    ...fields,
  }
}
