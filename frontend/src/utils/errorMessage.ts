export function getErrorMessage(error: unknown, fallback: string): string {
  if (typeof error === 'object' && error !== null) {
    const response = (error as { response?: { data?: { detail?: string } } }).response
    const detail = response?.data?.detail
    if (detail) {
      return detail
    }

    const message = (error as { message?: string }).message
    if (message) {
      return message
    }
  }

  return fallback
}
