import axios from 'axios'
import type {
  TasteEntitySearchResponse,
  TasteRouteRequest,
  TasteRouteResponse,
} from '@/types/taste'
import { getErrorMessage } from '@/utils/errorMessage'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 1200000,
  headers: {
    'Content-Type': 'application/json'
  }
})

/**
 * 生成旅行计划
 */
export async function generateTripPlan(formData: TasteRouteRequest): Promise<TasteRouteResponse> {
  try {
    const response = await apiClient.post<TasteRouteResponse>('/api/trip/plan', formData)
    return response.data
  } catch (error: unknown) {
    throw new Error(getErrorMessage(error, '生成旅行计划失败'))
  }
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
    throw new Error(getErrorMessage(error, 'Qloo 搜索暂时不可用'))
  }
}

export default apiClient
