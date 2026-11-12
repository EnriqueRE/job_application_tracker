import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { createMemoryHistory } from 'vue-router'

import App from '@/App.vue'
import { createAppRouter } from '@/router'
import { stubApi, type RouteHandler } from '@/test/fakeApi'
import { makeOrganization } from '@/test/organizations'

async function mountAt(path: string, routes: Record<string, RouteHandler>) {
  stubApi({ 'GET /api/organizations': () => Response.json([]), ...routes })
  const router = createAppRouter(createMemoryHistory())
  await router.push(path)
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const wrapper = mount(App, {
    global: { plugins: [router, [VueQueryPlugin, { queryClient }]] },
  })
  await flushPromises()
  return { wrapper, router }
}

describe('Organization create and edit pages', () => {
  it('creates an Organization and returns to the list', async () => {
    const { wrapper, router } = await mountAt('/organizations/new', {
      'POST /api/organizations': () =>
        Response.json(makeOrganization({ name: 'Globex' }), { status: 201 }),
    })

    expect(wrapper.get('h1').text()).toBe('New Organization')
    await wrapper.get('input[name="name"]').setValue('Globex')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(router.currentRoute.value.path).toBe('/organizations')
  })

  it('edits an existing Organization and returns to the list', async () => {
    const acme = makeOrganization({ name: 'Acme', notes: 'Old notes' })
    const { wrapper, router } = await mountAt(`/organizations/${acme.id}`, {
      'GET /api/organizations/:id': () => Response.json(acme),
      'PATCH /api/organizations/:id': () => Response.json({ ...acme, notes: 'New notes' }),
    })

    expect(wrapper.get('h1').text()).toBe('Edit Acme')
    expect((wrapper.get('textarea[name="notes"]').element as HTMLTextAreaElement).value).toBe(
      'Old notes',
    )
    await wrapper.get('textarea[name="notes"]').setValue('New notes')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(router.currentRoute.value.path).toBe('/organizations')
  })

  it('says so when the Organization does not exist', async () => {
    const { wrapper } = await mountAt('/organizations/999', {
      'GET /api/organizations/:id': () =>
        Response.json({ detail: 'Organization 999 was not found' }, { status: 404 }),
    })

    expect(wrapper.get('[role="alert"]').text()).toContain('Organization 999 was not found')
  })
})
