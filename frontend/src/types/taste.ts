export interface TasteEntity {
  id: string
  name: string
  entity_type: string
  description: string | null
  image_url: string | null
}

export interface TasteSeed {
  id: string | null
  name: string
  entity_type: string
}

export interface QlooContribution {
  entity_id: string
  name: string | null
  score: number | null
}

export interface PlaceCandidate {
  id: string
  name: string
  address: string | null
  description: string | null
  image_url: string | null
  latitude: number | null
  longitude: number | null
  affinity: number | null
  tags: string[]
  contributions: QlooContribution[]
}

export interface TasteRouteRequest {
  destination: string
  start_date: string
  end_date: string
  pace: 'relaxed' | 'balanced' | 'packed'
  budget: 'budget' | 'medium' | 'comfort'
  taste_seeds: TasteSeed[]
  constraints: string[]
  excluded_place_ids: string[]
}

export interface ItineraryItem {
  place_id: string
  start_time: string
  duration_minutes: number
  reason: string
}

export interface ItineraryDay {
  date: string
  items: ItineraryItem[]
}

export interface WorkflowStep {
  key: string
  label: string
  status: 'active' | 'completed' | 'repaired' | 'skipped' | 'failed'
}

export type PlanningAction = 'resolve_locality' | 'discover_strict' | 'discover_nearby'
  | 'compose_itinerary' | 'repair_itinerary' | 'build_routes' | 'finish' | 'fail'

export interface AgentDecision {
  iteration: number
  action: PlanningAction
  status: 'active' | 'completed' | 'repaired' | 'skipped' | 'failed'
  reason: string
  metrics: Record<string, number>
}

export interface ResolvedLocality { id: string; name: string }

export interface TravelLeg {
  from_place_id: string
  to_place_id: string
  distance_meters: number
  duration_minutes: number
}

export interface ItineraryRoute {
  date: string
  profile: 'driving'
  geometry: Array<[number, number]>
  legs: TravelLeg[]
  distance_meters: number
  duration_minutes: number
}

export interface TasteRoutePlan {
  request_id: string
  destination: string
  start_date: string
  end_date: string
  taste_profile: { tags: string[]; seeds: TasteSeed[] }
  candidates: PlaceCandidate[]
  days: ItineraryDay[]
  warnings: string[]
  trace: WorkflowStep[]
  completion_status: 'completed' | 'partial' | 'failed'
  locality: ResolvedLocality | null
  decisions: AgentDecision[]
  routes: ItineraryRoute[]
}

export interface TasteRouteResponse {
  success: boolean
  message: string
  data: TasteRoutePlan | null
  error_code: string | null
  retryable: boolean
}

export interface TasteEntitySearchResponse {
  items: TasteEntity[]
}
