import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import GenerationProgress from './GenerationProgress.vue'

describe('GenerationProgress', () => {
  it('shows completed, active, and pending workflow stages without a fake percentage', () => {
    const wrapper = mount(GenerationProgress, {
      props: {
        events: [
          { key: 'taste_resolution', label: 'Resolve taste signals', status: 'completed' },
          { key: 'qloo_discovery', label: 'Discover Qloo places', status: 'active' },
        ],
        elapsedSeconds: 12,
      },
    })

    expect(wrapper.get('[data-step="taste_resolution"]').attributes('data-status')).toBe('completed')
    expect(wrapper.get('[data-step="qloo_discovery"]').attributes('data-status')).toBe('active')
    expect(wrapper.get('[data-step="itinerary_composition"]').attributes('data-status')).toBe('pending')
    expect(wrapper.text()).toContain('12 seconds')
    expect(wrapper.text()).not.toMatch(/\d+%/)
    expect(wrapper.get('[role="progressbar"]').attributes('aria-valuenow')).toBeUndefined()
  })
})
