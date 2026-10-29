import { mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { beforeEach, describe, expect, it } from 'vitest'

import type { TasteRoutePlan } from '@/types/taste'
import Result from './Result.vue'

const ItineraryMapStub = {
  name: 'ItineraryMap',
  props: ['model', 'selectedMarkerId'],
  emits: ['select'],
  template: '<button data-test="map-select" @click="$emit(\'select\', model.markers[0].id)">{{ selectedMarkerId || \'none\' }}</button>',
}

const plan: TasteRoutePlan = {
  request_id: 'request-1', destination: 'Tokyo', start_date: '2026-11-10', end_date: '2026-11-10',
  taste_profile: { tags: ['Animation'], seeds: [] }, warnings: [],
  completion_status: 'completed', locality: { id: 'tokyo-id', name: 'Tokyo Metropolis' },
  decisions: [{ iteration: 1, action: 'resolve_locality', status: 'completed', reason: 'Matched by Qloo.', metrics: { result_count: 2 } }],
  routes: [{
    date: '2026-11-10', profile: 'driving', geometry: [[139.8, 35.7], [139.7, 35.6]],
    legs: [{ from_place_id: 'b', to_place_id: 'a', distance_meters: 2400, duration_minutes: 14 }],
    distance_meters: 2400, duration_minutes: 14,
  }],
  candidates: [
    { id: 'a', name: 'Place A', address: null, description: null, image_url: null, latitude: 35.6, longitude: 139.7, affinity: .8, tags: [], contributions: [] },
    { id: 'b', name: 'Place B', address: null, description: null, image_url: null, latitude: 35.7, longitude: 139.8, affinity: .7, tags: [], contributions: [] },
  ],
  days: [{ date: '2026-11-10', items: [
    { place_id: 'b', start_time: '09:00', duration_minutes: 60, reason: 'First' },
    { place_id: 'a', start_time: '11:00', duration_minutes: 60, reason: 'Second' },
  ] }],
}

async function mountResult() {
  const router = createRouter({ history: createMemoryHistory(), routes: [
    { path: '/', component: { template: '<div>Home</div>' } },
    { path: '/result', component: Result },
  ] })
  await router.push('/result')
  await router.isReady()
  return mount(Result, {
    global: {
      plugins: [router],
      stubs: { ItineraryMap: ItineraryMapStub, TasteProfileCard: true, TasteExplanation: true },
    },
  })
}

describe('Result map and itinerary linkage', () => {
  beforeEach(() => sessionStorage.setItem('tasteRoutePlan', JSON.stringify(plan)))

  it('highlights a stop selected from the map and sends card selection back to the map', async () => {
    const wrapper = await mountResult()

    await wrapper.get('[data-test="map-select"]').trigger('click')
    expect(wrapper.get('[data-marker-id="2026-11-10-0-b"]').classes()).toContain('is-selected')

    await wrapper.get('[data-marker-id="2026-11-10-1-a"]').trigger('click')
    expect(wrapper.get('[data-test="map-select"]').text()).toBe('2026-11-10-1-a')
  })

  it('shows resolved locality, completion, decisions, and driving leg evidence', async () => {
    const wrapper = await mountResult()
    expect(wrapper.text()).toContain('Tokyo Metropolis')
    expect(wrapper.text()).toContain('Completed')
    expect(wrapper.text()).toContain('Matched by Qloo.')
    expect(wrapper.text()).toContain('2.4 km')
    expect(wrapper.text()).toContain('14 min driving')
  })
})
