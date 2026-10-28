import { describe, expect, it } from 'vitest'

import apiClient from './api'

describe('api client', () => {
  it('uses the same-origin Vite proxy when no API base URL is configured', () => {
    expect(apiClient.defaults.baseURL).toBe('')
  })
})
