import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import TasteEntitySearch from './TasteEntitySearch.vue'
import { searchTasteEntities } from '@/services/api'

vi.mock('@/services/api', () => ({
  searchTasteEntities: vi.fn(),
}))

const bladeRunner = {
  id: 'movie-1',
  name: 'Blade Runner',
  entity_type: 'movie',
  description: '1982 film',
  image_url: null,
}

describe('TasteEntitySearch', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.mocked(searchTasteEntities).mockReset()
  })

  it('debounces requests and ignores a stale response', async () => {
    let resolveFirst!: (value: { items: typeof bladeRunner[] }) => void
    vi.mocked(searchTasteEntities)
      .mockImplementationOnce(
        () => new Promise((resolve) => { resolveFirst = resolve }),
      )
      .mockResolvedValueOnce({ items: [{ ...bladeRunner, id: 'movie-2', name: 'Arrival' }] })
    const wrapper = mount(TasteEntitySearch, { props: { modelValue: [] } })

    await wrapper.get('[data-test="taste-query"]').setValue('Blade')
    await vi.advanceTimersByTimeAsync(300)
    await wrapper.get('[data-test="taste-query"]').setValue('Arrival')
    await vi.advanceTimersByTimeAsync(300)

    expect(wrapper.text()).toContain('Arrival')
    resolveFirst({ items: [bladeRunner] })
    await Promise.resolve()
    expect(wrapper.text()).not.toContain('Blade Runner')
  })

  it('deduplicates selected entities', async () => {
    vi.mocked(searchTasteEntities).mockResolvedValue({ items: [bladeRunner] })
    const wrapper = mount(TasteEntitySearch, {
      props: {
        modelValue: [{ id: 'movie-1', name: 'Blade Runner', entity_type: 'movie' }],
      },
    })
    await wrapper.get('[data-test="taste-query"]').setValue('Blade')
    await vi.advanceTimersByTimeAsync(300)
    await wrapper.get('[data-test="result-movie-1"]').trigger('click')

    expect(wrapper.emitted('update:modelValue')).toBeUndefined()
  })

  it('removes a selected seed', async () => {
    const wrapper = mount(TasteEntitySearch, {
      props: {
        modelValue: [{ id: 'movie-1', name: 'Blade Runner', entity_type: 'movie' }],
      },
    })
    await wrapper.get('[data-test="remove-movie-1"]').trigger('click')

    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual([[]])
  })
})
