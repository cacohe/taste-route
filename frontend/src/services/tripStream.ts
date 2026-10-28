import type { TasteRouteResponse, WorkflowStep } from '@/types/taste'

type StreamRecord =
  | { type: 'progress'; step: WorkflowStep }
  | { type: 'result'; response: TasteRouteResponse }
  | { type: 'error'; error: { message: string } }

export async function consumeTripPlanStream(
  response: Response,
  onProgress: (step: WorkflowStep) => void,
): Promise<TasteRouteResponse> {
  if (!response.body) throw new Error('The planning stream is unavailable.')

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let result: TasteRouteResponse | null = null

  const consumeLine = (line: string) => {
    if (!line.trim()) return
    const record = JSON.parse(line) as StreamRecord
    if (record.type === 'progress') onProgress(record.step)
    if (record.type === 'result') result = record.response
    if (record.type === 'error') throw new Error(record.error.message)
  }

  while (true) {
    const { done, value } = await reader.read()
    buffer += decoder.decode(value, { stream: !done })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''
    lines.forEach(consumeLine)
    if (done) break
  }
  consumeLine(buffer)

  if (!result) throw new Error('The planning stream ended before returning an itinerary.')
  return result
}
