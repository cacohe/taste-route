<template>
  <div v-if="candidate" class="evidence">
    <p class="reason">{{ item.reason }}</p>
    <div class="meta">
      <span v-if="candidate.affinity !== null">Qloo affinity {{ Math.round(candidate.affinity * 100) }}%</span>
      <span v-for="tag in candidate.tags.slice(0, 8)" :key="tag">{{ tag }}</span>
    </div>
    <p v-if="namedSignals.length" class="signals">
      Connected to: {{ namedSignals.join(', ') }}
    </p>
    <p v-else class="signals">Qloo returned no named contribution signal for this place.</p>
  </div>
  <div v-else class="unavailable">Qloo evidence is unavailable; this place is omitted from the map.</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ItineraryItem, PlaceCandidate } from '@/types/taste'

const props = defineProps<{ item: ItineraryItem; candidate: PlaceCandidate | null }>()
const namedSignals = computed(() => (props.candidate?.contributions ?? [])
  .filter((signal) => Boolean(signal.name))
  .sort((left, right) => (right.score ?? -1) - (left.score ?? -1))
  .slice(0, 2)
  .map((signal) => signal.score === null
    ? signal.name!
    : `${signal.name} ${Math.round(signal.score * 100)}%`))
</script>

<style scoped>
.evidence { display: grid; gap: .65rem; }.reason { margin: 0; color: #403451; line-height: 1.6; }
.meta { display: flex; flex-wrap: wrap; gap: .4rem; }.meta span { padding: .3rem .55rem; border-radius: 999px; background: #f0ebfb; color: #5e4496; font-size: .75rem; }
.signals { margin: 0; color: #756a81; font-size: .82rem; }.unavailable { padding: .8rem; border-radius: 8px; background: #fff1f2; color: #9b3345; }
</style>
