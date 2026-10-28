<template>
  <main class="result-shell">
    <header>
      <button type="button" class="back" @click="router.push('/')">← Plan another trip</button>
      <div v-if="plan">
        <p class="eyebrow">YOUR TASTEROUTE</p>
        <h1>{{ plan.destination }}</h1>
        <p>{{ plan.start_date }} — {{ plan.end_date }}</p>
      </div>
    </header>

    <section v-if="!plan" class="empty-state">
      <h1>No route to display yet</h1>
      <p>Return home and generate a trip from at least one taste signal.</p>
      <button type="button" @click="router.push('/')">Start planning</button>
    </section>

    <template v-else>
      <div v-if="plan.warnings.length" class="warnings">
        <strong>Partial result</strong>
        <p v-for="warning in plan.warnings" :key="warning">{{ warning }}</p>
      </div>

      <div class="overview">
        <div class="profile-stack">
          <TasteProfileCard :tags="plan.taste_profile.tags" />
          <article class="trace-card" aria-label="Agent workflow trace">
            <p class="eyebrow">AGENT WORKFLOW</p>
            <div v-for="step in plan.trace" :key="step.key" class="trace-step">
              <span :class="`status ${step.status}`"></span>
              <span>{{ step.label }}</span>
              <small>{{ step.status }}</small>
            </div>
          </article>
        </div>
        <ItineraryMap
          :model="mapModel"
          :selected-marker-id="selectedMarkerId"
          @select="selectMarker($event, true)"
        />
      </div>

      <section class="days">
        <article v-for="(day, dayIndex) in plan.days" :key="day.date" class="day" :style="{ '--day-color': getDayColor(dayIndex) }">
          <div class="day-heading">
            <span>DAY {{ String(dayIndex + 1).padStart(2, '0') }}</span>
            <h2>{{ day.date }}</h2>
          </div>
          <div class="stops">
            <article
              v-for="(item, itemIndex) in day.items"
              :key="`${day.date}-${item.place_id}`"
              class="stop"
              :class="{ 'is-selected': selectedMarkerId === itineraryMarkerId(day.date, itemIndex, item.place_id) }"
              :data-marker-id="itineraryMarkerId(day.date, itemIndex, item.place_id)"
              tabindex="0"
              @click="selectMarker(itineraryMarkerId(day.date, itemIndex, item.place_id))"
              @keydown.enter="selectMarker(itineraryMarkerId(day.date, itemIndex, item.place_id))"
            >
              <div class="time">{{ item.start_time }}</div>
              <div class="stop-body">
                <template v-if="candidateFor(item.place_id)">
                  <img
                    v-if="candidateFor(item.place_id)?.image_url"
                    :src="candidateFor(item.place_id)?.image_url ?? ''"
                    :alt="candidateFor(item.place_id)?.name"
                  />
                  <div>
                    <h3>{{ candidateFor(item.place_id)?.name }}</h3>
                    <p class="address">{{ candidateFor(item.place_id)?.address || 'Address not provided by Qloo' }} · {{ item.duration_minutes }} min</p>
                    <TasteExplanation :item="item" :candidate="candidateFor(item.place_id)" />
                  </div>
                </template>
                <TasteExplanation v-else :item="item" :candidate="null" />
              </div>
            </article>
          </div>
        </article>
        <div v-if="!plan.days.length" class="empty-days">Places were discovered, but itinerary composition is temporarily unavailable. The Qloo recommendations remain visible on the map.</div>
      </section>
    </template>
  </main>
</template>

<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import { useRouter } from 'vue-router'
import TasteProfileCard from '@/components/taste/TasteProfileCard.vue'
import TasteExplanation from '@/components/trip/TasteExplanation.vue'
import ItineraryMap from '@/components/trip/ItineraryMap.vue'
import type { PlaceCandidate, TasteRoutePlan } from '@/types/taste'
import { parseStoredTasteRoutePlan } from '@/utils/tasteRoute'
import { buildItineraryMapModel, getDayColor, itineraryMarkerId } from '@/utils/itineraryMap'

