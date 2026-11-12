<script setup lang="ts">
import { ref } from 'vue'

import {
  APPLICATION_EVENT_TYPE_LABELS,
  APPLICATION_EVENT_TYPES,
  type ApplicationEventCreate,
  type ApplicationEventType,
} from '@/api/applicationEvents'
import type { Schemas } from '@/api/client'
import { Button } from '@/components/ui/button'

/** Add or edit one Application Event. Emits `submit` with the full event fields. */
const props = defineProps<{
  event?: Schemas['ApplicationTimelineEvent']
  saving?: boolean
  error?: string | null
}>()

const emit = defineEmits<{
  submit: [body: Required<Pick<ApplicationEventCreate, 'event_type' | 'occurred_at' | 'notes'>>]
  cancel: []
}>()

/** ISO timestamp → the local `YYYY-MM-DDTHH:mm` a datetime-local input expects. */
function toLocalInput(iso: string): string {
  const date = new Date(iso)
  const offsetMs = date.getTimezoneOffset() * 60_000
  return new Date(date.getTime() - offsetMs).toISOString().slice(0, 16)
}

const eventType = ref<ApplicationEventType>(props.event?.event_type ?? 'note')
const occurredAt = ref(toLocalInput(props.event?.occurred_at ?? new Date().toISOString()))
const notes = ref(props.event?.notes ?? '')

function submit() {
  emit('submit', {
    event_type: eventType.value,
    occurred_at: occurredAt.value ? new Date(occurredAt.value).toISOString() : null,
    notes: notes.value.trim() ? notes.value : null,
  })
}
</script>

<template>
  <div class="space-y-3 rounded-md border p-3">
    <div class="grid gap-3 sm:grid-cols-2">
      <label class="flex min-w-0 flex-col gap-1.5 text-sm font-medium">
        Type
        <select
          v-model="eventType"
          name="event_type"
          class="h-9 rounded-md border bg-background px-2 font-normal"
        >
          <option v-for="type in APPLICATION_EVENT_TYPES" :key="type" :value="type">
            {{ APPLICATION_EVENT_TYPE_LABELS[type] }}
          </option>
        </select>
      </label>
      <label class="flex min-w-0 flex-col gap-1.5 text-sm font-medium">
        When
        <input
          v-model="occurredAt"
          type="datetime-local"
          name="occurred_at"
          class="h-9 min-w-0 rounded-md border bg-background px-2 font-normal"
        />
      </label>
    </div>
    <label class="flex flex-col gap-1.5 text-sm font-medium">
      Notes
      <textarea
        v-model="notes"
        name="notes"
        rows="3"
        class="rounded-md border bg-background px-3 py-2 font-normal"
      />
    </label>
    <p v-if="error" role="alert" class="text-sm text-destructive">{{ error }}</p>
    <div class="flex gap-2">
      <Button size="sm" :disabled="saving" @click="submit">Save event</Button>
      <Button variant="ghost" size="sm" :disabled="saving" @click="emit('cancel')">Cancel</Button>
    </div>
  </div>
</template>
