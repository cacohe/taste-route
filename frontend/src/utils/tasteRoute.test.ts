import { describe, expect, it } from 'vitest'

import { parseStoredTasteRoutePlan, validateTasteRouteDraft } from './tasteRoute'

describe('parseStoredTasteRoutePlan', () => {
  it('returns null for corrupt or structurally invalid session data', () => {
    expect(parseStoredTasteRoutePlan('{broken')).toBeNull()
    expect(parseStoredTasteRoutePlan('{"destination":"Tokyo"}')).toBeNull()
  })

  it('rejects invalid nested candidate and itinerary data', () => {
    const base = {
      request_id: 'request-1', destination: 'Tokyo',
      start_date: '2026-11-10', end_date: '2026-11-11',
      taste_profile: { tags: [] }, warnings: [],
      completion_status: 'completed', locality: null, decisions: [], routes: [],
    }

    expect(parseStoredTasteRoutePlan(JSON.stringify({
      ...base, candidates: [null], days: [],
    }))).toBeNull()
    expect(parseStoredTasteRoutePlan(JSON.stringify({
      ...base, candidates: [], days: [null],
    }))).toBeNull()
  })

  it('accepts a minimally valid plan', () => {
    const raw = JSON.stringify({
      request_id: 'request-1',
      destination: 'Tokyo',
      start_date: '2026-11-10',
      end_date: '2026-11-11',
      taste_profile: { tags: [] },
      candidates: [],
      days: [],
      warnings: [],
      completion_status: 'partial',
      locality: null,
      decisions: [],
      routes: [],
    })

    expect(parseStoredTasteRoutePlan(raw)?.request_id).toBe('request-1')
  })

  it('rejects a completed stored plan with no itinerary stops', () => {
    const raw = JSON.stringify({
      request_id: 'request-empty', destination: 'Tokyo',
      start_date: '2026-11-10', end_date: '2026-11-11',
      taste_profile: { tags: [] }, candidates: [], days: [], warnings: [],
      completion_status: 'completed', locality: null, decisions: [], routes: [],
    })

    expect(parseStoredTasteRoutePlan(raw)).toBeNull()
  })

  it('rejects invalid decisions, completion status, route geometry, and legs', () => {
    const base = {
      request_id: 'request-1', destination: 'Tokyo', start_date: '2026-11-10', end_date: '2026-11-11',
      taste_profile: { tags: [] }, candidates: [], days: [], warnings: [],
      completion_status: 'completed', locality: null, decisions: [], routes: [],
    }
    expect(parseStoredTasteRoutePlan(JSON.stringify({ ...base, completion_status: 'done' }))).toBeNull()
    expect(parseStoredTasteRoutePlan(JSON.stringify({ ...base, decisions: [{ iteration: 1, action: 'browse_web', status: 'completed', reason: 'x', metrics: {} }] }))).toBeNull()
    expect(parseStoredTasteRoutePlan(JSON.stringify({ ...base, routes: [{ date: '2026-11-10', profile: 'driving', geometry: [['bad', 1]], legs: [], distance_meters: 1, duration_minutes: 1 }] }))).toBeNull()
    expect(parseStoredTasteRoutePlan(JSON.stringify({ ...base, routes: [{ date: '2026-11-10', profile: 'driving', geometry: [[1, 2]], legs: [{ from_place_id: 'a' }], distance_meters: 1, duration_minutes: 1 }] }))).toBeNull()
  })
})

describe('validateTasteRouteDraft', () => {
  it('rejects trips longer than 30 calendar days', () => {
    expect(validateTasteRouteDraft({
      destination: 'Tokyo',
      startDate: '2026-11-01',
      endDate: '2026-12-01',
      tasteSeedCount: 1,
    })).toBe('Trips cannot exceed 30 days.')
  })
})
