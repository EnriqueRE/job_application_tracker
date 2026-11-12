<script setup lang="ts">
import MarkdownView from '@/components/MarkdownView.vue'

/**
 * A Markdown textarea with a live preview: side by side on wide screens, stacked on phones.
 * Use with `v-model`; `label` names the textarea for assistive tech, `name`/`id` are passed through.
 */
defineProps<{ label: string; name?: string; id?: string; rows?: number; placeholder?: string }>()

const model = defineModel<string>({ required: true })
</script>

<template>
  <div class="grid gap-3 md:grid-cols-2">
    <textarea
      :id="id"
      v-model="model"
      :name="name"
      :rows="rows ?? 12"
      :placeholder="placeholder ?? 'Write Markdown…'"
      :aria-label="label"
      class="min-h-40 w-full min-w-0 rounded-md border bg-background px-3 py-2 font-mono text-sm"
    />
    <div
      data-testid="markdown-preview"
      class="min-w-0 rounded-md border border-dashed p-3"
      role="region"
      :aria-label="`${label} preview`"
    >
      <MarkdownView v-if="model.trim()" :source="model" />
      <p v-else class="text-sm text-muted-foreground">Preview appears here.</p>
    </div>
  </div>
</template>
