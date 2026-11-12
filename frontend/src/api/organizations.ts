import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, toValue, type MaybeRefOrGetter } from 'vue'

import { api, type Schemas } from './client'

export type Organization = Schemas['OrganizationRead']
export type OrganizationCreate = Schemas['OrganizationCreate']
export type OrganizationUpdate = Schemas['OrganizationUpdate']
export type OrganizationType = Schemas['OrganizationType']

/** Display labels for every OrganizationType, in the order forms offer them. */
export const ORGANIZATION_TYPE_LABELS: Record<OrganizationType, string> = {
  company: 'Company',
  recruiter: 'Recruiter',
  recruiting_firm: 'Recruiting firm',
  portal: 'Job portal',
}

export const ORGANIZATION_TYPES = Object.keys(ORGANIZATION_TYPE_LABELS) as OrganizationType[]

export interface OrganizationFilters {
  /** Matches name, industry or location. */
  q?: string
  organizationType?: OrganizationType
  includeArchived?: boolean
}

/** An API failure carrying the backend's `detail` message, ready to show to the user. */
export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

function toApiError(error: unknown, response: Response): ApiError {
  const detail = (error as { detail?: unknown } | undefined)?.detail
  if (typeof detail === 'string') return new ApiError(detail, response.status)
  if (Array.isArray(detail)) {
    // FastAPI validation errors: [{loc: [..., field], msg}, ...]
    const messages = detail.map((item: { loc?: unknown[]; msg?: string }) => {
      const field = item.loc?.at(-1)
      return field ? `${String(field)}: ${item.msg}` : (item.msg ?? 'invalid')
    })
    return new ApiError(messages.join('; '), response.status)
  }
  return new ApiError(`Request failed with HTTP ${response.status}`, response.status)
}

async function unwrap<T>(
  call: Promise<{ data?: T; error?: unknown; response: Response }>,
): Promise<T> {
  const { data, error, response } = await call
  if (error !== undefined || data === undefined) throw toApiError(error, response)
  return data
}

export function fetchOrganizations(filters: OrganizationFilters = {}): Promise<Organization[]> {
  const query: { q?: string; organization_type?: OrganizationType; include_archived?: boolean } = {}
  if (filters.q?.trim()) query.q = filters.q.trim()
  if (filters.organizationType) query.organization_type = filters.organizationType
  if (filters.includeArchived) query.include_archived = true
  return unwrap(api.GET('/api/organizations', { params: { query } }))
}

export function fetchOrganization(id: number): Promise<Organization> {
  return unwrap(
    api.GET('/api/organizations/{organization_id}', {
      params: { path: { organization_id: id } },
    }),
  )
}

export function createOrganization(body: OrganizationCreate): Promise<Organization> {
  return unwrap(api.POST('/api/organizations', { body }))
}

export function updateOrganization(id: number, body: OrganizationUpdate): Promise<Organization> {
  return unwrap(
    api.PATCH('/api/organizations/{organization_id}', {
      params: { path: { organization_id: id } },
      body,
    }),
  )
}

export function archiveOrganization(id: number): Promise<Organization> {
  return unwrap(
    api.POST('/api/organizations/{organization_id}/archive', {
      params: { path: { organization_id: id } },
    }),
  )
}

export function restoreOrganization(id: number): Promise<Organization> {
  return unwrap(
    api.POST('/api/organizations/{organization_id}/restore', {
      params: { path: { organization_id: id } },
    }),
  )
}

const ORGANIZATIONS_KEY = ['organizations'] as const

/** Organizations matching `filters` (reactive), ordered by name. Keeps the previous list while a new search loads. */
export function useOrganizations(filters: MaybeRefOrGetter<OrganizationFilters> = {}) {
  return useQuery({
    queryKey: computed(() => [...ORGANIZATIONS_KEY, 'list', { ...toValue(filters) }] as const),
    queryFn: () => fetchOrganizations(toValue(filters)),
    placeholderData: keepPreviousData,
  })
}

/** One Organization; disabled while `id` is undefined. */
export function useOrganization(id: MaybeRefOrGetter<number | undefined>) {
  return useQuery({
    queryKey: computed(() => [...ORGANIZATIONS_KEY, 'detail', toValue(id)] as const),
    queryFn: () => fetchOrganization(toValue(id)!),
    enabled: computed(() => toValue(id) !== undefined),
  })
}

function useOrganizationMutation<TVariables>(
  mutationFn: (variables: TVariables) => Promise<Organization>,
) {
  const queryClient = useQueryClient()
  return useMutation<Organization, ApiError, TVariables>({
    mutationFn,
    onSuccess: (organization) => {
      queryClient.setQueryData([...ORGANIZATIONS_KEY, 'detail', organization.id], organization)
      return queryClient.invalidateQueries({ queryKey: [...ORGANIZATIONS_KEY, 'list'] })
    },
  })
}

export function useCreateOrganization() {
  return useOrganizationMutation(createOrganization)
}

export function useUpdateOrganization() {
  return useOrganizationMutation(({ id, changes }: { id: number; changes: OrganizationUpdate }) =>
    updateOrganization(id, changes),
  )
}

/** Fails with an ApiError (status 409) when the Organization has active Applications. */
export function useArchiveOrganization() {
  return useOrganizationMutation(archiveOrganization)
}

export function useRestoreOrganization() {
  return useOrganizationMutation(restoreOrganization)
}