const router = useRouter()
const raw = sessionStorage.getItem('tasteRoutePlan')
const plan = ref<TasteRoutePlan | null>(parseStoredTasteRoutePlan(raw))
const selectedMarkerId = ref<string | null>(null)
const mapModel = computed(() => plan.value
  ? buildItineraryMapModel(plan.value)
  : { markers: [], routes: [] })

function candidateFor(id: string): PlaceCandidate | null {
  return plan.value?.candidates.find((candidate) => candidate.id === id) ?? null
}

function selectMarker(markerId: string, reveal = false) {
  selectedMarkerId.value = markerId
  if (reveal) {
    void nextTick(() => {
      const card = document.querySelector<HTMLElement>(`[data-marker-id="${CSS.escape(markerId)}"]`)
      card?.scrollIntoView?.({ behavior: 'smooth', block: 'center' })
      card?.focus({ preventScroll: true })
    })
  }
}
</script>

<style scoped>
.result-shell { min-height: 100vh; padding: 44px clamp(18px, 5vw, 76px) 80px; color: #251d35; background: #f7f4ed; }
header { display: flex; align-items: flex-start; gap: 32px; max-width: 1250px; margin: auto; }.back { margin-top: 10px; border: 0; background: transparent; color: #6747ac; cursor: pointer; }
.eyebrow { margin: 0; color: #7656b8; font-size: .72rem; font-weight: 800; letter-spacing: .18em; }h1 { margin: .25rem 0; font: 500 clamp(2.5rem, 5vw, 4.5rem)/1 Georgia, serif; }
.warnings, .empty-state, .empty-days { max-width: 1180px; margin: 24px auto; padding: 18px 22px; border: 1px solid #eadbb0; border-radius: 14px; background: #fff8df; }.warnings p { margin: .45rem 0 0; }
.overview { display: grid; grid-template-columns: minmax(280px, .75fr) minmax(420px, 1.5fr); gap: 20px; max-width: 1180px; margin: 34px auto; }.profile-stack { display: grid; gap: 14px; }.trace-card { padding: 18px; border-radius: 14px; background: #fff; box-shadow: 0 12px 32px rgba(50,35,70,.08); }.trace-step { display: grid; grid-template-columns: 10px 1fr auto; align-items: center; gap: 9px; margin-top: 10px; font-size: .85rem; }.trace-step small { color: #756a81; text-transform: capitalize; }.status { width: 9px; height: 9px; border-radius: 50%; background: #8a7b9a; }.status.completed { background: #3d9870; }.status.repaired { background: #c98924; }.status.failed { background: #c24b5f; }
.days { max-width: 1000px; margin: 54px auto 0; }.day { display: grid; grid-template-columns: 150px 1fr; gap: 30px; margin-bottom: 55px; }.day-heading span { color: var(--day-color); font-size: .75rem; font-weight: 800; letter-spacing: .14em; }.day-heading h2 { margin: .5rem 0; font: 500 1.35rem Georgia, serif; }
.stops { border-left: 1px solid #cfc5da; }.stop { display: grid; grid-template-columns: 82px 1fr; gap: 15px; margin: 0 0 25px -1px; }.time { padding-top: 7px; color: #675d71; font-size: .86rem; }.stop-body { display: grid; grid-template-columns: 120px 1fr; gap: 18px; padding: 20px; border-radius: 16px; background: white; box-shadow: 0 12px 32px rgba(50,35,70,.08); }.stop-body img { width: 120px; height: 110px; object-fit: cover; border-radius: 10px; }.stop-body h3 { margin: 0 0 .35rem; font-size: 1.2rem; }.address { color: #7a7084; font-size: .85rem; }
.stop { border-radius: 16px; cursor: pointer; outline: none; }.stop.is-selected .stop-body { box-shadow: 0 0 0 3px color-mix(in srgb, var(--day-color) 72%, white), 0 16px 38px rgba(50,35,70,.16); }.stop:focus-visible .stop-body { box-shadow: 0 0 0 3px #bda9ed, 0 16px 38px rgba(50,35,70,.16); }
@media (max-width: 760px) { .overview { grid-template-columns: 1fr; }.day { grid-template-columns: 1fr; }.stop { grid-template-columns: 60px 1fr; }.stop-body { grid-template-columns: 1fr; }.stop-body img { width: 100%; } }
</style>
