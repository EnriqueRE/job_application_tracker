import createClient from 'openapi-fetch'

import type { components, paths } from './schema'

/**
 * Typed client for the backend API, generated from its OpenAPI schema
 * (`npm run gen:api` refreshes `schema.d.ts`). Paths include the `/api` prefix.
 *
 *   const { data, error, response } = await api.GET('/api/health')
 */
export const api = createClient<paths>({
  baseUrl: globalThis.location?.origin ?? '',
  // Look up fetch per call so tests can stub it after this module loads.
  fetch: (request) => globalThis.fetch(request),
})

export type Schemas = components['schemas']
