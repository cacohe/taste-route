import { afterEach, describe, expect, it, vi } from 'vitest'

import type { TasteRouteRequest } from '@/types/taste'
import apiClient, { generateTripPlanStream } from './api'

afterEach(() => vi.unstubAllGlobals())

describe('api client', () => {
  it('uses the same-origin Vite proxy when no API base URL is configured', () => {
    expect(apiClient.defaults.baseURL).toBe('')
  })

  it('posts the request to the streaming endpoint and forwards progress', async () => {
    const request: TasteRouteRequest = {
      destination: 'Tokyo', start_date: '2026-11-10', end_date: '2026-11-11',
      pace: 'balanced', budget: 'medium', constraints: [], excluded_place_ids: [],
      taste_seeds: [{ id: 'movie-1', name: 'Spirited Away', entity_type: 'movie' }],
    }
    const response = {
      success: true, message: 'Done', error_code: null, retryable: false,
      data: {
        request_id: 'request-1', destination: 'Tokyo', start_date: '2026-11-10', end_date: '2026-11-11',
        taste_profile: { tags: [], seeds: [] }, candidates: [], days: [], warnings: [], trace: [],
      },
    }
    const body = `${JSON.stringify({ type: 'progress', step: { key: 'taste_resolution', label: 'Resolve taste signals', status: 'active' } })}\n${JSON.stringify({ type: 'result', response })}\n`
    const fetchMock = vi.fn().mockResolvedValue(new Response(body, { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)
    const onProgress = vi.fn()

    const result = await generateTripPlanStream(request, onProgress)

    expect(result.data?.request_id).toBe('request-1')
    expect(onProgress).toHaveBeenCalledOnce()
    expect(fetchMock).toHaveBeenCalledWith('/api/trip/plan/stream', expect.objectContaining({
      method: 'POST', body: JSON.stringify(request),
    }))
  })
})
