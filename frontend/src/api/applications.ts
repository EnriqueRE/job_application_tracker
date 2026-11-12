import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, toValue, type MaybeRefOrGetter } from 'vue'

import { api, type Schemas } from './client'
import { ApiError, unwrap } from './errors'

export type Application = Schemas['ApplicationRead']
export type ApplicationDetail = Schemas['ApplicationDetail']
export type ApplicationUpdate = Schemas['ApplicationUpdate']
export type ApplicationStatus = Schemas['ApplicationStatus']
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
