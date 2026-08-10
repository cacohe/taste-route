import dayjs from 'dayjs'
import { describe, expect, it } from 'vitest'
import { buildTripFormPayload, calculateTravelDays } from './tripForm'

describe('calculateTravelDays', () => {
  it('returns inclusive day count for valid ranges', () => {
    const start = dayjs('2025-06-01')
    const end = dayjs('2025-06-03')

    expect(calculateTravelDays(start, end)).toBe(3)
  })

  it('returns null when range exceeds 30 days', () => {
    const start = dayjs('2025-06-01')
    const end = dayjs('2025-07-10')

    expect(calculateTravelDays(start, end)).toBeNull()
  })

  it('returns null when end date is before start date', () => {
    const start = dayjs('2025-06-05')
    const end = dayjs('2025-06-01')

    expect(calculateTravelDays(start, end)).toBeNull()
  })
})

describe('buildTripFormPayload', () => {
  it('formats selected dates into API payload', () => {
    const payload = buildTripFormPayload({
      city: '北京',
      start_date: dayjs('2025-06-01'),
      end_date: dayjs('2025-06-03'),
      travel_days: 3,
      transportation: '公共交通',
      accommodation: '经济型酒店',
      preferences: ['美食'],
      free_text_input: '多安排博物馆',
    })

    expect(payload).toEqual({
      city: '北京',
      start_date: '2025-06-01',
      end_date: '2025-06-03',
      travel_days: 3,
      transportation: '公共交通',
      accommodation: '经济型酒店',
      preferences: ['美食'],
      free_text_input: '多安排博物馆',
    })
  })

  it('returns null when dates are missing', () => {
    const payload = buildTripFormPayload({
      city: '北京',
      start_date: null,
      end_date: null,
      travel_days: 1,
      transportation: '公共交通',
      accommodation: '经济型酒店',
      preferences: [],
      free_text_input: '',
    })

    expect(payload).toBeNull()
  })
})
