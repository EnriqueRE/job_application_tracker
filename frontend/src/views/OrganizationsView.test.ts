import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { createMemoryHistory } from 'vue-router'

import App from '@/App.vue'
import { createAppRouter } from '@/router'
import { requestsMade, stubApi, type RouteHandler } from '@/test/fakeApi'
import { makeOrganization } from '@/test/organizations'

async function mountAt(path: string, routes: Record<string, RouteHandler>) {
  const fetchMock = stubApi(routes)
  const router = createAppRouter(createMemoryHistory())
  await router.push(path)
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const wrapper = mount(App, {
    global: { plugins: [router, [VueQueryPlugin, { queryClient }]] },
    attachTo: document.body,
  })
  await flushPromises()
  return { wrapper, router, fetchMock }
}

function rowTexts(wrapper: Awaited<ReturnType<typeof mountAt>>['wrapper']) {
  return wrapper.findAll('tbody tr').map((row) => row.findAll('td').map((cell) => cell.text()))
}

describe('Organizations list', () => {
  it('shows each Organization with its type, industry, location and priority', async () => {
    const { wrapper } = await mountAt('/organizations', {
      'GET /api/organizations': () =>
        Response.json([
          makeOrganization({ name: 'Acme', industry: 'Retail', location: 'Madrid', priority: 5 }),
          makeOrganization({ name: 'Hays', organization_type: 'recruiting_firm' }),
        ]),
    })

    expect(rowTexts(wrapper).map((cells) => cells.slice(0, 5))).toEqual([
      ['Acme', 'Company', 'Retail', 'Madrid', '5'],
      ['Hays', 'Recruiting firm', '', '', '3'],
    ])
  })

  it('searches by name', async () => {
    const { wrapper, fetchMock } = await mountAt('/organizations', {
      'GET /api/organizations': (_request, url) =>
        Response.json(
          url.searchParams.get('q') === 'glob'
            ? [makeOrganization({ name: 'Globex' })]
            : [makeOrganization({ name: 'Acme' }), makeOrganization({ name: 'Globex' })],
        ),
    })

    await wrapper.get('input[type="search"]').setValue('glob')
    await flushPromises()

    expect(requestsMade(fetchMock)).toContain('GET /api/organizations?q=glob')
    expect(rowTexts(wrapper).map((cells) => cells[0])).toEqual(['Globex'])
  })

  it('archives an Organization and drops it from the list', async () => {
    let archived = false
    const acme = makeOrganization({ name: 'Acme' })
    const { wrapper, fetchMock } = await mountAt('/organizations', {
      'GET /api/organizations': () => Response.json(archived ? [] : [acme]),
      'POST /api/organizations/:id/archive': () => {
        archived = true
        return Response.json({ ...acme, archived_at: '2026-11-12T10:00:00Z' })
      },
    })

    await wrapper.get('tbody tr').get('button').trigger('click')
    await flushPromises()

    expect(requestsMade(fetchMock)).toContain(`POST /api/organizations/${acme.id}/archive`)
    expect(wrapper.findAll('tbody tr')).toHaveLength(0)
  })

  it('explains why archiving is blocked when the Organization has active Applications', async () => {
    const { wrapper } = await mountAt('/organizations', {
      'GET /api/organizations': () => Response.json([makeOrganization({ name: 'Acme' })]),
      'POST /api/organizations/:id/archive': () =>
        Response.json(
          {
            detail:
              'Acme has 2 active Applications; archive them before archiving the Organization',
          },
          { status: 409 },
        ),
    })

    await wrapper.get('tbody tr').get('button').trigger('click')
    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toContain(
      'Acme has 2 active Applications; archive them before archiving the Organization',
    )
    expect(rowTexts(wrapper).map((cells) => cells[0])).toEqual(['Acme'])
  })

  it('shows archived Organizations on request and restores them', async () => {
    const globex = makeOrganization({ name: 'Globex', archived_at: '2026-11-01T10:00:00Z' })
    const { wrapper, fetchMock } = await mountAt('/organizations', {
      'GET /api/organizations': (_request, url) =>
        Response.json(url.searchParams.get('include_archived') === 'true' ? [globex] : []),
      'POST /api/organizations/:id/restore': () => Response.json({ ...globex, archived_at: null }),
    })

    await wrapper.get('input[type="checkbox"]').setValue(true)
    await flushPromises()

    expect(requestsMade(fetchMock)).toContain('GET /api/organizations?include_archived=true')
    const row = wrapper.get('tbody tr')
    expect(row.text()).toContain('Archived')

    await row.get('button').trigger('click')
    await flushPromises()

    expect(requestsMade(fetchMock)).toContain(`POST /api/organizations/${globex.id}/restore`)
  })

  it('links to the create and edit forms', async () => {
    const acme = makeOrganization({ name: 'Acme' })
    const { wrapper } = await mountAt('/organizations', {
      'GET /api/organizations': () => Response.json([acme]),
    })

    expect(wrapper.get('a[href="/organizations/new"]').text()).toContain('New Organization')
    expect(wrapper.get('tbody tr a').attributes('href')).toBe(`/organizations/${acme.id}`)
  })
})
