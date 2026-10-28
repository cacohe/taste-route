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
    })

    expect(parseStoredTasteRoutePlan(raw)?.request_id).toBe('request-1')
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
