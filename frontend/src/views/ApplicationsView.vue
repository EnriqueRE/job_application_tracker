<script setup lang="ts">
import {
  createSortedRowModel,
  FlexRender,
  rowSortingFeature,
  sortFn_basic,
  sortFn_text,
  tableFeatures,
  useTable,
  type ColumnDef,
  type SortingState,
  type Updater,
} from '@tanstack/vue-table'
import { ArrowDown, ArrowUp, ArrowUpDown, Plus } from 'lucide-vue-next'
import { computed, h } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import {
  APPLICATION_STATUS_LABELS,
  APPLICATION_STATUSES,
  useApplications,
  type Application,
} from '@/api/applications'
import DueSoonStrip from '@/components/DueSoonStrip.vue'
import PageHeader from '@/components/PageHeader.vue'
import PipelineStatusCounts from '@/components/PipelineStatusCounts.vue'
import { Button } from '@/components/ui/button'

import {
  parseListQuery,
  serializeListQuery,
  toApiFilters,
  type ApplicationListQuery,
  type SortColumn,
} from './applicationListQuery'

const route = useRoute()
const router = useRouter()
const listQuery = computed(() => parseListQuery(route.query))

/**
 * Navigate to the list with `changes` applied. Typing replaces the current history
 * entry so back/forward steps between deliberate changes, not keystrokes.
 */
function updateListQuery(changes: Partial<ApplicationListQuery>, { replace = false } = {}) {
  const query = serializeListQuery({ ...listQuery.value, ...changes })
  void (replace ? router.replace({ query }) : router.push({ query }))
}

function onTextFilter(field: 'organization' | 'role', event: Event) {
  updateListQuery({ [field]: (event.target as HTMLInputElement).value }, { replace: true })
}

const features = tableFeatures({
  rowSortingFeature,
  sortedRowModel: createSortedRowModel(),
  sortFns: { basic: sortFn_basic, text: sortFn_text },
})

type Column = ColumnDef<typeof features, Application> & { id: SortColumn }

const columns: Column[] = [
  {
    id: 'organization',
    header: 'Organization',
    accessorFn: (application) => application.organization.name,
    sortFn: 'text',
  },
  {
    id: 'role',
    header: 'Role',
    accessorFn: (application) => application.role,
    sortFn: 'text',
    cell: ({ row }) =>
      h('span', { class: 'inline-flex flex-wrap items-center gap-2' }, [
        h(
          RouterLink,
          { to: `/applications/${row.original.id}`, class: 'font-medium hover:underline' },
          () => row.original.role,
        ),
        row.original.archived_at
          ? h(
              'span',
              { class: 'rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground' },
              'Archived',
            )
          : null,
      ]),
  },
  {
    id: 'status',
    header: 'Pipeline Status',
    // Sort in pipeline order rather than alphabetically.
    accessorFn: (application) => APPLICATION_STATUSES.indexOf(application.current_status),
    sortFn: 'basic',
    cell: ({ row }) => APPLICATION_STATUS_LABELS[row.original.current_status],
  },
  {
    id: 'applied_at',
    header: 'Applied',
    accessorFn: (application) => application.applied_at ?? undefined,
    sortFn: 'text',
    sortUndefined: 'last',
  },
  {
    id: 'next_action_at',
    header: 'Next action',
    accessorFn: (application) => application.next_action_at ?? undefined,
    sortFn: 'text',
    sortUndefined: 'last',
  },
]

const sorting = computed<SortingState>(() => [
  { id: listQuery.value.sort.column, desc: listQuery.value.sort.desc },
])

function onSortingChange(updater: Updater<SortingState>) {
  const next = typeof updater === 'function' ? updater(sorting.value) : updater
  const [entry] = next
  if (entry) updateListQuery({ sort: { column: entry.id as SortColumn, desc: entry.desc } })
}

const applications = useApplications(() => toApiFilters(listQuery.value))
const emptyRows: Application[] = []
const data = computed(() => applications.data.value ?? emptyRows)

