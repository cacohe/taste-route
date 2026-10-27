export function getErrorMessage(error: unknown, fallback: string): string {
  if (typeof error === 'object' && error !== null) {
    const response = (error as {
      response?: { data?: { detail?: string | { message?: unknown } } }
    }).response
    const detail = response?.data?.detail
    if (typeof detail === 'string' && detail) {
      return detail
    }
    if (
      typeof detail === 'object'
      && detail !== null
      && typeof detail.message === 'string'
      && detail.message
    ) return detail.message

    const message = (error as { message?: string }).message
    if (message) {
      return message
    }
  }

  return fallback
}
