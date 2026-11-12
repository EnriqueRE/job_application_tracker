<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'

import { useOrganization } from '@/api/organizations'
import OrganizationForm from '@/components/OrganizationForm.vue'
import PageHeader from '@/components/PageHeader.vue'

/** Create an Organization (no `id`) or edit the one with `id`. */
const props = defineProps<{ id?: string }>()

const router = useRouter()
const organizationId = computed(() => (props.id === undefined ? undefined : Number(props.id)))
const { data: organization, isPending, error } = useOrganization(organizationId)

const title = computed(() =>
  organizationId.value === undefined
    ? 'New Organization'
    : organization.value
      ? `Edit ${organization.value.name}`
      : 'Edit Organization',
)

function backToList() {
  void router.push('/organizations')
}
</script>

<template>
  <PageHeader :title="title" />
  <OrganizationForm v-if="organizationId === undefined" @saved="backToList" @cancel="backToList" />
  <p v-else-if="isPending" class="text-muted-foreground">Loading Organization…</p>
  <p v-else-if="error" role="alert" class="text-destructive">{{ error.message }}</p>
  <OrganizationForm
    v-else-if="organization"
    :key="organization.id"
    :organization="organization"
    @saved="backToList"
    @cancel="backToList"
  />
</template>
