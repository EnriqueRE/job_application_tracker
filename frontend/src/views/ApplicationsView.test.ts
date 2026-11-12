import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory } from 'vue-router'

import type { Schemas } from '@/api/client'
import App from '@/App.vue'
import { createAppRouter } from '@/router'
import { makeApplication } from '@/test/applications'
import { requestsMade, stubApi, type RouteHandler } from '@/test/fakeApi'

type Application = Schemas['ApplicationRead']
type ApplicationStatus = Schemas['ApplicationStatus']

const STATUSES: ApplicationStatus[] = [
  'saved',
  'applied',
  'screening',
  'interview',
  'technical_interview',
  'final_interview',
  'offer',
  'rejected',
  'withdrawn',
  'closed',
  'no_response',
]

function counts(nonZero: Partial<Record<ApplicationStatus, number>> = {}) {
  return STATUSES.map((status) => ({ status, count: nonZero[status] ?? 0 }))
}

interface FakeBackend {
  applications?: Application[] | RouteHandler
  due?: Application[]
  counts?: Schemas['StatusCount'][]
}

async function mountAt(path: string, backend: FakeBackend = {}) {
  const list = backend.applications ?? []
  const fetchMock = stubApi({
    'GET /api/applications': Array.isArray(list) ? () => Response.json(list) : list,
    'GET /api/applications/due': () => Response.json(backend.due ?? []),
    'GET /api/applications/status-counts': () => Response.json(backend.counts ?? counts()),
  })
  const router = createAppRouter(createMemoryHistory())
  await router.push(path)
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const wrapper = mount(App, {
    global: { plugins: [router, [VueQueryPlugin, { queryClient }]] },
  })
  await flushPromises()
  return { wrapper, router, fetchMock }
}

