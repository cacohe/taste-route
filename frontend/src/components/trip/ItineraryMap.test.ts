import { flushPromises, mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { ItineraryMapModel } from '@/utils/itineraryMap'
import ItineraryMap from './ItineraryMap.vue'

const mapState = vi.hoisted(() => ({
  markers: [] as HTMLElement[],
  handlers: new Map<string, (event?: unknown) => void>(),
  layers: [] as unknown[],
  easeTo: vi.fn(),
  setWorkerUrl: vi.fn(),
  syncLoad: false,
}))

vi.mock('maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url', () => ({ default: '/maplibre-worker.js' }))

vi.mock('maplibre-gl', () => {
  class Map {
    constructor() { mapState.handlers.clear(); mapState.layers = [] }
    on(event: string, handler: (event?: unknown) => void) {
      mapState.handlers.set(event, handler)
      if (event === 'load') {
        if (mapState.syncLoad) handler()
        else queueMicrotask(() => handler())
      }
      return this
    }
    addControl() { return this }
    addSource() { return this }
    addLayer(layer: unknown) { mapState.layers.push(layer); return this }
    fitBounds() { return this }
    easeTo(options: unknown) { mapState.easeTo(options); return this }
    remove() {}
  }
  class Marker {
    element: HTMLElement
    constructor(options: { element: HTMLElement }) { this.element = options.element; mapState.markers.push(options.element) }
    setLngLat() { return this }
    setPopup() { return this }
    addTo() { return this }
  }
  class Popup { setText() { return this } }
  class LngLatBounds { extend() { return this } }
  class NavigationControl {}
  return { Map, Marker, Popup, LngLatBounds, NavigationControl, setWorkerUrl: mapState.setWorkerUrl }
})

const model: ItineraryMapModel = {
  markers: [
    { id: 'day-1-a', placeId: 'a', name: 'Place A', label: 'D1-1', color: '#6342ad', coordinates: [139.7, 35.6], kind: 'itinerary' },
    { id: 'day-1-b', placeId: 'b', name: 'Place B', label: 'D1-2', color: '#6342ad', coordinates: [139.8, 35.7], kind: 'itinerary' },
  ],
  routes: [{ date: '2026-11-10', color: '#6342ad', coordinates: [[139.7, 35.6], [139.8, 35.7]] }],
}

describe('ItineraryMap', () => {
  beforeEach(() => {
    mapState.markers = []
    mapState.handlers.clear()
    mapState.layers = []
    mapState.easeTo.mockReset()
    mapState.setWorkerUrl.mockReset()
    mapState.syncLoad = false
  })

  afterEach(() => vi.useRealTimers())

  it('renders itinerary-only markers and a route layer', async () => {
    mount(ItineraryMap, { props: { model, selectedMarkerId: null } })
    await flushPromises()

    expect(mapState.markers.map((marker) => marker.textContent)).toEqual(['D1-1', 'D1-2'])
    expect(mapState.layers).toHaveLength(2)
    expect(mapState.setWorkerUrl).toHaveBeenCalledWith('/maplibre-worker.js')
  })

  it('emits marker selection and highlights selection from the itinerary list', async () => {
    const wrapper = mount(ItineraryMap, { props: { model, selectedMarkerId: null } })
    await flushPromises()

    mapState.markers[0].click()
    expect(wrapper.emitted('select')).toEqual([['day-1-a']])

    await wrapper.setProps({ selectedMarkerId: 'day-1-b' })
    expect(mapState.markers[1].classList.contains('is-selected')).toBe(true)
    expect(mapState.easeTo).toHaveBeenCalled()
  })

  it('surfaces asynchronous basemap failures', async () => {
    const wrapper = mount(ItineraryMap, { props: { model, selectedMarkerId: null } })
    await flushPromises()

    mapState.handlers.get('error')?.({ error: new Error('tile failed') })
    await nextTick()

    expect(wrapper.text()).toContain('basemap is temporarily unavailable')
  })

  it('does not report a timeout when the map loads synchronously', async () => {
    vi.useFakeTimers()
    mapState.syncLoad = true
    const wrapper = mount(ItineraryMap, { props: { model, selectedMarkerId: null } })
    await flushPromises()

    expect(vi.getTimerCount()).toBe(0)
    await vi.advanceTimersByTimeAsync(12_001)
    await nextTick()

    expect(wrapper.text()).not.toContain('taking longer than expected')
  })

  it('explains candidate fallback markers when no route was composed', async () => {
    const fallback: ItineraryMapModel = {
      routes: [],
      markers: [{ ...model.markers[0], kind: 'candidate', label: '1' }],
    }
    const wrapper = mount(ItineraryMap, { props: { model: fallback, selectedMarkerId: null } })
    await flushPromises()

    expect(wrapper.text()).toContain('Discovered Qloo places')
  })
})
