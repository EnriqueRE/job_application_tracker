<script setup lang="ts">
import { computed, ref } from 'vue'

import {
  APPLICATION_EVENT_TYPE_LABELS,
  useAddApplicationEvent,
  useDeleteApplicationEvent,
  useUpdateApplicationEvent,
  type ApplicationEventCreate,
} from '@/api/applicationEvents'
import { APPLICATION_STATUS_LABELS, type ApplicationDetail } from '@/api/applications'
import ApplicationEventForm from '@/components/ApplicationEventForm.vue'
import { Button } from '@/components/ui/button'

/** An Application's Application Events, newest first, with add/edit/delete. */
const props = defineProps<{ application: ApplicationDetail }>()

const applicationId = () => props.application.id
const add = useAddApplicationEvent(applicationId)
const update = useUpdateApplicationEvent(applicationId)
const remove = useDeleteApplicationEvent(applicationId)

/** 'new', an event id being edited, or null. */
const editing = ref<'new' | number | null>(null)
const confirmingDelete = ref<number | null>(null)

const events = computed(() => [...props.application.events].reverse())

const formatter = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' })

function formatWhen(iso: string | null): string {
  return iso ? formatter.format(new Date(iso)) : 'Undated'
}

function startEditing(target: 'new' | number) {
  add.reset()
  update.reset()
  confirmingDelete.value = null
  editing.value = target
}

async function save(body: ApplicationEventCreate) {
  if (editing.value === 'new') await add.mutateAsync(body)
  else if (editing.value !== null)
    await update.mutateAsync({ eventId: editing.value, changes: body })
  editing.value = null
}

function onSubmit(body: ApplicationEventCreate) {
  // Errors are shown by the form via the mutation state.
  save(body).catch(() => {})
}

function confirmDelete(eventId: number) {
  remove.mutate(eventId, { onSuccess: () => (confirmingDelete.value = null) })
}

const formError = computed(
  () => (editing.value === 'new' ? add.error : update.error).value?.message,
)
const formSaving = computed(() => add.isPending.value || update.isPending.value)
</script>

<template>
  <section class="min-w-0 space-y-3">
    <header class="flex items-center justify-between gap-3">
      <h2 class="text-lg font-semibold">Timeline</h2>
      <Button v-if="editing !== 'new'" variant="outline" size="sm" @click="startEditing('new')">
        Add event
      </Button>
    </header>

    <ApplicationEventForm
      v-if="editing === 'new'"
      :saving="formSaving"
      :error="formError"
      @submit="onSubmit"
      @cancel="editing = null"
    />

    <p v-if="events.length === 0 && editing !== 'new'" class="text-sm text-muted-foreground">
      No Application Events yet.
    </p>

    <ol class="space-y-3">
      <li v-for="event in events" :key="event.id" class="min-w-0 border-l-2 pl-3">
        <ApplicationEventForm
          v-if="editing === event.id"
          :event="event"
          :saving="formSaving"
          :error="formError"
          @submit="onSubmit"
          @cancel="editing = null"
        />
        <template v-else>
          <div class="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
            <p class="font-medium">
              {{ APPLICATION_EVENT_TYPE_LABELS[event.event_type] }}
              <span v-if="event.resulting_status" class="text-sm font-normal text-muted-foreground">
                → {{ APPLICATION_STATUS_LABELS[event.resulting_status] }}
              </span>
            </p>
            <time :datetime="event.occurred_at ?? undefined" class="text-sm text-muted-foreground">
              {{ formatWhen(event.occurred_at) }}
            </time>
          </div>
          <p v-if="event.notes" class="text-sm break-words whitespace-pre-line">
            {{ event.notes }}
          </p>
          <div v-if="confirmingDelete === event.id" class="mt-2 flex flex-wrap items-center gap-2">
            <span class="text-sm">Delete this Application Event?</span>
            <Button
              variant="destructive"
              size="sm"
              :disabled="remove.isPending.value"
              @click="confirmDelete(event.id)"
            >
              Delete event
            </Button>
            <Button variant="ghost" size="sm" @click="confirmingDelete = null">Keep</Button>
            <p v-if="remove.error.value" role="alert" class="w-full text-sm text-destructive">
              {{ remove.error.value.message }}
            </p>
          </div>
          <div v-else class="mt-1 flex gap-1">
            <Button variant="ghost" size="sm" @click="startEditing(event.id)">Edit</Button>
            <Button
              variant="ghost"
              size="sm"
              @click="
                () => {
                  remove.reset()
                  confirmingDelete = event.id
                }
              "
            >
              Delete
            </Button>
          </div>
        </template>
      </li>
    </ol>
  </section>
</template>
