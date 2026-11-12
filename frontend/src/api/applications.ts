import { keepPreviousData, useQuery } from '@tanstack/vue-query'
import { computed, toValue, type MaybeRefOrGetter } from 'vue'

import { api, type Schemas } from './client'
import { unwrap } from './errors'

export type Application = Schemas['ApplicationRead']
export type ApplicationStatus = Schemas['ApplicationStatus']
export type StatusCount = Schemas['StatusCount']

/** Display labels for every Pipeline Status, in pipeline order. */
export const APPLICATION_STATUS_LABELS: Record<ApplicationStatus, string> = {
  saved: 'Saved',
  applied: 'Applied',
  screening: 'Screening',
  interview: 'Interview',
  technical_interview: 'Technical interview',
  final_interview: 'Final interview',
  offer: 'Offer',
  rejected: 'Rejected',
  withdrawn: 'Withdrawn',
  closed: 'Closed',
  no_response: 'No response',
}

export const APPLICATION_STATUSES = Object.keys(APPLICATION_STATUS_LABELS) as ApplicationStatus[]

export interface ApplicationFilters {
  /** Case-insensitive substring of the Organization name. */
  organization?: string
  /** Case-insensitive substring of the role. */
  role?: string
  /** Keep Applications in any of these Pipeline Statuses (all when empty). */
  statuses?: ApplicationStatus[]
  includeArchived?: boolean
}

/** `GET /api/applications` */
export function fetchApplications(filters: ApplicationFilters = {}): Promise<Application[]> {
  const query: {
    organization?: string
    role?: string
    status?: ApplicationStatus[]
    include_archived?: boolean
  } = {}
  if (filters.organization?.trim()) query.organization = filters.organization.trim()
  if (filters.role?.trim()) query.role = filters.role.trim()
  if (filters.statuses?.length) query.status = filters.statuses
  if (filters.includeArchived) query.include_archived = true
  return unwrap(api.GET('/api/applications', { params: { query } }))
}

/** All Application queries live under this key; invalidate it after any Application change. */
export const APPLICATIONS_KEY = ['applications'] as const

/** Applications matching `filters` (reactive). Keeps the previous list while a new one loads. */
export function useApplications(filters: MaybeRefOrGetter<ApplicationFilters> = {}) {
  return useQuery({
    queryKey: computed(() => [...APPLICATIONS_KEY, 'list', { ...toValue(filters) }] as const),
    queryFn: () => fetchApplications(toValue(filters)),
    placeholderData: keepPreviousData,
  })
}

/** `GET /api/applications/status-counts`: all Pipeline Statuses in pipeline order. */
export function fetchStatusCounts(): Promise<StatusCount[]> {
  return unwrap(api.GET('/api/applications/status-counts'))
}

/** How many non-archived Applications are in each Pipeline Status. */
export function useStatusCounts() {
  return useQuery({ queryKey: [...APPLICATIONS_KEY, 'status-counts'], queryFn: fetchStatusCounts })
}

/** `GET /api/applications/due`: overdue or due within a week, soonest first. */
export function fetchDueApplications(): Promise<Application[]> {
  return unwrap(api.GET('/api/applications/due'))
}

/** Non-archived Applications whose next action is overdue or due within a week. */
export function useDueApplications() {
  return useQuery({ queryKey: [...APPLICATIONS_KEY, 'due'], queryFn: fetchDueApplications })
}
