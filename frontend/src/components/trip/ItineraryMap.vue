<template>
  <article class="map-card">
    <div ref="mapContainer" class="map" aria-label="Interactive itinerary map"></div>
    <p v-if="model.routes.length === 0 && model.markers.some((marker) => marker.kind === 'candidate')" class="map-note">
      Discovered Qloo places are shown while itinerary composition is unavailable.
    </p>
    <p v-if="mapError" class="map-error" role="alert">{{ mapError }}</p>
  </article>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import 'maplibre-gl/dist/maplibre-gl.css'
import type { Map as MapLibreMap } from 'maplibre-gl'
import type { ItineraryMapModel } from '@/utils/itineraryMap'
import { getMapStyleUrl } from '@/utils/mapConfig'

const props = defineProps<{ model: ItineraryMapModel; selectedMarkerId: string | null }>()
const emit = defineEmits<{ select: [markerId: string] }>()

const mapContainer = ref<HTMLElement | null>(null)
const mapError = ref('')
const markerElements = new Map<string, HTMLButtonElement>()
let map: MapLibreMap | null = null
let loadTimer: ReturnType<typeof setTimeout> | null = null

function clearLoadTimer() {
  if (loadTimer !== null) clearTimeout(loadTimer)
  loadTimer = null
}

function updateSelection(markerId: string | null) {
  markerElements.forEach((element, id) => element.classList.toggle('is-selected', id === markerId))
  const selected = props.model.markers.find((marker) => marker.id === markerId)
  if (selected && map) map.easeTo({ center: selected.coordinates, duration: 500 })
}

async function initMap() {
  if (!mapContainer.value || !props.model.markers.length) {
    mapError.value = 'Qloo returned no mappable coordinates.'
    return
  }
  try {
    const { LngLatBounds, Map, Marker, NavigationControl, Popup } = await import('maplibre-gl')
    const first = props.model.markers[0]
    map = new Map({
      container: mapContainer.value,
      style: getMapStyleUrl(),
      center: first.coordinates,
      zoom: 11,
    })
    map.on('error', () => {
      mapError.value = 'The basemap is temporarily unavailable. Itinerary evidence is still available below.'
    })
    map.on('load', () => {
      clearLoadTimer()
      props.model.routes.forEach((route, index) => {
        const sourceId = `taste-route-${index}`
        map?.addSource(sourceId, {
          type: 'geojson',
          data: { type: 'Feature', properties: {}, geometry: { type: 'LineString', coordinates: route.coordinates } },
        })
        map?.addLayer({
          id: `${sourceId}-casing`, source: sourceId, type: 'line',
          paint: { 'line-color': '#ffffff', 'line-width': 7, 'line-opacity': .88 },
        })
        map?.addLayer({
          id: sourceId, source: sourceId, type: 'line',
          paint: { 'line-color': route.color, 'line-width': 4, 'line-opacity': .9 },
        })
      })
    })
    map.addControl(new NavigationControl(), 'top-right')
    const bounds = new LngLatBounds()
    props.model.markers.forEach((marker) => {
      const element = document.createElement('button')
      element.type = 'button'
      element.className = `taste-marker ${marker.kind === 'candidate' ? 'is-candidate' : ''}`
      element.textContent = marker.label
      element.title = marker.name
      element.setAttribute('aria-label', `${marker.label}: ${marker.name}`)
      element.style.setProperty('--marker-color', marker.color)
      element.addEventListener('click', () => emit('select', marker.id))
      markerElements.set(marker.id, element)
      new Marker({ element })
        .setLngLat(marker.coordinates)
        .setPopup(new Popup({ offset: 22 }).setText(marker.name))
        .addTo(map!)
      bounds.extend(marker.coordinates)
    })
    if (props.model.markers.length > 1) map.fitBounds(bounds, { padding: 55, maxZoom: 14 })
    updateSelection(props.selectedMarkerId)
    loadTimer = setTimeout(() => {
      mapError.value = 'The basemap is taking too long to load. Itinerary evidence is still available below.'
    }, 12000)
  } catch {
    mapError.value = 'The basemap is temporarily unavailable. Itinerary evidence is still available below.'
  }
}

watch(() => props.selectedMarkerId, updateSelection)
onMounted(async () => { await nextTick(); await initMap() })
onBeforeUnmount(() => {
  clearLoadTimer()
  markerElements.clear()
  map?.remove()
})
</script>

<style scoped>
.map-card { position: relative; min-height: 330px; overflow: hidden; border-radius: 18px; background: #e6e0d7; box-shadow: 0 18px 45px rgba(45,30,80,.12); }
.map { width: 100%; height: 100%; min-height: 330px; }
.map-error, .map-note { position: absolute; inset: auto 12px 12px; margin: 0; padding: 10px 12px; border-radius: 9px; background: rgba(255,255,255,.94); color: #4f445d; font-size: .78rem; box-shadow: 0 4px 18px #33264d22; }
.map-error { color: #9b3348; }.map-note + .map-error { bottom: 58px; }
:global(.taste-marker) { min-width: 34px; height: 30px; padding: 0 7px; border: 2px solid white; border-radius: 999px; background: var(--marker-color, #6342ad); color: white; font-size: .7rem; font-weight: 800; box-shadow: 0 3px 9px #51436866; cursor: pointer; transition: transform .16s ease, box-shadow .16s ease; }
:global(.taste-marker.is-candidate) { opacity: .78; }
:global(.taste-marker.is-selected) { transform: scale(1.24); box-shadow: 0 0 0 4px #ffffffaa, 0 5px 16px #39276788; z-index: 2; }
:global(.taste-marker:focus-visible) { outline: 3px solid #f2bd5a; outline-offset: 2px; }
@media (prefers-reduced-motion: reduce) { :global(.taste-marker) { transition: none; } }
</style>
