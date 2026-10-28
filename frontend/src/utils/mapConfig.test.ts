import { describe, expect, it } from 'vitest'
import { getMapStyleUrl } from './mapConfig'

describe('getMapStyleUrl', () => {
  it('defaults to a full production street basemap', () => {
    expect(getMapStyleUrl()).toBe('https://tiles.openfreemap.org/styles/liberty')
  })
})