describe('Applications list', () => {
  it('shows each Application as a row linking to its detail screen', async () => {
    const { wrapper } = await mountAt('/applications', {
      applications: [
        makeApplication({
          id: 7,
          organization: { id: 3, name: 'Globex', organization_type: 'company' },
          role: 'Staff Engineer',
          current_status: 'technical_interview',
          applied_at: '2026-10-02',
          next_action_at: '2026-11-20',
        }),
      ],
    })

    const table = wrapper.get('table')
    expect(table.findAll('thead th').map((th) => th.text())).toEqual([
      'Organization',
      'Role',
      'Pipeline Status',
      'Applied',
      'Next action',
    ])
    const cells = table
      .findAll('tbody tr')[0]!
      .findAll('td')
      .map((td) => td.text())
    expect(cells).toEqual([
      'Globex',
      'Staff Engineer',
      'Technical interview',
      '2026-10-02',
      '2026-11-20',
    ])
    expect(table.get('tbody tr a').attributes('href')).toBe('/applications/7')
  })

  describe('filters', () => {
    const listRequests = (fetchMock: Awaited<ReturnType<typeof mountAt>>['fetchMock']) =>
      requestsMade(fetchMock).filter((request) => request.startsWith('GET /api/applications?'))

    it('loads the filters from the URL and asks the API for them', async () => {
      const { wrapper, fetchMock } = await mountAt(
        '/applications?organization=glob&role=eng&status=offer&status=applied&archived=true',
      )

      expect(listRequests(fetchMock).at(-1)).toBe(
        'GET /api/applications?organization=glob&role=eng&status=offer&status=applied&include_archived=true',
      )
      expect(wrapper.get<HTMLInputElement>('input[name="organization"]').element.value).toBe('glob')
      expect(wrapper.get<HTMLInputElement>('input[name="role"]').element.value).toBe('eng')
      expect(wrapper.get<HTMLInputElement>('input[name="archived"]').element.checked).toBe(true)
    })

    it('puts typed text filters in the URL and refetches', async () => {
      const { wrapper, router, fetchMock } = await mountAt('/applications')

      await wrapper.get('input[name="role"]').setValue('staff')
      await flushPromises()

      expect(router.currentRoute.value.query).toMatchObject({ role: 'staff' })
      expect(listRequests(fetchMock).at(-1)).toBe('GET /api/applications?role=staff')
    })

    it('shows archived Applications only when asked, marking them', async () => {
      const archived = makeApplication({ role: 'Old', archived_at: '2026-10-30T09:00:00Z' })
      const { wrapper, router, fetchMock } = await mountAt('/applications', {
        applications: (_request, url) =>
          Response.json(url.searchParams.get('include_archived') === 'true' ? [archived] : []),
      })
      expect(wrapper.get('tbody').text()).toContain('No Applications match')

      await wrapper.get('input[name="archived"]').setValue(true)
      await flushPromises()

      expect(router.currentRoute.value.query).toMatchObject({ archived: 'true' })
      expect(listRequests(fetchMock).at(-1)).toBe('GET /api/applications?include_archived=true')
      expect(wrapper.get('tbody tr').text()).toContain('Archived')
    })
  })

  it('links to the form for a new Application', async () => {
    const { wrapper } = await mountAt('/applications')

    const link = wrapper.findAll('a').find((a) => a.text() === 'New Application')
    expect(link?.attributes('href')).toBe('/applications/new')
  })

  it('says so when no Application matches', async () => {
    const { wrapper } = await mountAt('/applications?role=nothing')

    expect(wrapper.get('tbody').text()).toContain('No Applications match these filters.')
  })

  it('follows back and forward through filter changes', async () => {
    const { wrapper, router } = await mountAt('/applications')

    await wrapper.get('input[name="archived"]').setValue(true)
    await flushPromises()
    router.back()
    await flushPromises()

    expect(router.currentRoute.value.query.archived).toBeUndefined()
    expect(wrapper.get<HTMLInputElement>('input[name="archived"]').element.checked).toBe(false)

    router.forward()
    await flushPromises()

    expect(wrapper.get<HTMLInputElement>('input[name="archived"]').element.checked).toBe(true)
  })

  describe('Due soon', () => {
    afterEach(() => {
      vi.useRealTimers()
    })

    it('lists upcoming and overdue next actions, marking the overdue ones', async () => {
      vi.useFakeTimers({ toFake: ['Date'] })
      vi.setSystemTime(new Date(2026, 10, 12, 9, 0))
      const { wrapper } = await mountAt('/applications', {
        due: [
          makeApplication({
            id: 4,
            organization: { id: 1, name: 'Initech', organization_type: 'company' },
            role: 'Platform Engineer',
            next_action_at: '2026-11-10',
          }),
          makeApplication({
            id: 5,
            organization: { id: 2, name: 'Hooli', organization_type: 'company' },
            role: 'SRE',
            next_action_at: '2026-11-12',
          }),
        ],
      })

      const items = wrapper.get('[aria-label="Due soon"]').findAll('li')
      expect(items).toHaveLength(2)
      expect(items[0]!.text()).toContain('Initech')
      expect(items[0]!.text()).toContain('Platform Engineer')
      expect(items[0]!.text()).toContain('Overdue')
      expect(items[0]!.get('a').attributes('href')).toBe('/applications/4')
      expect(items[1]!.text()).toContain('Hooli')
      expect(items[1]!.text()).toContain('Today')
      expect(items[1]!.text()).not.toContain('Overdue')
    })

    it('stays out of the way when nothing is due', async () => {
      const { wrapper } = await mountAt('/applications', { due: [] })

      expect(wrapper.find('[aria-label="Due soon"]').exists()).toBe(false)
    })
  })

  describe('Pipeline Status counts', () => {
    const countButtons = (wrapper: Awaited<ReturnType<typeof mountAt>>['wrapper']) =>
      wrapper.get('[aria-label="Pipeline Status counts"]').findAll('button')

    it('shows how many Applications are in each Pipeline Status', async () => {
      const { wrapper } = await mountAt('/applications', {
        counts: counts({ applied: 4, offer: 1 }),
      })

      const texts = countButtons(wrapper).map((button) =>
        button
          .findAll('span')
          .map((span) => span.text())
          .join(' '),
      )
      expect(texts).toHaveLength(11)
      expect(texts[0]).toBe('Saved 0')
      expect(texts[1]).toBe('Applied 4')
      expect(texts[6]).toBe('Offer 1')
    })

    it('filters the table to a Pipeline Status when its count is clicked, and back', async () => {
      const { wrapper, router, fetchMock } = await mountAt('/applications', {
        counts: counts({ offer: 1 }),
      })
      const offer = () => countButtons(wrapper)[6]!

      await offer().trigger('click')
      await flushPromises()

      expect(router.currentRoute.value.query).toMatchObject({ status: 'offer' })
      expect(requestsMade(fetchMock)).toContain('GET /api/applications?status=offer')
      expect(offer().attributes('aria-pressed')).toBe('true')

      await offer().trigger('click')
      await flushPromises()

      expect(router.currentRoute.value.query.status).toBeUndefined()
      expect(offer().attributes('aria-pressed')).toBe('false')
    })
  })

  describe('sorting', () => {
    const applications = [
      makeApplication({ role: 'A', applied_at: '2026-10-01', next_action_at: null }),
      makeApplication({ role: 'B', applied_at: null, next_action_at: '2026-11-15' }),
      makeApplication({ role: 'C', applied_at: '2026-10-20', next_action_at: '2026-11-13' }),
    ]
    const roles = (wrapper: Awaited<ReturnType<typeof mountAt>>['wrapper']) =>
      wrapper.findAll('tbody tr').map((tr) => tr.findAll('td')[1]!.text())
    const headerButton = (wrapper: Awaited<ReturnType<typeof mountAt>>['wrapper'], label: string) =>
      wrapper.findAll('thead button').find((button) => button.text().startsWith(label))!

    it('shows the most recently applied first, undated last', async () => {
      const { wrapper } = await mountAt('/applications', { applications })

      expect(roles(wrapper)).toEqual(['C', 'A', 'B'])
    })

    it('sorts by a column when its header is clicked, keeping the sort in the URL', async () => {
      const { wrapper, router } = await mountAt('/applications', { applications })

      await headerButton(wrapper, 'Next action').trigger('click')
      await flushPromises()

      expect(router.currentRoute.value.query).toMatchObject({
        sort: 'next_action_at',
        order: 'asc',
      })
      expect(roles(wrapper)).toEqual(['C', 'B', 'A'])

      await headerButton(wrapper, 'Next action').trigger('click')
      await flushPromises()

      expect(router.currentRoute.value.query).toMatchObject({ order: 'desc' })
      expect(roles(wrapper)).toEqual(['B', 'C', 'A'])
    })

    it('restores the sort from the URL', async () => {
      const { wrapper } = await mountAt('/applications?sort=role&order=desc', { applications })

      expect(roles(wrapper)).toEqual(['C', 'B', 'A'])
      expect(headerButton(wrapper, 'Role').attributes('aria-label')).toContain('descending')
    })
  })
})
