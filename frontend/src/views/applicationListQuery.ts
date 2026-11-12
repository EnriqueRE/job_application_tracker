import type { LocationQuery, LocationQueryRaw } from 'vue-router'

import {
  APPLICATION_STATUSES,
  type ApplicationFilters,
  type ApplicationStatus,
} from '@/api/applications'

/** Columns of the Applications list that can be sorted. */
export const SORTABLE_COLUMNS = [
  'organization',
  'role',
  'status',
  'applied_at',
  'next_action_at',
] as const
export type SortColumn = (typeof SORTABLE_COLUMNS)[number]

export interface ListSort {
  column: SortColumn
  desc: boolean
}

/**
 * Everything the Applications list shows, as kept in the URL query string so it
 * survives reloads and back/forward:
 * `?organization=&role=&status=offer&status=applied&archived=true&sort=role&order=asc`.
 */
export interface ApplicationListQuery {
  organization: string
  role: string
  statuses: ApplicationStatus[]
  includeArchived: boolean
  sort: ListSort
}

export const DEFAULT_SORT: ListSort = { column: 'applied_at', desc: true }

function all(value: LocationQuery[string] | undefined): string[] {
  if (value == null) return []
  return (Array.isArray(value) ? value : [value]).filter((item): item is string => item != null)
}

function first(value: LocationQuery[string] | undefined): string | undefined {
  return all(value)[0]
}

export function parseListQuery(query: LocationQuery): ApplicationListQuery {
  const column = first(query.sort)
  const sort: ListSort = SORTABLE_COLUMNS.includes(column as SortColumn)
    ? { column: column as SortColumn, desc: first(query.order) === 'desc' }
    : DEFAULT_SORT
  return {
    organization: first(query.organization) ?? '',
    role: first(query.role) ?? '',
    statuses: all(query.status).filter((status): status is ApplicationStatus =>
      APPLICATION_STATUSES.includes(status as ApplicationStatus),
    ),
    includeArchived: first(query.archived) === 'true',
    sort,
  }
}

/** The URL query for `list`, leaving out empty filters and the default sort. */
export function serializeListQuery(list: ApplicationListQuery): LocationQueryRaw {
  const query: LocationQueryRaw = {}
  if (list.organization) query.organization = list.organization
  if (list.role) query.role = list.role
  if (list.statuses.length) {
    query.status = list.statuses.length === 1 ? list.statuses[0] : list.statuses
  }
  if (list.includeArchived) query.archived = 'true'
  if (list.sort.column !== DEFAULT_SORT.column || list.sort.desc !== DEFAULT_SORT.desc) {
    query.sort = list.sort.column
    query.order = list.sort.desc ? 'desc' : 'asc'
  }
  return query
}

/** The API filters a list query asks for. */
export function toApiFilters(list: ApplicationListQuery): ApplicationFilters {
  return {
    organization: list.organization,
    role: list.role,
    statuses: list.statuses,
    includeArchived: list.includeArchived,
  }
}
