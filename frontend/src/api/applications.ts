import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, toValue, type MaybeRefOrGetter } from 'vue'

import { api, type Schemas } from './client'
import { ApiError, unwrap } from './errors'

export type Application = Schemas['ApplicationRead']
export type ApplicationDetail = Schemas['ApplicationDetail']
export type ApplicationCreate = Schemas['ApplicationCreate']
export type ApplicationUpdate = Schemas['ApplicationUpdate']
export type ApplicationStatus = Schemas['ApplicationStatus']
export type StatusCount = Schemas['StatusCount']
export type WorkArrangement = Schemas['WorkArrangement']

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

export const WORK_ARRANGEMENT_LABELS: Record<WorkArrangement, string> = {
  remote: 'Remote',
  hybrid: 'Hybrid',
  onsite: 'On-site',
  unspecified: 'Unspecified',
}

/** Root query key for everything Application-shaped; invalidate it after any change. */
export const APPLICATIONS_KEY = ['applications'] as const

export function applicationDetailKey(id: number | undefined) {
  return [...APPLICATIONS_KEY, 'detail', id] as const
}

export function fetchApplication(id: number): Promise<ApplicationDetail> {
  return unwrap(
    api.GET('/api/applications/{application_id}', {
      params: { path: { application_id: id } },
    }),
  )
}

export function updateApplication(id: number, body: ApplicationUpdate): Promise<ApplicationDetail> {
  return unwrap(
    api.PATCH('/api/applications/{application_id}', {
      params: { path: { application_id: id } },
      body,
    }),
  )
}

export function archiveApplication(id: number): Promise<Application> {
  return unwrap(
    api.POST('/api/applications/{application_id}/archive', {
      params: { path: { application_id: id } },
    }),
  )
}

export function restoreApplication(id: number): Promise<Application> {
  return unwrap(
    api.POST('/api/applications/{application_id}/restore', {
      params: { path: { application_id: id } },
    }),
  )
}

/** One Application with its long texts and timeline; disabled while `id` is undefined. */
export function useApplication(id: MaybeRefOrGetter<number | undefined>) {
  return useQuery({
    queryKey: computed(() => applicationDetailKey(toValue(id))),
    queryFn: () => fetchApplication(toValue(id)!),
    enabled: computed(() => toValue(id) !== undefined),
  })
}

/** PATCH an Application (`{id, changes}`); the detail cache takes the response. */
export function useUpdateApplication() {
  const queryClient = useQueryClient()
  return useMutation<ApplicationDetail, ApiError, { id: number; changes: ApplicationUpdate }>({
    mutationFn: ({ id, changes }) => updateApplication(id, changes),
    onSuccess: (application) => {
      queryClient.setQueryData(applicationDetailKey(application.id), application)
      return queryClient.invalidateQueries({
        queryKey: APPLICATIONS_KEY,
        predicate: (query) => query.queryKey[1] !== 'detail',
      })
    },
  })
}

function useApplicationAction(action: (id: number) => Promise<Application>) {
  const queryClient = useQueryClient()
  return useMutation<Application, ApiError, number>({
    mutationFn: action,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: APPLICATIONS_KEY }),
  })
}

export function useArchiveApplication() {
  return useApplicationAction(archiveApplication)
}

export function useRestoreApplication() {
  return useApplicationAction(restoreApplication)
}

export function createApplication(body: ApplicationCreate): Promise<ApplicationDetail> {
  return unwrap(api.POST('/api/applications', { body }))
}

/** POST a new Application; the detail cache takes the response and lists refresh. */
export function useCreateApplication() {
  const queryClient = useQueryClient()
  return useMutation<ApplicationDetail, ApiError, ApplicationCreate>({
    mutationFn: createApplication,
    onSuccess: (application) => {
      queryClient.setQueryData(applicationDetailKey(application.id), application)
      return queryClient.invalidateQueries({
        queryKey: APPLICATIONS_KEY,
        predicate: (query) => query.queryKey[1] !== 'detail',
      })
    },
  })
}

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

/**
 * `GET /api/applications/due`: overdue or due within a week of `today` (a local
 * `YYYY-MM-DD` date, so the browser's time zone decides what "today" is), soonest first.
 */
export function fetchDueApplications(today: string): Promise<Application[]> {
  return unwrap(api.GET('/api/applications/due', { params: { query: { today } } }))
}

/** Non-archived Applications whose next action is overdue or due within a week of `today`. */
export function useDueApplications(today: string) {
  return useQuery({
    queryKey: [...APPLICATIONS_KEY, 'due', today],
    queryFn: () => fetchDueApplications(today),
  })
}
