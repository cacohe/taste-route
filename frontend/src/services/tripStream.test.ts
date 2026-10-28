import { describe, expect, it, vi } from 'vitest'

import type { TasteRouteResponse, WorkflowStep } from '@/types/taste'
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
    trace: [],
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
    const onProgress = vi.fn<(step: WorkflowStep) => void>()
    const progress = JSON.stringify({
      type: 'progress',
      step: { key: 'taste_resolution', label: 'Resolve taste signals', status: 'completed' },
    })
    const terminal = JSON.stringify({ type: 'result', response: result })

    const response = await consumeTripPlanStream(
      streamingResponse(progress.slice(0, 24), `${progress.slice(24)}\n${terminal}\n`),
      onProgress,
    )

    expect(onProgress).toHaveBeenCalledWith({
      key: 'taste_resolution', label: 'Resolve taste signals', status: 'completed',
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
      step: { key: 'taste_resolution', label: 'Resolve taste signals', status: 'active' },
    })

    await expect(consumeTripPlanStream(streamingResponse(`${progress}\n`), () => {}))
      .rejects.toThrow('ended before returning an itinerary')
  })
})
