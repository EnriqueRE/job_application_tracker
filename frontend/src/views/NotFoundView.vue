<script setup lang="ts">
import PageHeader from '@/components/PageHeader.vue'
import { Button } from '@/components/ui/button'
</script>

<template>
  <PageHeader title="Page not found" />
  <Button as-child variant="outline">
    <RouterLink to="/applications">Back to Applications</RouterLink>
  </Button>
</template>
