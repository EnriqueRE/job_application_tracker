<script setup lang="ts">
import { computed, reactive, ref, useId } from 'vue'

import {
  ORGANIZATION_TYPE_LABELS,
  ORGANIZATION_TYPES,
  useCreateOrganization,
  useUpdateOrganization,
  type Organization,
  type OrganizationCreate,
  type OrganizationType,
  type OrganizationUpdate,
} from '@/api/organizations'
import { Button } from '@/components/ui/button'
import { blankToNull } from '@/lib/text'

/**
 * Create or edit an Organization. Saves through the API itself and emits `saved`
 * with the stored Organization. Without `organization` it creates one, starting
 * from `initialName` / `initialType` (handy for creating one inline elsewhere).
 */
const props = withDefaults(
  defineProps<{
    organization?: Organization
    initialName?: string
    initialType?: OrganizationType
    submitLabel?: string
  }>(),
  { organization: undefined, initialName: '', initialType: 'company', submitLabel: undefined },
)

const emit = defineEmits<{ saved: [organization: Organization]; cancel: [] }>()

type TextField = 'industry' | 'location' | 'website_url' | 'career_url' | 'contact_url' | 'notes'

const source = props.organization
const form = reactive({
  name: source?.name ?? props.initialName,
  organization_type: source?.organization_type ?? props.initialType,
  priority: source?.priority ?? 3,
  industry: source?.industry ?? '',
  location: source?.location ?? '',
  website_url: source?.website_url ?? '',
  career_url: source?.career_url ?? '',
  contact_url: source?.contact_url ?? '',
  notes: source?.notes ?? '',
})

const create = useCreateOrganization()
const update = useUpdateOrganization()
const validationError = ref<string>()

const saving = computed(() => create.isPending.value || update.isPending.value)
const errorMessage = computed(
  () => validationError.value ?? create.error.value?.message ?? update.error.value?.message,
)

const textFields: { key: TextField; label: string; type: string }[] = [
  { key: 'industry', label: 'Industry', type: 'text' },
  { key: 'location', label: 'Location', type: 'text' },
  { key: 'website_url', label: 'Website', type: 'url' },
  { key: 'career_url', label: 'Careers page', type: 'url' },
  { key: 'contact_url', label: 'Contact page', type: 'url' },
]

function payload(): OrganizationCreate {
  return {
    name: form.name.trim(),
    organization_type: form.organization_type,
    industry: blankToNull(form.industry),
    location: blankToNull(form.location),
    priority: Number(form.priority),
    website_url: blankToNull(form.website_url),
    career_url: blankToNull(form.career_url),
    contact_url: blankToNull(form.contact_url),
    notes: blankToNull(form.notes),
  }
}

function changes(original: Organization, next: OrganizationCreate): OrganizationUpdate {
  return Object.fromEntries(
    Object.entries(next).filter(
      ([key, value]) => original[key as keyof OrganizationCreate] !== value,
    ),
  )
}

function submit() {
  validationError.value = undefined
  create.reset()
  update.reset()
  if (!form.name.trim()) {
    validationError.value = 'Name is required.'
    return
  }
  const body = payload()
  const onSuccess = (organization: Organization) => emit('saved', organization)
  if (props.organization) {
    const diff = changes(props.organization, body)
    if (Object.keys(diff).length === 0) return emit('saved', props.organization)
    update.mutate({ id: props.organization.id, changes: diff }, { onSuccess })
  } else {
    create.mutate(body, { onSuccess })
  }
}

const id = useId()
const inputClass =
  'h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm shadow-xs outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50'
</script>

<template>
  <form class="grid max-w-2xl gap-4" novalidate @submit.prevent="submit">
    <p
      v-if="errorMessage"
      role="alert"
      class="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive"
    >
      {{ errorMessage }}
    </p>

    <div class="grid gap-4 sm:grid-cols-[2fr_1fr_6rem]">
      <div class="grid gap-1.5">
        <label :for="`${id}-name`" class="text-sm font-medium">Name</label>
        <input
          :id="`${id}-name`"
          v-model="form.name"
          name="name"
          required
          maxlength="255"
          :class="inputClass"
        />
      </div>
      <div class="grid gap-1.5">
        <label :for="`${id}-type`" class="text-sm font-medium">Type</label>
        <select
          :id="`${id}-type`"
          v-model="form.organization_type"
          name="organization_type"
          :class="inputClass"
        >
          <option v-for="type in ORGANIZATION_TYPES" :key="type" :value="type">
            {{ ORGANIZATION_TYPE_LABELS[type] }}
          </option>
        </select>
      </div>
      <div class="grid gap-1.5">
        <label :for="`${id}-priority`" class="text-sm font-medium">Priority</label>
        <input
          :id="`${id}-priority`"
          v-model.number="form.priority"
          name="priority"
          type="number"
          min="0"
          max="5"
          :class="inputClass"
        />
      </div>
    </div>

    <div class="grid gap-4 sm:grid-cols-2">
      <div v-for="field in textFields" :key="field.key" class="grid gap-1.5">
        <label :for="`${id}-${field.key}`" class="text-sm font-medium">{{ field.label }}</label>
        <input
          :id="`${id}-${field.key}`"
          v-model="form[field.key]"
          :name="field.key"
          :type="field.type"
          :class="inputClass"
        />
      </div>
    </div>

    <div class="grid gap-1.5">
      <label :for="`${id}-notes`" class="text-sm font-medium">Notes</label>
      <textarea
        :id="`${id}-notes`"
        v-model="form.notes"
        name="notes"
        rows="4"
        :class="[inputClass, 'h-auto py-2']"
      />
    </div>

    <div class="flex gap-2">
      <Button type="submit" :disabled="saving">
        {{ submitLabel ?? (organization ? 'Save changes' : 'Create Organization') }}
      </Button>
      <Button type="button" variant="outline" @click="emit('cancel')">Cancel</Button>
    </div>
  </form>
</template>
