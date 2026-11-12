import { vi } from 'vitest'

/** A route handler gets the request, its URL and the `:param` values from the route key. */
export type RouteHandler = (
  request: Request,
  url: URL,
  params: Record<string, string>,
) => Response | Promise<Response>

/**
 * Stub `fetch` with a tiny fake backend for component tests. Routes are keyed
 * `'METHOD /path/:param'`; unknown routes answer 404. `/api/health` answers ok
 * unless overridden. Returns the fetch mock so tests can inspect requests.
 */
export function stubApi(routes: Record<string, RouteHandler>) {
  const table = Object.entries({ 'GET /api/health': healthy, ...routes }).map(([key, handler]) => {
    const [method, path] = key.split(' ') as [string, string]
    const names: string[] = []
    const pattern = path.replace(/:(\w+)/g, (_, name: string) => {
      names.push(name)
      return '([^/]+)'
    })
    return { method, regex: new RegExp(`^${pattern}$`), names, handler }
  })

  const fetchMock = vi.fn<typeof fetch>(async (input) => {
    const request = input as Request
    const url = new URL(request.url)
    for (const route of table) {
      const match = route.method === request.method && route.regex.exec(url.pathname)
      if (match) {
        const params = Object.fromEntries(route.names.map((name, i) => [name, match[i + 1]!]))
        return route.handler(request, url, params)
      }
    }
    return Response.json({ detail: 'Not Found' }, { status: 404 })
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

const healthy: RouteHandler = () => Response.json({ status: 'ok', database: 'ok' })

/** The requests the mock received, as `'METHOD /path?query'` strings. */
export function requestsMade(fetchMock: ReturnType<typeof stubApi>): string[] {
  return fetchMock.mock.calls.map(([input]) => {
    const request = input as Request
    const url = new URL(request.url)
    return `${request.method} ${url.pathname}${url.search}`
  })
}
