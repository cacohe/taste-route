import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import GenerationProgress from './GenerationProgress.vue'

describe('GenerationProgress', () => {
  it('shows real decisions in arrival order including retries without a fake percentage', () => {
    const wrapper = mount(GenerationProgress, {
      props: {
        events: [
          { iteration: 1, action: 'resolve_locality', status: 'completed', reason: 'Resolved Shanghai.', metrics: {} },
          { iteration: 2, action: 'discover_strict', status: 'failed', reason: 'No strict candidates.', metrics: { candidate_count: 0 } },
          { iteration: 3, action: 'discover_nearby', status: 'completed', reason: 'Expanded once.', metrics: { candidate_count: 4 } },
        ],
        elapsedSeconds: 12,
      },
    })

    expect(wrapper.findAll('li').map((item) => item.attributes('data-action'))).toEqual([
      'resolve_locality', 'discover_strict', 'discover_nearby',
    ])
    expect(wrapper.text()).toContain('Resolved Shanghai.')
    expect(wrapper.text()).toContain('Expanded once.')
    expect(wrapper.text()).toContain('12 seconds')
    expect(wrapper.text()).not.toMatch(/\d+%/)
    expect(wrapper.get('[role="progressbar"]').attributes('aria-valuenow')).toBeUndefined()
  })
})
