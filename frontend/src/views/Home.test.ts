import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { generateTripPlanStream } from '@/services/api'
import Home from './Home.vue'

vi.mock('@/services/api', () => ({ generateTripPlanStream: vi.fn() }))

const TasteEntitySearchStub = {
  props: ['modelValue'],
  emits: ['update:modelValue'],
  template: '<button type="button" data-test="add-seed" @click="$emit(\'update:modelValue\', [{ id: \'movie-1\', name: \'Spirited Away\', entity_type: \'movie\' }])">Add seed</button>',
}

async function mountHome() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: Home },
      { path: '/result', component: { template: '<div>Result</div>' } },
    ],
  })
  await router.push('/')
  await router.isReady()
  const wrapper = mount(Home, {
    global: { plugins: [router], stubs: { TasteEntitySearch: TasteEntitySearchStub } },
  })
  await wrapper.get('input[placeholder="Tokyo / Lisbon"]').setValue('Tokyo')
  const dates = wrapper.findAll('input[type="date"]')
  await dates[0].setValue('2026-11-10')
  await dates[1].setValue('2026-11-11')
  await wrapper.get('[data-test="add-seed"]').trigger('click')
  return wrapper
}

describe('Home generation flow', () => {
  beforeEach(() => {
    vi.mocked(generateTripPlanStream).mockReset()
    sessionStorage.clear()
  })

  it('renders real streamed progress while generation is pending', async () => {
    vi.mocked(generateTripPlanStream).mockImplementation(async (_request, onProgress) => {
      onProgress({ key: 'taste_resolution', label: 'Resolve taste signals', status: 'completed' })
      onProgress({ key: 'qloo_discovery', label: 'Discover Qloo places', status: 'active' })
      return new Promise(() => {})
    })
    const wrapper = await mountHome()

    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(wrapper.get('[aria-label="TasteRoute generation progress"]').exists()).toBe(true)
    expect(wrapper.get('[data-step="qloo_discovery"]').attributes('data-status')).toBe('active')
    expect(wrapper.get('button[type="submit"]').attributes('disabled')).toBeDefined()
    wrapper.unmount()
  })

  it('restores a retry action after a streamed failure', async () => {
    vi.mocked(generateTripPlanStream).mockRejectedValue(new Error('Qloo is temporarily busy.'))
    const wrapper = await mountHome()

    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(wrapper.text()).toContain('Qloo is temporarily busy.')
    expect(wrapper.get('button[type="submit"]').text()).toContain('Try generation again')
    expect(wrapper.get('button[type="submit"]').attributes('disabled')).toBeUndefined()
  })
})
