import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import TasteExplanation from './TasteExplanation.vue'

const candidate = {
  id: 'museum',
  name: 'Museum of the Moving Image',
  address: 'Astoria',
  description: null,
  image_url: null,
  latitude: 40.75,
  longitude: -73.92,
  affinity: 0.84,
  tags: ['Film culture'],
  contributions: [{ entity_id: 'movie-1', name: 'Blade Runner', score: 0.77 }],
}

describe('TasteExplanation', () => {
  it('renders only the evidence bound to the matching Qloo candidate', () => {
    const wrapper = mount(TasteExplanation, {
      props: {
        item: {
          place_id: 'museum',
          start_time: '10:00',
          duration_minutes: 120,
          reason: 'Matches the selected film culture.',
        },
        candidate,
      },
    })

    expect(wrapper.text()).toContain('Blade Runner')
    expect(wrapper.text()).toContain('84%')
    expect(wrapper.text()).toContain('Matches the selected film culture.')
  })

  it('shows an honest unavailable state without inventing evidence', () => {
    const wrapper = mount(TasteExplanation, {
      props: {
        item: {
          place_id: 'missing',
          start_time: '10:00',
          duration_minutes: 60,
          reason: 'Generated reason',
        },
        candidate: null,
      },
    })

    expect(wrapper.text()).toContain('Qloo 依据不可用')
    expect(wrapper.text()).not.toContain('%')
  })
})
