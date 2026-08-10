import { describe, expect, it } from 'vitest'
import { getErrorMessage } from './errorMessage'

describe('getErrorMessage', () => {
  it('prefers API detail from axios-style errors', () => {
    const message = getErrorMessage(
      { response: { data: { detail: '城市不能为空' } }, message: 'Request failed' },
      'fallback'
    )

    expect(message).toBe('城市不能为空')
  })

  it('falls back to error.message', () => {
    expect(getErrorMessage({ message: 'Network Error' }, 'fallback')).toBe('Network Error')
  })

  it('uses provided fallback for unknown errors', () => {
    expect(getErrorMessage(null, '生成旅行计划失败')).toBe('生成旅行计划失败')
  })
})
