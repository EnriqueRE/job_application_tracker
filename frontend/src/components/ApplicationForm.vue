<script setup lang="ts">
import { computed, reactive, ref, useId } from 'vue'

import {
  WORK_ARRANGEMENT_LABELS,
  useCreateApplication,
  useUpdateApplication,
  type ApplicationCreate,
  type ApplicationDetail,
  type ApplicationUpdate,
  type WorkArrangement,
} from '@/api/applications'
import MarkdownEditor from '@/components/MarkdownEditor.vue'
import OrganizationPicker, { type PickedOrganization } from '@/components/OrganizationPicker.vue'
import { Button } from '@/components/ui/button'
import { blankToNull } from '@/lib/text'

/**
 * Create or edit an Application. Saves through the API itself and emits `saved`
 * with the stored Application. Without `application` it creates one.
 */
const props = defineProps<{ application?: ApplicationDetail }>()
const emit = defineEmits<{ saved: [application: ApplicationDetail]; cancel: [] }>()

const source = props.application
const organization = ref<PickedOrganization | undefined>(source?.organization)
const form = reactive({
  role: source?.role ?? '',
  location: source?.location ?? '',
  work_arrangement: source?.work_arrangement ?? ('unspecified' as WorkArrangement),
  vacancy_source: source?.vacancy_source ?? '',
  vacancy_url: source?.vacancy_url ?? '',
  applied_at: source?.applied_at ?? '',
  next_action_at: source?.next_action_at ?? '',
  job_description: source?.job_description ?? '',
  interview_notes: source?.interview_notes ?? '',
  application_notes: source?.application_notes ?? '',
})

type FieldErrors = Partial<Record<'organization' | 'role' | 'vacancy_url', string>>
const fieldErrors = ref<FieldErrors>({})

const create = useCreateApplication()
const update = useUpdateApplication()
const saving = computed(() => create.isPending.value || update.isPending.value)
const serverError = computed(() => create.error.value?.message ?? update.error.value?.message)

function isHttpUrl(value: string): boolean {
  try {
    const url = new URL(value)
    return (url.protocol === 'http:' || url.protocol === 'https:') && !/\s/.test(value)
  } catch {
    return false
  }
}

function validate(): FieldErrors {
  const errors: FieldErrors = {}
  if (!organization.value) errors.organization = 'Organization is required.'
  if (!form.role.trim()) errors.role = 'Role is required.'
  const url = form.vacancy_url.trim()
  if (url && !isHttpUrl(url)) {
    errors.vacancy_url = 'Vacancy URL must start with http:// or https://.'
  }
  return errors
}

function payload(organizationId: number): ApplicationCreate {
  return {
    organization_id: organizationId,
    role: form.role.trim(),
    location: blankToNull(form.location),
    work_arrangement: form.work_arrangement,
    vacancy_source: blankToNull(form.vacancy_source),
    vacancy_url: blankToNull(form.vacancy_url),
    applied_at: form.applied_at || null,
    next_action_at: form.next_action_at || null,
    // Markdown keeps its whitespace; only an all-blank text counts as empty.
    job_description: blankToNull(form.job_description, { keepWhitespace: true }),
    interview_notes: blankToNull(form.interview_notes, { keepWhitespace: true }),
    application_notes: blankToNull(form.application_notes, { keepWhitespace: true }),
  }
}

function changes(original: ApplicationDetail, next: ApplicationCreate): ApplicationUpdate {
  const before: Record<string, unknown> = { ...original, organization_id: original.organization.id }
  return Object.fromEntries(Object.entries(next).filter(([key, value]) => before[key] !== value))
}

function submit() {
  create.reset()
  update.reset()
  fieldErrors.value = validate()
  if (Object.keys(fieldErrors.value).length > 0 || !organization.value) return
  const body = payload(organization.value.id)
  const onSuccess = (application: ApplicationDetail) => emit('saved', application)
  if (props.application) {
    const diff = changes(props.application, body)
    if (Object.keys(diff).length === 0) return emit('saved', props.application)
    update.mutate({ id: props.application.id, changes: diff }, { onSuccess })
  } else {
    create.mutate(body, { onSuccess })
  }
}

