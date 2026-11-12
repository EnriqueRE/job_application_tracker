import { useQuery } from '@tanstack/vue-query'

import { api, type Schemas } from './client'

/** Backend health. A 503 still carries a HealthStatus body, so it is data, not an error. */
export async function fetchHealth(): Promise<Schemas['HealthStatus']> {
  const { data, error, response } = await api.GET('/api/health')
  const body = data ?? error
  if (!body) throw new Error(`Health check failed with HTTP ${response.status}`)
  return body
}

export function useHealth() {
  return useQuery({ queryKey: ['health'], queryFn: fetchHealth, refetchInterval: 60_000 })
}
