import { describe, expect, it } from 'vitest'

import type { PlaceCandidate, TasteRoutePlan } from '@/types/taste'
import { buildItineraryMapModel } from './itineraryMap'

function candidate(id: string, longitude: number | null, latitude: number | null): PlaceCandidate {
  return {
    id, name: `Place ${id}`, address: null, description: null, image_url: null,
    longitude, latitude, affinity: null, tags: [], contributions: [],
  }
}

function plan(overrides: Partial<TasteRoutePlan> = {}): TasteRoutePlan {
  return {
    request_id: 'request-1', destination: 'Tokyo', start_date: '2026-11-10', end_date: '2026-11-11',
    taste_profile: { tags: [], seeds: [] }, warnings: [], trace: [],
    candidates: [candidate('a', 139.70, 35.68), candidate('b', 139.71, 35.69), candidate('unused', 139.72, 35.70)],
    days: [
      { date: '2026-11-10', items: [
        { place_id: 'b', start_time: '09:00', duration_minutes: 60, reason: 'First' },
        { place_id: 'a', start_time: '11:00', duration_minutes: 60, reason: 'Second' },
      ] },
    ],
    ...overrides,
  }
}

describe('buildItineraryMapModel', () => {
  it('numbers only itinerary stops in day and visit order', () => {
    const model = buildItineraryMapModel(plan())

    expect(model.markers.map(({ placeId, label }) => [placeId, label])).toEqual([
      ['b', 'D1-1'], ['a', 'D1-2'],
    ])
  })

  it('builds one ordered coordinate route per day', () => {
    const model = buildItineraryMapModel(plan())

    expect(model.routes).toEqual([
      expect.objectContaining({ date: '2026-11-10', coordinates: [[139.71, 35.69], [139.70, 35.68]] }),
    ])
  })

  it('skips itinerary items that have no mappable matching candidate', () => {
    const source = plan({
      candidates: [candidate('a', null, 35.68)],
      days: [{ date: '2026-11-10', items: [
        { place_id: 'missing', start_time: '09:00', duration_minutes: 60, reason: 'Missing' },
        { place_id: 'a', start_time: '11:00', duration_minutes: 60, reason: 'No longitude' },
      ] }],
    })

    expect(buildItineraryMapModel(source)).toEqual({ markers: [], routes: [] })
  })

  it('shows discovered candidates as fallback evidence when no itinerary exists', () => {
    const model = buildItineraryMapModel(plan({ days: [] }))

    expect(model.routes).toEqual([])
    expect(model.markers.map(({ placeId, kind }) => [placeId, kind])).toEqual([
      ['a', 'candidate'], ['b', 'candidate'], ['unused', 'candidate'],
    ])
  })
})