const table = useTable({
  features,
  columns,
  data,
  state: computed(() => ({ sorting: sorting.value })),
  onSortingChange,
  enableSortingRemoval: false,
  enableMultiSort: false,
  sortDescFirst: false,
})

function ariaSort(direction: false | 'asc' | 'desc') {
  if (!direction) return undefined
  return direction === 'asc' ? 'ascending' : 'descending'
}

function sortLabel(title: string, direction: false | 'asc' | 'desc') {
  if (!direction) return `Sort by ${title}`
  return `Sort by ${title}, currently ${direction === 'asc' ? 'ascending' : 'descending'}`
}
</script>

<template>
  <PageHeader title="Applications">
    <template #actions>
      <Button as-child>
        <RouterLink to="/applications/new">
          <Plus aria-hidden="true" />
          New Application
        </RouterLink>
      </Button>
    </template>
  </PageHeader>
  <DueSoonStrip />
  <PipelineStatusCounts
    :selected="listQuery.statuses"
    @select="(statuses) => updateListQuery({ statuses })"
  />
  <form class="mb-4 flex flex-wrap items-end gap-3" role="search" @submit.prevent>
    <label class="flex min-w-40 flex-1 flex-col gap-1 text-sm">
      <span class="font-medium">Organization</span>
      <input
        name="organization"
        type="search"
        class="h-9 rounded-md border bg-background px-3"
        :value="listQuery.organization"
        @input="onTextFilter('organization', $event)"
      />
    </label>
    <label class="flex min-w-40 flex-1 flex-col gap-1 text-sm">
      <span class="font-medium">Role</span>
      <input
        name="role"
        type="search"
        class="h-9 rounded-md border bg-background px-3"
        :value="listQuery.role"
        @input="onTextFilter('role', $event)"
      />
    </label>
    <label class="flex h-9 items-center gap-2 text-sm">
      <input
        name="archived"
        type="checkbox"
        class="size-4"
        :checked="listQuery.includeArchived"
        @change="updateListQuery({ includeArchived: ($event.target as HTMLInputElement).checked })"
      />
      Show archived
    </label>
  </form>
  <div class="overflow-x-auto rounded-md border">
    <table class="w-full text-sm">
      <thead class="bg-muted/50 text-left">
        <tr v-for="group in table.getHeaderGroups()" :key="group.id">
          <th
            v-for="header in group.headers"
            :key="header.id"
            class="px-3 py-2 font-medium whitespace-nowrap"
            :aria-sort="ariaSort(header.column.getIsSorted())"
          >
            <button
              type="button"
              class="inline-flex items-center gap-1 hover:underline"
              :aria-label="
                sortLabel(String(header.column.columnDef.header), header.column.getIsSorted())
              "
              @click="header.column.getToggleSortingHandler()?.($event)"
            >
              <FlexRender :header="header" />
              <ArrowUp
                v-if="header.column.getIsSorted() === 'asc'"
                aria-hidden="true"
                class="size-3.5"
              />
              <ArrowDown
                v-else-if="header.column.getIsSorted() === 'desc'"
                aria-hidden="true"
                class="size-3.5"
              />
              <ArrowUpDown v-else aria-hidden="true" class="size-3.5 text-muted-foreground" />
            </button>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in table.getRowModel().rows" :key="row.id" class="border-t">
          <td v-for="cell in row.getAllCells()" :key="cell.id" class="px-3 py-2">
            <FlexRender :cell="cell" />
          </td>
        </tr>
        <tr v-if="!table.getRowModel().rows.length" class="border-t">
          <td :colspan="columns.length" class="px-3 py-6 text-center text-muted-foreground">
            <template v-if="applications.isPending.value">Loading Applications…</template>
            <template v-else-if="applications.isError.value">
              Could not load Applications: {{ applications.error.value?.message }}
            </template>
            <template v-else>No Applications match these filters.</template>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
