import type { TasteRoutePlan } from '@/types/taste'

type TasteRouteDraft = {
  destination: string
  startDate: string
  endDate: string
  tasteSeedCount: number
}

export function validateTasteRouteDraft(draft: TasteRouteDraft): string | null {
  if (!draft.destination || !draft.startDate || !draft.endDate) {
    return 'Enter a destination and travel dates.'
  }
  const start = Date.parse(`${draft.startDate}T00:00:00Z`)
  const end = Date.parse(`${draft.endDate}T00:00:00Z`)
  if (!Number.isFinite(start) || !Number.isFinite(end) || end < start) {
    return 'The end date cannot be before the start date.'
  }
  if ((end - start) / 86_400_000 >= 30) {
    return 'Trips cannot exceed 30 days.'
  }
  if (draft.tasteSeedCount < 1) {
    return 'Select at least one taste signal.'
  }
  return null
}

export function parseStoredTasteRoutePlan(raw: string | null): TasteRoutePlan | null {
  if (!raw) return null
  try {
    const value: unknown = JSON.parse(raw)
    if (!isRecord(value)) return null
    if (
      !isString(value.request_id)
      || !isString(value.destination)
      || !isString(value.start_date)
      || !isString(value.end_date)
      || !isRecord(value.taste_profile)
      || !isStringArray(value.taste_profile.tags)
      || !isCandidateArray(value.candidates)
      || !isDayArray(value.days)
      || !isStringArray(value.warnings)
      || !['completed', 'partial', 'failed'].includes(String(value.completion_status))
      || !isLocality(value.locality)
      || !isDecisionArray(value.decisions)
      || !isRouteArray(value.routes)
    ) return null
    return value as unknown as TasteRoutePlan
  } catch {
    return null
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isString(value: unknown): value is string {
  return typeof value === 'string' && value.length > 0
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === 'string')
}

function isNullableString(value: unknown): boolean {
  return value === null || typeof value === 'string'
}

function isNullableNumber(value: unknown): boolean {
  return value === null || (typeof value === 'number' && Number.isFinite(value))
}

function isCandidateArray(value: unknown): boolean {
  return Array.isArray(value) && value.every((candidate) => {
    if (!isRecord(candidate)) return false
    return isString(candidate.id)
      && isString(candidate.name)
      && isNullableString(candidate.address)
      && isNullableString(candidate.description)
      && isNullableString(candidate.image_url)
      && isNullableNumber(candidate.latitude)
      && isNullableNumber(candidate.longitude)
      && isNullableNumber(candidate.affinity)
      && isStringArray(candidate.tags)
      && Array.isArray(candidate.contributions)
      && candidate.contributions.every((signal) => (
        isRecord(signal)
        && isString(signal.entity_id)
        && isNullableString(signal.name)
        && isNullableNumber(signal.score)
      ))
  })
}

function isDayArray(value: unknown): boolean {
  return Array.isArray(value) && value.every((day) => {
    if (!isRecord(day) || !isString(day.date) || !Array.isArray(day.items)) return false
    return day.items.every((item) => (
      isRecord(item)
      && isString(item.place_id)
      && isString(item.start_time)
      && typeof item.duration_minutes === 'number'
      && Number.isFinite(item.duration_minutes)
      && isString(item.reason)
    ))
  })
}

const actions = new Set([
  'resolve_locality', 'discover_strict', 'discover_nearby', 'compose_itinerary',
  'repair_itinerary', 'build_routes', 'finish', 'fail',
])
const statuses = new Set(['active', 'completed', 'repaired', 'skipped', 'failed'])

function isLocality(value: unknown): boolean {
  return value === null || (isRecord(value) && isString(value.id) && isString(value.name))
}

function isDecisionArray(value: unknown): boolean {
  return Array.isArray(value) && value.every((decision) => (
    isRecord(decision)
    && Number.isInteger(decision.iteration) && Number(decision.iteration) > 0
    && typeof decision.action === 'string' && actions.has(decision.action)
    && typeof decision.status === 'string' && statuses.has(decision.status)
    && isString(decision.reason)
    && isRecord(decision.metrics)
    && Object.values(decision.metrics).every((metric) => typeof metric === 'number' && Number.isFinite(metric))
  ))
}

function isRouteArray(value: unknown): boolean {
  return Array.isArray(value) && value.every((route) => (
    isRecord(route) && isString(route.date) && route.profile === 'driving'
    && Array.isArray(route.geometry)
    && route.geometry.every((point) => Array.isArray(point) && point.length === 2 && point.every((coordinate) => typeof coordinate === 'number' && Number.isFinite(coordinate)))
    && Array.isArray(route.legs) && route.legs.every((leg) => (
      isRecord(leg) && isString(leg.from_place_id) && isString(leg.to_place_id)
      && isNonNegativeNumber(leg.distance_meters) && isNonNegativeNumber(leg.duration_minutes)
    ))
    && isNonNegativeNumber(route.distance_meters) && isNonNegativeNumber(route.duration_minutes)
  ))
}

function isNonNegativeNumber(value: unknown): boolean {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0
}
