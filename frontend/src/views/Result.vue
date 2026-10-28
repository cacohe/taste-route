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
        <article class="map-card">
          <div ref="mapContainer" class="map" aria-label="MapLibre itinerary map"></div>
          <p v-if="mapError" class="map-error">{{ mapError }}</p>
        </article>
      </div>

      <section class="days">
        <article v-for="(day, dayIndex) in plan.days" :key="day.date" class="day">
          <div class="day-heading">
            <span>DAY {{ String(dayIndex + 1).padStart(2, '0') }}</span>
            <h2>{{ day.date }}</h2>
          </div>
          <div class="stops">
            <article v-for="item in day.items" :key="`${day.date}-${item.place_id}`" class="stop">
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
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import 'maplibre-gl/dist/maplibre-gl.css'
import type { Map as MapLibreMap } from 'maplibre-gl'
import TasteProfileCard from '@/components/taste/TasteProfileCard.vue'
import TasteExplanation from '@/components/trip/TasteExplanation.vue'
import type { PlaceCandidate, TasteRoutePlan } from '@/types/taste'
import { parseStoredTasteRoutePlan } from '@/utils/tasteRoute'
import { getMapStyleUrl } from '@/utils/mapConfig'

const router = useRouter()
const mapContainer = ref<HTMLElement | null>(null)
const mapError = ref('')
const raw = sessionStorage.getItem('tasteRoutePlan')
const plan = ref<TasteRoutePlan | null>(parseStoredTasteRoutePlan(raw))
let map: MapLibreMap | null = null

function candidateFor(id: string): PlaceCandidate | null {
  return plan.value?.candidates.find((candidate) => candidate.id === id) ?? null
}

async function initMap() {
  if (!plan.value || !mapContainer.value) return
  const located = plan.value.candidates.filter(
    (candidate) => candidate.longitude !== null && candidate.latitude !== null,
  )
  if (!located.length) {
    mapError.value = 'Qloo returned no mappable coordinates.'
    return
  }
  try {
    const { LngLatBounds, Map, Marker, NavigationControl, Popup } = await import('maplibre-gl')
    map = new Map({
      container: mapContainer.value,
      style: getMapStyleUrl(),
      center: [located[0].longitude!, located[0].latitude!],
      zoom: 11,
    })
    map.addControl(new NavigationControl(), 'top-right')
    const bounds = new LngLatBounds()
    located.forEach((candidate, index) => {
      const marker = document.createElement('button')
      marker.className = 'taste-marker'
      marker.textContent = String(index + 1)
      marker.title = candidate.name
      new Marker({ element: marker })
        .setLngLat([candidate.longitude!, candidate.latitude!])
        .setPopup(new Popup({ offset: 20 }).setText(candidate.name))
        .addTo(map!)
      bounds.extend([candidate.longitude!, candidate.latitude!])
    })
    if (located.length > 1) map.fitBounds(bounds, { padding: 55, maxZoom: 13 })
  } catch {
    mapError.value = 'The basemap is temporarily unavailable. Place evidence and coordinates are still preserved.'
  }
}

onMounted(async () => { await nextTick(); await initMap() })
onBeforeUnmount(() => map?.remove())
</script>

<style scoped>
.result-shell { min-height: 100vh; padding: 44px clamp(18px, 5vw, 76px) 80px; color: #251d35; background: #f7f4ed; }
header { display: flex; align-items: flex-start; gap: 32px; max-width: 1250px; margin: auto; }.back { margin-top: 10px; border: 0; background: transparent; color: #6747ac; cursor: pointer; }
.eyebrow { margin: 0; color: #7656b8; font-size: .72rem; font-weight: 800; letter-spacing: .18em; }h1 { margin: .25rem 0; font: 500 clamp(2.5rem, 5vw, 4.5rem)/1 Georgia, serif; }
.warnings, .empty-state, .empty-days { max-width: 1180px; margin: 24px auto; padding: 18px 22px; border: 1px solid #eadbb0; border-radius: 14px; background: #fff8df; }.warnings p { margin: .45rem 0 0; }
.overview { display: grid; grid-template-columns: minmax(280px, .75fr) minmax(420px, 1.5fr); gap: 20px; max-width: 1180px; margin: 34px auto; }.profile-stack { display: grid; gap: 14px; }.trace-card { padding: 18px; border-radius: 14px; background: #fff; box-shadow: 0 12px 32px rgba(50,35,70,.08); }.trace-step { display: grid; grid-template-columns: 10px 1fr auto; align-items: center; gap: 9px; margin-top: 10px; font-size: .85rem; }.trace-step small { color: #756a81; text-transform: capitalize; }.status { width: 9px; height: 9px; border-radius: 50%; background: #8a7b9a; }.status.completed { background: #3d9870; }.status.repaired { background: #c98924; }.status.failed { background: #c24b5f; }.map-card { position: relative; min-height: 330px; overflow: hidden; border-radius: 18px; background: #e6e0d7; box-shadow: 0 18px 45px rgba(45,30,80,.12); }.map { width: 100%; height: 100%; min-height: 330px; }.map-error { position: absolute; inset: auto 12px 12px; margin: 0; padding: 10px; border-radius: 8px; background: rgba(255,255,255,.92); }
.days { max-width: 1000px; margin: 54px auto 0; }.day { display: grid; grid-template-columns: 150px 1fr; gap: 30px; margin-bottom: 55px; }.day-heading span { color: #7757b5; font-size: .75rem; font-weight: 800; letter-spacing: .14em; }.day-heading h2 { margin: .5rem 0; font: 500 1.35rem Georgia, serif; }
.stops { border-left: 1px solid #cfc5da; }.stop { display: grid; grid-template-columns: 82px 1fr; gap: 15px; margin: 0 0 25px -1px; }.time { padding-top: 7px; color: #675d71; font-size: .86rem; }.stop-body { display: grid; grid-template-columns: 120px 1fr; gap: 18px; padding: 20px; border-radius: 16px; background: white; box-shadow: 0 12px 32px rgba(50,35,70,.08); }.stop-body img { width: 120px; height: 110px; object-fit: cover; border-radius: 10px; }.stop-body h3 { margin: 0 0 .35rem; font-size: 1.2rem; }.address { color: #7a7084; font-size: .85rem; }
:global(.taste-marker) { width: 29px; height: 29px; border: 2px solid white; border-radius: 50%; background: #6342ad; color: white; font-weight: 800; box-shadow: 0 3px 9px #51436866; cursor: pointer; }
@media (max-width: 760px) { .overview { grid-template-columns: 1fr; }.day { grid-template-columns: 1fr; }.stop { grid-template-columns: 60px 1fr; }.stop-body { grid-template-columns: 1fr; }.stop-body img { width: 100%; } }
</style>
