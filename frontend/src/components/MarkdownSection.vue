<script setup lang="ts">
import { ref } from 'vue'

import MarkdownEditor from '@/components/MarkdownEditor.vue'
import MarkdownView from '@/components/MarkdownView.vue'
import { Button } from '@/components/ui/button'

/**
 * A titled Markdown text that reads rendered by default and has an Edit toggle
 * (textarea + live preview, Save/Cancel). `save` receives the new text, or null
 * when emptied; the section returns to reading once it resolves and shows the
 * error message if it rejects.
 */
const props = defineProps<{
  title: string
  source: string | null
  save: (value: string | null) => Promise<unknown>
}>()

const editing = ref(false)
const draft = ref('')
const saving = ref(false)
const error = ref<string | null>(null)

function startEditing() {
  draft.value = props.source ?? ''
  error.value = null
  editing.value = true
}

function cancel() {
  editing.value = false
  error.value = null
}

async function submit() {
  saving.value = true
  error.value = null
  try {
    await props.save(draft.value.trim() ? draft.value : null)
    editing.value = false
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <section class="min-w-0 space-y-3">
    <header class="flex items-center justify-between gap-3">
      <h2 class="text-lg font-semibold">{{ title }}</h2>
      <Button v-if="!editing" variant="outline" size="sm" @click="startEditing">
        {{ source?.trim() ? 'Edit' : 'Add' }}
      </Button>
    </header>

    <div v-if="editing" class="space-y-3">
      <MarkdownEditor v-model="draft" :label="title" />
      <p v-if="error" role="alert" class="text-sm text-destructive">{{ error }}</p>
      <div class="flex gap-2">
        <Button size="sm" :disabled="saving" @click="submit">Save</Button>
        <Button variant="ghost" size="sm" :disabled="saving" @click="cancel"> Cancel </Button>
      </div>
    </div>
    <MarkdownView v-else-if="source?.trim()" :source="source" />
    <p v-else class="text-sm text-muted-foreground">No {{ title }} yet.</p>
  </section>
</template>
