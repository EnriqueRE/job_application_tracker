<script setup lang="ts">
import { ref } from 'vue'

import { useClearStatusOverride, useSetStatusOverride } from '@/api/applicationEvents'
import {
  APPLICATION_STATUS_LABELS,
  APPLICATION_STATUSES,
  type ApplicationDetail,
  type ApplicationStatus,
} from '@/api/applications'
import { Button } from '@/components/ui/button'

/** Pin the Pipeline Status by hand (Status Override), or clear the override. */
const props = defineProps<{ application: ApplicationDetail }>()

const applicationId = () => props.application.id
const set = useSetStatusOverride(applicationId)
const clear = useClearStatusOverride(applicationId)

const status = ref<ApplicationStatus>(props.application.current_status)
</script>

<template>
  <div class="flex flex-wrap items-center gap-2">
    <label class="flex items-center gap-2 text-sm">
      <span class="text-muted-foreground">Override status</span>
      <select
        v-model="status"
        name="override_status"
        class="h-8 rounded-md border bg-background px-2"
      >
        <option v-for="value in APPLICATION_STATUSES" :key="value" :value="value">
          {{ APPLICATION_STATUS_LABELS[value] }}
        </option>
      </select>
    </label>
    <Button variant="outline" size="sm" :disabled="set.isPending.value" @click="set.mutate(status)">
      Set override
    </Button>
    <Button
      v-if="application.status_overridden"
      variant="ghost"
      size="sm"
      :disabled="clear.isPending.value"
      @click="clear.mutate()"
    >
      Clear override
    </Button>
    <p
      v-if="set.error.value || clear.error.value"
      role="alert"
      class="w-full text-sm text-destructive"
    >
      {{ (set.error.value ?? clear.error.value)?.message }}
    </p>
  </div>
</template>
