<script setup lang="ts">
import { computed, ref } from 'vue'

import {
  ORGANIZATION_TYPE_LABELS,
  useArchiveOrganization,
  useOrganizations,
  useRestoreOrganization,
  type Organization,
} from '@/api/organizations'
import PageHeader from '@/components/PageHeader.vue'
import { Button, buttonVariants } from '@/components/ui/button'

const search = ref('')
const includeArchived = ref(false)

const {
  data: organizations,
  isPending,
  error,
} = useOrganizations(() => ({
  q: search.value,
  includeArchived: includeArchived.value,
}))

const archive = useArchiveOrganization()
const restore = useRestoreOrganization()

const actionError = computed(() => archive.error.value?.message ?? restore.error.value?.message)
const busy = computed(() => archive.isPending.value || restore.isPending.value)

function toggleArchived(organization: Organization) {
  archive.reset()
  restore.reset()
  if (organization.archived_at) restore.mutate(organization.id)
  else archive.mutate(organization.id)
}
</script>

<template>
  <PageHeader title="Organizations">
    <template #actions>
      <RouterLink to="/organizations/new" :class="buttonVariants()">New Organization</RouterLink>
    </template>
  </PageHeader>

  <div class="mb-4 flex flex-wrap items-center gap-x-6 gap-y-3">
    <input
      v-model="search"
      type="search"
      placeholder="Search by name, industry or location"
      aria-label="Search Organizations"
      class="h-9 w-full max-w-sm rounded-md border border-input bg-transparent px-3 text-sm shadow-xs outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50"
    />
    <label class="inline-flex items-center gap-2 text-sm">
      <input v-model="includeArchived" type="checkbox" class="size-4" />
      Show archived
    </label>
  </div>

  <p
    v-if="actionError"
    role="alert"
    class="mb-4 rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive"
  >
    {{ actionError }}
  </p>

  <p v-if="isPending" class="text-muted-foreground">Loading Organizations…</p>
  <p v-else-if="error" role="alert" class="text-destructive">
    Could not load Organizations: {{ error.message }}
  </p>
  <p v-else-if="!organizations?.length" class="text-muted-foreground">
    {{ search.trim() ? 'No Organizations match your search.' : 'No Organizations yet.' }}
  </p>
  <div v-else class="overflow-x-auto rounded-md border">
    <table class="w-full text-sm">
      <thead class="bg-muted/50 text-left text-muted-foreground">
        <tr>
          <th class="px-3 py-2 font-medium">Name</th>
          <th class="px-3 py-2 font-medium">Type</th>
          <th class="px-3 py-2 font-medium">Industry</th>
          <th class="px-3 py-2 font-medium">Location</th>
          <th class="px-3 py-2 font-medium">Priority</th>
          <th class="px-3 py-2"><span class="sr-only">Actions</span></th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="organization in organizations"
          :key="organization.id"
          class="border-t"
          :class="{ 'text-muted-foreground': organization.archived_at }"
        >
          <td class="px-3 py-2 font-medium">
            <RouterLink :to="`/organizations/${organization.id}`" class="hover:underline">{{
              organization.name
            }}</RouterLink>
          </td>
          <td class="px-3 py-2">{{ ORGANIZATION_TYPE_LABELS[organization.organization_type] }}</td>
          <td class="px-3 py-2">{{ organization.industry ?? '' }}</td>
          <td class="px-3 py-2">{{ organization.location ?? '' }}</td>
          <td class="px-3 py-2">{{ organization.priority }}</td>
          <td class="px-3 py-2 text-right whitespace-nowrap">
            <span v-if="organization.archived_at" class="mr-3 text-xs">Archived</span>
            <Button
              variant="outline"
              size="sm"
              :disabled="busy"
              @click="toggleArchived(organization)"
            >
              {{ organization.archived_at ? 'Restore' : 'Archive' }}
            </Button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
