const DEFAULT_STYLE = 'https://tiles.openfreemap.org/styles/liberty'

export function getMapStyleUrl(): string {
  return import.meta.env.VITE_MAP_STYLE_URL?.trim() || DEFAULT_STYLE
}
