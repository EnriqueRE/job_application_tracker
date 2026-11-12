<script setup lang="ts">
import {
  APPLICATION_STATUSES,
  APPLICATION_STATUS_LABELS,
  useStatusCounts,
  type ApplicationStatus,
} from '@/api/applications'
import { cn } from '@/lib/utils'

const props = defineProps<{ selected: ApplicationStatus[] }>()
const emit = defineEmits<{ select: [statuses: ApplicationStatus[]] }>()

const counts = useStatusCounts()

/** Clicking a count adds its Pipeline Status to the filter, or removes it if already there. */
function toggle(status: ApplicationStatus) {
  const selected = props.selected.includes(status)
    ? props.selected.filter((s) => s !== status)
    : [...props.selected, status]
  emit(
    'select',
    APPLICATION_STATUSES.filter((s) => selected.includes(s)),
  )
}
</script>

<template>
  <ul
    v-if="counts.data.value"
    aria-label="Pipeline Status counts"
    class="mb-4 flex gap-2 overflow-x-auto pb-1"
  >
    <li v-for="{ status, count } in counts.data.value" :key="status" class="shrink-0">
      <button
        type="button"
        :aria-pressed="selected.includes(status)"
        :class="
          cn(
            'flex items-baseline gap-1.5 rounded-md border px-3 py-1.5 text-sm hover:bg-accent',
            selected.includes(status) &&
              'border-primary bg-primary text-primary-foreground hover:bg-primary/90',
            count === 0 && !selected.includes(status) && 'text-muted-foreground',
          )
        "
        @click="toggle(status)"
      >
        <span>{{ APPLICATION_STATUS_LABELS[status] }}</span>
        <span class="font-semibold tabular-nums">{{ count }}</span>
      </button>
    </li>
  </ul>
</template>
