<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import { useDueApplications } from '@/api/applications'
import { todayIsoDate } from '@/lib/dates'
import { cn } from '@/lib/utils'

const today = todayIsoDate()
const due = useDueApplications(today)

const items = computed(() =>
  (due.data.value ?? []).map((application) => {
    const date = application.next_action_at ?? ''
    return { application, date, overdue: date < today, isToday: date === today }
  }),
)
</script>

<template>
  <section v-if="items.length" aria-label="Due soon" class="mb-4">
    <h2 class="mb-2 text-sm font-medium text-muted-foreground">Due soon</h2>
    <ul class="flex gap-2 overflow-x-auto pb-1">
      <li v-for="{ application, date, overdue, isToday } in items" :key="application.id">
        <RouterLink
          :to="`/applications/${application.id}`"
          :class="
            cn(
              'flex w-56 shrink-0 flex-col rounded-md border px-3 py-2 text-sm hover:bg-accent',
              overdue && 'border-destructive/60 bg-destructive/10',
            )
          "
        >
          <span class="truncate font-medium">{{ application.organization.name }}</span>
          <span class="truncate">{{ application.role }}</span>
          <span
            :class="
              cn('text-xs', overdue ? 'font-semibold text-destructive' : 'text-muted-foreground')
            "
          >
            <template v-if="overdue">Overdue · {{ date }}</template>
            <template v-else-if="isToday">Today</template>
            <template v-else>{{ date }}</template>
          </span>
        </RouterLink>
      </li>
    </ul>
  </section>
</template>
