import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import { createMemoryHistory } from 'vue-router'

import App from './App.vue'
import { createAppRouter } from './router'

async function mountAt(path: string) {
  vi.stubGlobal(
    'fetch',
    vi.fn<typeof fetch>().mockResolvedValue(Response.json({ status: 'ok', database: 'ok' })),
  )
  const router = createAppRouter(createMemoryHistory())
  await router.push(path)
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const wrapper = mount(App, {
    global: { plugins: [router, [VueQueryPlugin, { queryClient }]] },
  })
  await flushPromises()
  return { wrapper, router }
}

describe('App layout', () => {
  it('opens on the Applications page', async () => {
    const { wrapper, router } = await mountAt('/')

    expect(router.currentRoute.value.path).toBe('/applications')
    expect(wrapper.find('h1').text()).toBe('Applications')
  })

  it('navigates between Applications and Organizations', async () => {
    const { wrapper, router } = await mountAt('/applications')

    const nav = wrapper.get('nav')
    expect(nav.findAll('a').map((a) => a.text())).toEqual(['Applications', 'Organizations'])

    await nav.findAll('a')[1]!.trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.path).toBe('/organizations')
    expect(wrapper.find('h1').text()).toBe('Organizations')
  })

  it('shows a not-found page for unknown paths', async () => {
    const { wrapper } = await mountAt('/nope')

    expect(wrapper.find('h1').text()).toBe('Page not found')
  })
})
