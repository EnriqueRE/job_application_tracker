<script setup lang="ts">
import { computed, ref, useId } from 'vue'

import { useOrganizations, type Organization } from '@/api/organizations'
import OrganizationForm from '@/components/OrganizationForm.vue'
import { Button } from '@/components/ui/button'

export type PickedOrganization = Pick<Organization, 'id' | 'name'>

/**
 * Choose an Organization by searching its name, or create a new one inline.
 * Use with `v-model`. Renders its own `<form>` while creating, so keep it
 * outside other forms.
 */
const props = defineProps<{ label?: string; error?: string }>()
const model = defineModel<PickedOrganization | undefined>({ required: true })

const query = ref('')
const creating = ref(false)
const { data: organizations, isFetching } = useOrganizations(() => ({ q: query.value }))
const options = computed(() => organizations.value ?? [])

function choose(organization: PickedOrganization) {
  model.value = { id: organization.id, name: organization.name }
  query.value = ''
  creating.value = false
}

const id = useId()
const inputClass =
  'h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm shadow-xs outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50'
</script>

<template>
  <div class="grid gap-1.5">
    <label :for="`${id}-search`" class="text-sm font-medium">{{
      props.label ?? 'Organization'
    }}</label>

    <div v-if="model" class="flex items-center gap-2">
      <span data-testid="selected-organization" class="text-sm font-medium">{{ model.name }}</span>
      <Button type="button" variant="outline" size="sm" @click="model = undefined">Change</Button>
    </div>

    <template v-else-if="creating">
      <div class="rounded-md border p-4">
        <p class="mb-3 text-sm font-medium">New Organization</p>
        <OrganizationForm
          :initial-name="query.trim()"
          submit-label="Create and use"
          @saved="choose"
          @cancel="creating = false"
        />
      </div>
    </template>

    <template v-else>
      <input
        :id="`${id}-search`"
        v-model="query"
        name="organization_search"
        role="combobox"
        aria-autocomplete="list"
        :aria-controls="`${id}-options`"
        aria-expanded="true"
        :aria-invalid="error ? 'true' : undefined"
        :aria-describedby="error ? `${id}-error` : undefined"
        autocomplete="off"
        placeholder="Search Organizations…"
        :class="inputClass"
      />
      <ul
        :id="`${id}-options`"
        role="listbox"
        :aria-label="`${props.label ?? 'Organization'} results`"
        class="max-h-56 overflow-y-auto rounded-md border"
      >
        <li
          v-for="organization in options"
          :key="organization.id"
          role="option"
          aria-selected="false"
          tabindex="0"
          class="cursor-pointer px-3 py-1.5 text-sm hover:bg-accent focus:bg-accent focus:outline-none"
          @click="choose(organization)"
          @keydown.enter.prevent="choose(organization)"
          @keydown.space.prevent="choose(organization)"
        >
          {{ organization.name }}
        </li>
        <li
          v-if="!isFetching && options.length === 0"
          class="px-3 py-1.5 text-sm text-muted-foreground"
        >
          No matching Organizations.
        </li>
      </ul>
      <div>
        <Button type="button" variant="outline" size="sm" @click="creating = true">
          {{
            query.trim() ? `Create new Organization “${query.trim()}”` : 'Create new Organization'
          }}
        </Button>
      </div>
    </template>

    <p v-if="error" :id="`${id}-error`" class="text-sm text-destructive">{{ error }}</p>
  </div>
</template>
