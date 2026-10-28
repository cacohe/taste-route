const DEMO_STYLE = 'https://demotiles.maplibre.org/style.json'

export function getMapStyleUrl(): string {
  return import.meta.env.VITE_MAP_STYLE_URL?.trim() || DEMO_STYLE
}
