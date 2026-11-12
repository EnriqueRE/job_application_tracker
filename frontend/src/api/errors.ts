/** An API failure carrying the backend's `detail` message, ready to show to the user. */
export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

function toApiError(error: unknown, response: Response): ApiError {
  const detail = (error as { detail?: unknown } | undefined)?.detail
  if (typeof detail === 'string') return new ApiError(detail, response.status)
  if (Array.isArray(detail)) {
    // FastAPI validation errors: [{loc: [..., field], msg}, ...]
    const messages = detail.map((item: { loc?: unknown[]; msg?: string }) => {
      const field = item.loc?.at(-1)
      return field ? `${String(field)}: ${item.msg}` : (item.msg ?? 'invalid')
    })
    return new ApiError(messages.join('; '), response.status)
  }
  return new ApiError(`Request failed with HTTP ${response.status}`, response.status)
}

/** The data of an openapi-fetch call, or an ApiError when it failed. */
export async function unwrap<T>(
  call: Promise<{ data?: T; error?: unknown; response: Response }>,
): Promise<T> {
  const { data, error, response } = await call
  if (error !== undefined || data === undefined) throw toApiError(error, response)
  return data
}
