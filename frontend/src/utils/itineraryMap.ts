import type { PlaceCandidate, TasteRoutePlan } from '@/types/taste'

const DAY_COLORS = ['#6342ad', '#d26945', '#25846f', '#b07b19']

export interface ItineraryMapMarker {
  id: string
  placeId: string
  name: string
  label: string
  color: string
  coordinates: [number, number]
  kind: 'itinerary' | 'candidate'
}

export interface ItineraryMapRoute {
  date: string
  color: string
  coordinates: Array<[number, number]>
}

export interface ItineraryMapModel {
  markers: ItineraryMapMarker[]
  routes: ItineraryMapRoute[]
}

function coordinates(candidate: PlaceCandidate | undefined): [number, number] | null {
  if (candidate?.longitude === null || candidate?.latitude === null || !candidate) return null
  return [candidate.longitude, candidate.latitude]
}

export function buildItineraryMapModel(plan: TasteRoutePlan): ItineraryMapModel {
  const candidates = new Map(plan.candidates.map((candidate) => [candidate.id, candidate]))

  if (!plan.days.length) {
    const markers = plan.candidates.flatMap((candidate, index): ItineraryMapMarker[] => {
      const point = coordinates(candidate)
      return point ? [{
        id: `candidate-${candidate.id}`,
        placeId: candidate.id,
        name: candidate.name,
        label: String(index + 1),
        color: '#71647f',
        coordinates: point,
        kind: 'candidate',
      }] : []
    })
    return { markers, routes: [] }
  }

  const markers: ItineraryMapMarker[] = []
  const routes: ItineraryMapRoute[] = []
  plan.days.forEach((day, dayIndex) => {
    const color = DAY_COLORS[dayIndex % DAY_COLORS.length]
    const routeCoordinates: Array<[number, number]> = []
    day.items.forEach((item, stopIndex) => {
      const candidate = candidates.get(item.place_id)
      const point = coordinates(candidate)
      if (!candidate || !point) return
      routeCoordinates.push(point)
      markers.push({
        id: `${day.date}-${stopIndex}-${item.place_id}`,
        placeId: item.place_id,
        name: candidate.name,
        label: `D${dayIndex + 1}-${stopIndex + 1}`,
        color,
        coordinates: point,
        kind: 'itinerary',
      })
    })
    if (routeCoordinates.length > 1) routes.push({ date: day.date, color, coordinates: routeCoordinates })
  })
  return { markers, routes }
}
