import axios from 'axios'
import type {
  TasteEntitySearchResponse,
  TasteRouteRequest,
  TasteRouteResponse,
  AgentDecision,
} from '@/types/taste'
import { getErrorMessage } from '@/utils/errorMessage'
import { consumeTripPlanStream } from './tripStream'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 240000,
  headers: {
    'Content-Type': 'application/json'
  }
})

/**
 * Generate a grounded itinerary.
 */
export async function generateTripPlan(formData: TasteRouteRequest): Promise<TasteRouteResponse> {
  try {
    const response = await apiClient.post<TasteRouteResponse>('/api/trip/plan', formData)
    return response.data
  } catch (error: unknown) {
    throw new Error(getErrorMessage(error, 'Could not generate the itinerary.'))
  }
}

export async function generateTripPlanStream(
  formData: TasteRouteRequest,
  onProgress: (decision: AgentDecision) => void,
  signal?: AbortSignal,
): Promise<TasteRouteResponse> {
  const response = await fetch(`${API_BASE_URL.replace(/\/$/, '')}/api/trip/plan/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(formData),
    signal,
  })
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: string | { message?: string } } | null
    const message = typeof payload?.detail === 'string' ? payload.detail : payload?.detail?.message
    throw new Error(message || 'Could not start itinerary generation.')
  }
  return consumeTripPlanStream(response, onProgress)
}

export async function searchTasteEntities(
  query: string,
  entityType?: string,
): Promise<TasteEntitySearchResponse> {
  try {
    const response = await apiClient.get<TasteEntitySearchResponse>('/api/taste/entities', {
      params: { q: query, type: entityType },
    })
    return response.data
  } catch (error: unknown) {
    throw new Error(getErrorMessage(error, 'Qloo search is temporarily unavailable.'))
  }
}

export default apiClient
