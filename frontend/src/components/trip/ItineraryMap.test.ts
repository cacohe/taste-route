import { flushPromises, mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { ItineraryMapModel } from '@/utils/itineraryMap'
import ItineraryMap from './ItineraryMap.vue'

const mapState = vi.hoisted(() => ({
  markers: [] as HTMLElement[],
  handlers: new Map<string, (event?: unknown) => void>(),
  layers: [] as unknown[],
  easeTo: vi.fn(),
}))

vi.mock('maplibre-gl', () => {
  class Map {
    constructor() { mapState.handlers.clear(); mapState.layers = [] }
    on(event: string, handler: (event?: unknown) => void) {
      mapState.handlers.set(event, handler)
      if (event === 'load') queueMicrotask(() => handler())
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
  return { Map, Marker, Popup, LngLatBounds, NavigationControl }
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
  })

  it('renders itinerary-only markers and a route layer', async () => {
    mount(ItineraryMap, { props: { model, selectedMarkerId: null } })
    await flushPromises()

    expect(mapState.markers.map((marker) => marker.textContent)).toEqual(['D1-1', 'D1-2'])
    expect(mapState.layers).toHaveLength(2)
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
