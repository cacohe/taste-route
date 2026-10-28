<template>
  <section class="generation-progress" aria-live="polite" aria-label="TasteRoute generation progress">
    <div class="progress-heading">
      <div>
        <p class="kicker">AGENT WORKFLOW</p>
        <h3>Building your cultural route</h3>
      </div>
      <span>{{ elapsedSeconds }} seconds</span>
    </div>
    <div class="progress-track" role="progressbar" aria-label="Itinerary generation in progress">
      <span></span>
    </div>
    <ol>
      <li
        v-for="step in steps"
        :key="step.key"
        :data-step="step.key"
        :data-status="step.status"
      >
        <span class="step-indicator" aria-hidden="true"></span>
        <span>{{ step.label }}</span>
        <small>{{ statusLabel(step.status) }}</small>
      </li>
    </ol>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { WorkflowStep } from '@/types/taste'

const props = defineProps<{
  events: WorkflowStep[]
  elapsedSeconds: number
}>()

const workflow = [
  { key: 'taste_resolution', label: 'Resolve taste signals' },
  { key: 'qloo_discovery', label: 'Discover Qloo places' },
  { key: 'itinerary_composition', label: 'Compose itinerary' },
]

type DisplayStatus = WorkflowStep['status'] | 'pending'

const steps = computed(() => workflow.map((definition) => {
  const latest = [...props.events].reverse().find((event) => event.key === definition.key)
  return { ...definition, status: (latest?.status ?? 'pending') as DisplayStatus }
}))

function statusLabel(status: DisplayStatus): string {
  if (status === 'active') return 'In progress'
  if (status === 'pending') return 'Waiting'
  if (status === 'repaired') return 'Completed after repair'
  return status.charAt(0).toUpperCase() + status.slice(1)
}
</script>

<style scoped>
.generation-progress { padding: 22px; border: 1px solid #dcd2ee; border-radius: 18px; background: #f7f3ff; }
.progress-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 18px; }
.kicker { margin: 0 0 4px; color: #7656b8; font-size: .68rem; font-weight: 800; letter-spacing: .16em; }
h3 { margin: 0; color: #2d2144; font: 500 1.25rem/1.2 Georgia, serif; }
.progress-heading > span { color: #746985; font-size: .78rem; white-space: nowrap; }
.progress-track { height: 4px; margin: 18px 0; overflow: hidden; border-radius: 99px; background: #ddd3ec; }
.progress-track span { display: block; width: 38%; height: 100%; border-radius: inherit; background: #6947b7; animation: travel 1.4s ease-in-out infinite alternate; }
ol { display: grid; gap: 10px; margin: 0; padding: 0; list-style: none; }
li { display: grid; grid-template-columns: 12px 1fr auto; align-items: center; gap: 10px; color: #6f657b; font-size: .86rem; }
li small { font-size: .72rem; }
.step-indicator { width: 10px; height: 10px; border: 2px solid #b9adc8; border-radius: 50%; }
li[data-status='active'] { color: #2d2144; font-weight: 700; }
li[data-status='active'] .step-indicator { border-color: #6947b7; box-shadow: 0 0 0 4px #e6dcf7; }
li[data-status='completed'] .step-indicator, li[data-status='repaired'] .step-indicator { border-color: #3d9870; background: #3d9870; }
li[data-status='failed'] .step-indicator { border-color: #c24b5f; background: #c24b5f; }
@keyframes travel { from { transform: translateX(-15%); } to { transform: translateX(180%); } }
@media (prefers-reduced-motion: reduce) { .progress-track span { width: 62%; animation: none; } }
</style>
