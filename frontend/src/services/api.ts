import axios from 'axios'
import type { TripFormData, TripPlanResponse, AttractionPhotoResponse } from '@/types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 1200000,
  headers: {
    'Content-Type': 'application/json'
  }
})

apiClient.interceptors.request.use(
  (config) => {
    console.log('发送请求:', config.method?.toUpperCase(), config.url)
    return config
  },
  (error) => {
    console.error('请求错误:', error)
    return Promise.reject(error)
  }
)

apiClient.interceptors.response.use(
  (response) => {
    console.log('收到响应:', response.status, response.config.url)
    return response
  },
  (error) => {
    console.error('响应错误:', error.response?.status, error.message)
    return Promise.reject(error)
  }
)

function getErrorMessage(error: any, fallback: string): string {
  return error.response?.data?.detail || error.message || fallback
}

/**
 * 生成旅行计划
 */
export async function generateTripPlan(formData: TripFormData): Promise<TripPlanResponse> {
  try {
    const response = await apiClient.post<TripPlanResponse>('/api/trip/plan', formData)
    return response.data
  } catch (error: any) {
    console.error('生成旅行计划失败:', error)
    throw new Error(getErrorMessage(error, '生成旅行计划失败'))
  }
}

/**
 * 获取景点图片（Unsplash，不走 MCP）
 */
export async function getAttractionPhoto(name: string): Promise<AttractionPhotoResponse> {
  try {
    const response = await apiClient.get<AttractionPhotoResponse>('/api/poi/photo', {
      params: { name }
    })
    return response.data
  } catch (error: any) {
    console.error('获取景点图片失败:', error)
    throw new Error(getErrorMessage(error, '获取景点图片失败'))
  }
}

export default apiClient
