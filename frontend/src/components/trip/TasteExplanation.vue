<template>
  <div v-if="candidate" class="evidence">
    <p class="reason">{{ item.reason }}</p>
    <div class="meta">
      <span v-if="candidate.affinity !== null">Qloo affinity {{ Math.round(candidate.affinity * 100) }}%</span>
      <span v-for="tag in candidate.tags" :key="tag">{{ tag }}</span>
    </div>
    <p v-if="candidate.contributions.length" class="signals">
      关联自：{{ candidate.contributions.map((signal) => signal.name || signal.entity_id).join('、') }}
    </p>
    <p v-else class="signals">Qloo 未返回可展示的单项贡献信号。</p>
  </div>
  <div v-else class="unavailable">Qloo 依据不可用；此地点不会在地图上显示。</div>
</template>

<script setup lang="ts">
import type { ItineraryItem, PlaceCandidate } from '@/types/taste'

defineProps<{ item: ItineraryItem; candidate: PlaceCandidate | null }>()
</script>

<style scoped>
.evidence { display: grid; gap: .65rem; }.reason { margin: 0; color: #403451; line-height: 1.6; }
.meta { display: flex; flex-wrap: wrap; gap: .4rem; }.meta span { padding: .3rem .55rem; border-radius: 999px; background: #f0ebfb; color: #5e4496; font-size: .75rem; }
.signals { margin: 0; color: #756a81; font-size: .82rem; }.unavailable { padding: .8rem; border-radius: 8px; background: #fff1f2; color: #9b3345; }
</style>
