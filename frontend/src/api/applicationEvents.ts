import { useMutation, useQueryClient } from '@tanstack/vue-query'
import { toValue, type MaybeRefOrGetter } from 'vue'

import { APPLICATIONS_KEY, type ApplicationStatus } from './applications'
import { api, type Schemas } from './client'
import { ApiError, unwrap } from './errors'

export type ApplicationEventType = Schemas['ApplicationEventType']
export type ApplicationEventCreate = Schemas['ApplicationEventCreate']
export type ApplicationEventUpdate = Schemas['ApplicationEventUpdate']
export type ApplicationEventMutation = Schemas['ApplicationEventMutation']
export type ApplicationStatusRead = Schemas['ApplicationStatusRead']

/** Display labels for every Application Event type, in the order forms offer them. */
export const APPLICATION_EVENT_TYPE_LABELS: Record<ApplicationEventType, string> = {
  note: 'Note',
  saved: 'Saved',
  applied: 'Applied',
  contacted: 'Contacted',
  screening: 'Screening',
  interview_scheduled: 'Interview scheduled',
  interview_completed: 'Interview completed',
  technical_interview: 'Technical interview',
  final_interview: 'Final interview',
  follow_up: 'Follow-up',
  offer: 'Offer',
  rejected: 'Rejected',
  withdrawn: 'Withdrawn',
  closed: 'Closed',
  no_response: 'No response',
}

export const APPLICATION_EVENT_TYPES = Object.keys(
  APPLICATION_EVENT_TYPE_LABELS,
) as ApplicationEventType[]

export function addApplicationEvent(
  applicationId: number,
  body: ApplicationEventCreate,
): Promise<ApplicationEventMutation> {
  return unwrap(
    api.POST('/api/applications/{application_id}/events', {
      params: { path: { application_id: applicationId } },
      body,
    }),
  )
}

export function updateApplicationEvent(
  applicationId: number,
  eventId: number,
  body: ApplicationEventUpdate,
): Promise<ApplicationEventMutation> {
  return unwrap(
    api.PATCH('/api/applications/{application_id}/events/{event_id}', {
      params: { path: { application_id: applicationId, event_id: eventId } },
      body,
    }),
  )
}

export function deleteApplicationEvent(
  applicationId: number,
  eventId: number,
): Promise<ApplicationStatusRead> {
  return unwrap(
    api.DELETE('/api/applications/{application_id}/events/{event_id}', {
      params: { path: { application_id: applicationId, event_id: eventId } },
    }),
  )
}

export function setStatusOverride(
  applicationId: number,
  status: ApplicationStatus,
): Promise<ApplicationStatusRead> {
  return unwrap(
    api.PUT('/api/applications/{application_id}/status-override', {
      params: { path: { application_id: applicationId } },
      body: { status },
    }),
  )
}

export function clearStatusOverride(applicationId: number): Promise<ApplicationStatusRead> {
  return unwrap(
    api.DELETE('/api/applications/{application_id}/status-override', {
      params: { path: { application_id: applicationId } },
    }),
  )
}

/** A mutation on one Application's timeline or status; refreshes every Application query after. */
function useApplicationChange<TResult, TVariables>(
  applicationId: MaybeRefOrGetter<number>,
  change: (applicationId: number, variables: TVariables) => Promise<TResult>,
) {
  const queryClient = useQueryClient()
  return useMutation<TResult, ApiError, TVariables>({
    mutationFn: (variables) => change(toValue(applicationId), variables),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: APPLICATIONS_KEY }),
  })
}

export function useAddApplicationEvent(applicationId: MaybeRefOrGetter<number>) {
  return useApplicationChange(applicationId, addApplicationEvent)
}

/** Variables: `{eventId, changes}`. */
export function useUpdateApplicationEvent(applicationId: MaybeRefOrGetter<number>) {
  return useApplicationChange(
    applicationId,
    (id, { eventId, changes }: { eventId: number; changes: ApplicationEventUpdate }) =>
      updateApplicationEvent(id, eventId, changes),
  )
}

/** Variables: the event id. */
export function useDeleteApplicationEvent(applicationId: MaybeRefOrGetter<number>) {
  return useApplicationChange(applicationId, deleteApplicationEvent)
}

/** Variables: the Pipeline Status to pin. */
export function useSetStatusOverride(applicationId: MaybeRefOrGetter<number>) {
  return useApplicationChange(applicationId, setStatusOverride)
}

export function useClearStatusOverride(applicationId: MaybeRefOrGetter<number>) {
  return useApplicationChange<ApplicationStatusRead, void>(applicationId, (id) =>
    clearStatusOverride(id),
  )
}
