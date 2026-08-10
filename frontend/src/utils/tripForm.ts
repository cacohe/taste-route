import type { Dayjs } from 'dayjs'
import type { TripFormData } from '@/types'

export interface TripFormState {
  city: string
  start_date: Dayjs | null
  end_date: Dayjs | null
  travel_days: number
  transportation: string
  accommodation: string
  preferences: string[]
  free_text_input: string
}

export function calculateTravelDays(start: Dayjs, end: Dayjs): number | null {
  const days = end.diff(start, 'day') + 1
  if (days > 0 && days <= 30) {
    return days
  }
  return null
}

export function buildTripFormPayload(form: TripFormState): TripFormData | null {
  if (!form.start_date || !form.end_date) {
    return null
  }

  return {
    city: form.city,
    start_date: form.start_date.format('YYYY-MM-DD'),
    end_date: form.end_date.format('YYYY-MM-DD'),
    travel_days: form.travel_days,
    transportation: form.transportation,
    accommodation: form.accommodation,
    preferences: form.preferences,
    free_text_input: form.free_text_input,
  }
}
