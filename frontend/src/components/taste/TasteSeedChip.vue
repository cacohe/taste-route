<template>
  <span class="seed-chip">
    <span class="seed-type">{{ seed.entity_type }}</span>
    <span>{{ seed.name }}</span>
    <button
      type="button"
      class="remove"
      :data-test="`remove-${seed.id}`"
      :aria-label="`移除 ${seed.name}`"
      @click="$emit('remove')"
    >×</button>
  </span>
</template>

<script setup lang="ts">
import type { TasteSeed } from '@/types/taste'

defineProps<{ seed: TasteSeed }>()
defineEmits<{ remove: [] }>()
</script>

<style scoped>
.seed-chip { display: inline-flex; align-items: center; gap: .45rem; padding: .45rem .65rem; border: 1px solid #d6c8ff; border-radius: 999px; background: #f7f3ff; color: #31245f; }
.seed-type { font-size: .7rem; text-transform: uppercase; color: #7157b7; }
.remove { border: 0; background: transparent; color: #7251c7; cursor: pointer; font-size: 1rem; line-height: 1; }
</style>
