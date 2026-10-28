import { describe, expect, it } from 'vitest'
import { getMapStyleUrl } from './mapConfig'

describe('getMapStyleUrl', () => {
  it('always returns a usable style URL', () => {
    expect(getMapStyleUrl()).toMatch(/^https?:\/\//)
  })
})
