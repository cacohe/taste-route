import { describe, expect, it, vi } from 'vitest'

import type { AgentDecision, TasteRouteResponse } from '@/types/taste'
import { consumeTripPlanStream } from './tripStream'

const result: TasteRouteResponse = {
  success: true,
  message: 'TasteRoute planning completed.',
  data: {
    request_id: 'request-1',
    destination: 'Tokyo',
    start_date: '2026-11-10',
    end_date: '2026-11-11',
    taste_profile: { tags: [], seeds: [] },
    candidates: [],
    days: [],
    warnings: [],
    completion_status: 'completed', locality: { id: 'tokyo', name: 'Tokyo' }, decisions: [], routes: [],
  },
  error_code: null,
  retryable: false,
}

function streamingResponse(...chunks: string[]): Response {
  const encoder = new TextEncoder()
  return new Response(new ReadableStream({
    start(controller) {
      chunks.forEach((chunk) => controller.enqueue(encoder.encode(chunk)))
      controller.close()
    },
  }), { status: 200 })
}

describe('consumeTripPlanStream', () => {
  it('preserves partial NDJSON lines across byte chunks', async () => {
    const onProgress = vi.fn<(decision: AgentDecision) => void>()
    const progress = JSON.stringify({
      type: 'progress',
      decision: { iteration: 1, action: 'resolve_locality', status: 'completed', reason: 'Resolved.', metrics: { result_count: 2 } },
    })
    const terminal = JSON.stringify({ type: 'result', response: result })

    const response = await consumeTripPlanStream(
      streamingResponse(progress.slice(0, 24), `${progress.slice(24)}\n${terminal}\n`),
      onProgress,
    )

    expect(onProgress).toHaveBeenCalledWith({
      iteration: 1, action: 'resolve_locality', status: 'completed', reason: 'Resolved.', metrics: { result_count: 2 },
    })
    expect(response.data?.request_id).toBe('request-1')
  })

  it('throws the public message from an error record', async () => {
    const record = JSON.stringify({
      type: 'error',
      error: { error_code: 'QLOO_RATE_LIMITED', message: 'Qloo is busy.', retryable: true },
    })

    await expect(consumeTripPlanStream(streamingResponse(`${record}\n`), () => {}))
      .rejects.toThrow('Qloo is busy.')
  })

  it('rejects a stream that closes without a result', async () => {
    const progress = JSON.stringify({
      type: 'progress',
      decision: { iteration: 1, action: 'resolve_locality', status: 'completed', reason: 'Resolved.', metrics: {} },
    })

    await expect(consumeTripPlanStream(streamingResponse(`${progress}\n`), () => {}))
      .rejects.toThrow('ended before returning an itinerary')
  })
})
