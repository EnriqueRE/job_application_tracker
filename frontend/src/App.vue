<script setup lang="ts">
import ApiStatus from '@/components/ApiStatus.vue'

const links = [
  { to: '/applications', label: 'Applications' },
  { to: '/organizations', label: 'Organizations' },
]
</script>

<template>
  <div class="flex min-h-dvh flex-col bg-background text-foreground">
    <header class="sticky top-0 z-10 border-b bg-background/95 backdrop-blur">
      <div
        class="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-x-6 gap-y-2 px-4 py-3"
      >
        <RouterLink to="/" class="font-semibold">Job Tracker</RouterLink>
        <nav aria-label="Main" class="-mx-1 flex gap-1 overflow-x-auto">
          <RouterLink
            v-for="link in links"
            :key="link.to"
            :to="link.to"
            class="rounded-md px-3 py-1.5 text-sm font-medium text-muted-foreground hover:bg-accent hover:text-accent-foreground"
            active-class="bg-accent text-accent-foreground"
          >
            {{ link.label }}
          </RouterLink>
        </nav>
      </div>
    </header>
    <main class="mx-auto w-full max-w-6xl flex-1 px-4 py-6">
      <RouterView />
    </main>
    <footer class="mx-auto w-full max-w-6xl px-4 py-3">
      <ApiStatus />
    </footer>
  </div>
</template>
