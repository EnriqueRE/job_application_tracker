<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import {
  APPLICATION_STATUS_LABELS,
  WORK_ARRANGEMENT_LABELS,
  useApplication,
  useUpdateApplication,
  type ApplicationUpdate,
} from '@/api/applications'
import ApplicationTimeline from '@/components/ApplicationTimeline.vue'
import MarkdownSection from '@/components/MarkdownSection.vue'
import PageHeader from '@/components/PageHeader.vue'
import StatusOverrideControl from '@/components/StatusOverrideControl.vue'

const route = useRoute()
const id = computed(() => Number(route.params.id))

const { data: application, error, isPending } = useApplication(id)
const update = useUpdateApplication()

type MarkdownField = 'job_description' | 'interview_notes' | 'application_notes'

const sections: { field: MarkdownField; title: string }[] = [
  { field: 'job_description', title: 'Job Description' },
  { field: 'interview_notes', title: 'Interview Notes' },
  { field: 'application_notes', title: 'Application Notes' },
]

function saveField(field: MarkdownField) {
  return (value: string | null) => {
    const changes: ApplicationUpdate = { [field]: value }
    return update.mutateAsync({ id: id.value, changes })
  }
}

const facts = computed(() => {
  const app = application.value
  if (!app) return []
  return [
    { label: 'Location', value: app.location },
    { label: 'Work arrangement', value: WORK_ARRANGEMENT_LABELS[app.work_arrangement] },
    { label: 'Source', value: app.vacancy_source },
    { label: 'Vacancy age', value: app.vacancy_age },
    { label: 'Applied', value: app.applied_at },
    { label: 'Next action', value: app.next_action_at },
  ].filter((fact) => fact.value)
})
</script>

<template>
  <p v-if="isPending" class="text-muted-foreground">Loading…</p>
  <p v-else-if="error" role="alert" class="text-destructive">{{ error.message }}</p>
  <article v-else-if="application" class="min-w-0 space-y-8">
    <div>
      <PageHeader :title="application.role" />
      <div class="-mt-4 space-y-3">
        <p class="text-lg">
          <RouterLink
            :to="`/organizations/${application.organization.id}`"
            class="font-medium underline-offset-4 hover:underline"
          >
            {{ application.organization.name }}
          </RouterLink>
        </p>
        <p data-testid="pipeline-status" class="flex flex-wrap items-center gap-2">
          <span class="rounded-full bg-secondary px-3 py-1 text-sm font-medium">
            {{ APPLICATION_STATUS_LABELS[application.current_status] }}
          </span>
          <span
            v-if="application.status_overridden"
            class="rounded-full border border-amber-500 px-2 py-0.5 text-xs text-amber-700 dark:text-amber-400"
            title="Set by hand; Application Events will not change it until cleared"
          >
            Status Override
          </span>
          <span v-if="application.archived_at" class="text-sm text-muted-foreground">
            Archived
          </span>
        </p>
        <StatusOverrideControl :application="application" />
        <dl class="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm sm:grid-cols-[auto_1fr_auto_1fr]">
          <template v-for="fact in facts" :key="fact.label">
            <dt class="text-muted-foreground">{{ fact.label }}</dt>
            <dd class="min-w-0 break-words">{{ fact.value }}</dd>
          </template>
        </dl>
        <p v-if="application.vacancy_url" class="min-w-0 text-sm break-all">
          <a
            :href="application.vacancy_url"
            target="_blank"
            rel="noopener noreferrer"
            class="text-primary underline underline-offset-4"
          >
            {{ application.vacancy_url }}
          </a>
        </p>
      </div>
    </div>

    <MarkdownSection
      v-for="item in sections"
      :key="item.field"
      :title="item.title"
      :source="application[item.field]"
      :save="saveField(item.field)"
    />

    <ApplicationTimeline :application="application" />
  </article>
</template>