const workArrangements = Object.keys(WORK_ARRANGEMENT_LABELS) as WorkArrangement[]
const textFields = [
  { key: 'location', label: 'Location' },
  { key: 'vacancy_source', label: 'Vacancy source' },
] as const
const dateFields = [
  { key: 'applied_at', label: 'Applied date' },
  { key: 'next_action_at', label: 'Next action date' },
] as const
const markdownFields = [
  { key: 'job_description', label: 'Job Description', rows: 16 },
  { key: 'interview_notes', label: 'Interview Notes', rows: 6 },
  { key: 'application_notes', label: 'Application Notes', rows: 6 },
] as const

const id = useId()
const formId = `${id}-form`
const inputClass =
  'h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm shadow-xs outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 aria-invalid:border-destructive'
</script>

<template>
  <div class="grid max-w-5xl gap-4">
    <p
      v-if="serverError"
      role="alert"
      class="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive"
    >
      {{ serverError }}
    </p>

    <!-- Outside the <form>: creating an Organization inline renders a form of its own. -->
    <div class="max-w-xl">
      <OrganizationPicker v-model="organization" :error="fieldErrors.organization" />
    </div>

    <form
      :id="formId"
      data-testid="application-form"
      class="grid gap-4"
      novalidate
      @submit.prevent="submit"
    >
      <div class="grid gap-4 sm:grid-cols-2">
        <div class="grid gap-1.5">
          <label :for="`${id}-role`" class="text-sm font-medium">Role</label>
          <input
            :id="`${id}-role`"
            v-model="form.role"
            name="role"
            required
            maxlength="255"
            :aria-invalid="fieldErrors.role ? 'true' : undefined"
            :aria-describedby="fieldErrors.role ? `${id}-role-error` : undefined"
            :class="inputClass"
          />
          <p v-if="fieldErrors.role" :id="`${id}-role-error`" class="text-sm text-destructive">
            {{ fieldErrors.role }}
          </p>
        </div>
        <div class="grid gap-1.5">
          <label :for="`${id}-work_arrangement`" class="text-sm font-medium">
            Work arrangement
          </label>
          <select
            :id="`${id}-work_arrangement`"
            v-model="form.work_arrangement"
            name="work_arrangement"
            :class="inputClass"
          >
            <option v-for="value in workArrangements" :key="value" :value="value">
              {{ WORK_ARRANGEMENT_LABELS[value] }}
            </option>
          </select>
        </div>
        <div v-for="field in textFields" :key="field.key" class="grid gap-1.5">
          <label :for="`${id}-${field.key}`" class="text-sm font-medium">{{ field.label }}</label>
          <input
            :id="`${id}-${field.key}`"
            v-model="form[field.key]"
            :name="field.key"
            maxlength="255"
            :class="inputClass"
          />
        </div>
        <div class="grid gap-1.5 sm:col-span-2">
          <label :for="`${id}-vacancy_url`" class="text-sm font-medium">Vacancy URL</label>
          <input
            :id="`${id}-vacancy_url`"
            v-model="form.vacancy_url"
            name="vacancy_url"
            type="url"
            placeholder="https://…"
            :aria-invalid="fieldErrors.vacancy_url ? 'true' : undefined"
            :aria-describedby="fieldErrors.vacancy_url ? `${id}-vacancy_url-error` : undefined"
            :class="inputClass"
          />
          <p
            v-if="fieldErrors.vacancy_url"
            :id="`${id}-vacancy_url-error`"
            class="text-sm text-destructive"
          >
            {{ fieldErrors.vacancy_url }}
          </p>
        </div>
        <div v-for="field in dateFields" :key="field.key" class="grid gap-1.5">
          <label :for="`${id}-${field.key}`" class="text-sm font-medium">{{ field.label }}</label>
          <input
            :id="`${id}-${field.key}`"
            v-model="form[field.key]"
            :name="field.key"
            type="date"
            :class="inputClass"
          />
        </div>
      </div>

      <div v-for="field in markdownFields" :key="field.key" class="grid gap-1.5">
        <label :for="`${id}-${field.key}`" class="text-sm font-medium">{{ field.label }}</label>
        <MarkdownEditor
          :id="`${id}-${field.key}`"
          v-model="form[field.key]"
          :name="field.key"
          :label="field.label"
          :rows="field.rows"
          :placeholder="field.key === 'job_description' ? 'Paste the Job Description…' : undefined"
        />
      </div>

      <div class="flex gap-2">
        <Button type="submit" :disabled="saving">
          {{ application ? 'Save changes' : 'Create Application' }}
        </Button>
        <Button type="button" variant="outline" @click="emit('cancel')">Cancel</Button>
      </div>
    </form>
  </div>
</template>
