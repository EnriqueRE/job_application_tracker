import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

import ApiStatus from './ApiStatus.vue'

function mountWithBackend(response: Response) {
  const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(response)
  vi.stubGlobal('fetch', fetchMock)
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const wrapper = mount(ApiStatus, {
    global: { plugins: [[VueQueryPlugin, { queryClient }]] },
  })
  return { wrapper, fetchMock }
}

function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('ApiStatus', () => {
  it('asks the backend health endpoint and reports it is online', async () => {
    const { wrapper, fetchMock } = mountWithBackend(json(200, { status: 'ok', database: 'ok' }))
    await flushPromises()

    const request = fetchMock.mock.calls[0]![0] as Request
    expect(new URL(request.url).pathname).toBe('/api/health')
    expect(wrapper.text()).toContain('Backend online')
  })

  it('reports when the database is unreachable', async () => {
    const { wrapper } = mountWithBackend(json(503, { status: 'error', database: 'unreachable' }))
    await flushPromises()

    expect(wrapper.text()).toContain('Backend offline')
  })
})
