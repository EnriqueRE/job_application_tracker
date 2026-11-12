<script setup lang="ts">
import { computed } from 'vue'

import { useHealth } from '@/api/health'

const { data, isPending } = useHealth()

const online = computed(() => data.value?.status === 'ok')
</script>

<template>
  <span class="inline-flex items-center gap-1.5 text-xs text-muted-foreground" role="status">
    <span
      class="size-2 rounded-full"
      :class="isPending ? 'bg-muted-foreground' : online ? 'bg-emerald-500' : 'bg-destructive'"
      aria-hidden="true"
    />
    <template v-if="isPending">Checking backend…</template>
    <template v-else-if="online">Backend online</template>
    <template v-else>Backend offline</template>
  </span>
</template>
