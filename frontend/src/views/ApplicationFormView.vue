<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'

import { useApplication, type ApplicationDetail } from '@/api/applications'
import ApplicationForm from '@/components/ApplicationForm.vue'
import PageHeader from '@/components/PageHeader.vue'

/** Create an Application (no `id`) or edit the one with `id`. */
const props = defineProps<{ id?: string }>()

const router = useRouter()
const applicationId = computed(() => (props.id === undefined ? undefined : Number(props.id)))
const { data: application, isPending, error } = useApplication(applicationId)

const title = computed(() =>
  applicationId.value === undefined
    ? 'New Application'
    : application.value
      ? `Edit ${application.value.role} at ${application.value.organization.name}`
      : 'Edit Application',
)

function openDetail(saved: ApplicationDetail) {
  void router.push(`/applications/${saved.id}`)
}

function cancel() {
  void router.push(
    applicationId.value === undefined ? '/applications' : `/applications/${applicationId.value}`,
  )
}
</script>

<template>
  <PageHeader :title="title" />
  <ApplicationForm v-if="applicationId === undefined" @saved="openDetail" @cancel="cancel" />
  <p v-else-if="isPending" class="text-muted-foreground">Loading Application…</p>
  <p v-else-if="error" role="alert" class="text-destructive">{{ error.message }}</p>
  <ApplicationForm
    v-else-if="application"
    :key="application.id"
    :application="application"
    @saved="openDetail"
    @cancel="cancel"
  />
</template>
