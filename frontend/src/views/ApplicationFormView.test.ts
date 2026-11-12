import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory } from 'vue-router'

import App from '@/App.vue'
import { createAppRouter } from '@/router'
import { makeApplicationDetail } from '@/test/applications'
import { requestsMade, stubApi, type RouteHandler } from '@/test/fakeApi'
import { makeOrganization } from '@/test/organizations'

const acme = makeOrganization({ name: 'Acme' })
const globex = makeOrganization({ name: 'Globex' })

/** Records the JSON bodies sent to the fake API, keyed `'METHOD /path'`. */
const sentBodies: Record<string, unknown> = {}

function recording(
  key: string,
  respond: (body: Record<string, unknown>) => Response,
): RouteHandler {
  return async (request) => {
    const body = (await request.json()) as Record<string, unknown>
    sentBodies[key] = body
    return respond(body)
  }
}

async function mountAt(path: string, routes: Record<string, RouteHandler> = {}) {
  const fetchMock = stubApi({
    'GET /api/organizations': (_request, url) => {
      const q = (url.searchParams.get('q') ?? '').toLowerCase()
      return Response.json([acme, globex].filter((org) => org.name.toLowerCase().includes(q)))
    },
    ...routes,
  })
  const router = createAppRouter(createMemoryHistory())
  await router.push(path)
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const wrapper = mount(App, {
    attachTo: document.body,
    global: { plugins: [router, [VueQueryPlugin, { queryClient }]] },
  })
  await flushPromises()
  return { wrapper, router, fetchMock }
}

afterEach(() => {
  document.body.innerHTML = ''
  for (const key of Object.keys(sentBodies)) delete sentBodies[key]
  vi.unstubAllGlobals()
})

describe('New Application page', () => {
  it('creates an Application for a searched Organization and opens its detail screen', async () => {
    const { wrapper, router } = await mountAt('/applications/new', {
      'POST /api/applications': recording('POST /api/applications', (body) =>
        Response.json(makeApplicationDetail({ id: 42, role: body.role as string }), {
          status: 201,
        }),
      ),
    })

    expect(wrapper.get('h1').text()).toBe('New Application')
    await wrapper.get('input[name="organization_search"]').setValue('glob')
    await flushPromises()
    await wrapper.get('[role="option"]').trigger('click')
    await wrapper.get('input[name="role"]').setValue('Backend Engineer')
    await wrapper.get('select[name="work_arrangement"]').setValue('remote')
    await wrapper.get('input[name="vacancy_url"]').setValue('https://jobs.example.com/1')
    await wrapper.get('input[name="applied_at"]').setValue('2026-11-10')
    await wrapper.get('textarea[name="job_description"]').setValue('# Backend Engineer')
    await wrapper.get('form[data-testid="application-form"]').trigger('submit')
    await flushPromises()

    expect(sentBodies['POST /api/applications']).toEqual({
      organization_id: globex.id,
      role: 'Backend Engineer',
      location: null,
      work_arrangement: 'remote',
      vacancy_source: null,
      vacancy_url: 'https://jobs.example.com/1',
      applied_at: '2026-11-10',
      next_action_at: null,
      job_description: '# Backend Engineer',
      interview_notes: null,
      application_notes: null,
    })
    expect(router.currentRoute.value.path).toBe('/applications/42')
  })

  it('asks for the Organization, the role and a well-formed vacancy URL before saving', async () => {
    const { wrapper, fetchMock } = await mountAt('/applications/new')

    await wrapper.get('input[name="vacancy_url"]').setValue('jobs.example.com/1')
    await wrapper.get('form[data-testid="application-form"]').trigger('submit')
    await flushPromises()

    const text = wrapper.text()
    expect(text).toContain('Organization is required.')
    expect(text).toContain('Role is required.')
    expect(text).toContain('Vacancy URL must start with http:// or https://.')
    expect(requestsMade(fetchMock).filter((r) => r.startsWith('POST'))).toEqual([])
  })

  it('shows the server validation message when the API rejects the Application', async () => {
    const { wrapper, router } = await mountAt('/applications/new', {
      'POST /api/applications': () =>
        Response.json(
          {
            detail: [
              {
                loc: ['body', 'vacancy_url'],
                msg: 'Value error, must be a URL starting with http:// or https://',
              },
            ],
          },
          { status: 422 },
        ),
    })

    await wrapper.get('input[name="organization_search"]').setValue('acme')
    await flushPromises()
    await wrapper.get('[role="option"]').trigger('click')
    await wrapper.get('input[name="role"]').setValue('Engineer')
    await wrapper.get('form[data-testid="application-form"]').trigger('submit')
    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toContain(
      'vacancy_url: Value error, must be a URL starting with http:// or https://',
    )
    expect(router.currentRoute.value.path).toBe('/applications/new')
  })

  it('creates a new Organization inline and files the Application under it', async () => {
    const initech = makeOrganization({ name: 'Initech' })
    const { wrapper } = await mountAt('/applications/new', {
      'POST /api/organizations': recording('POST /api/organizations', () =>
        Response.json(initech, { status: 201 }),
      ),
      'POST /api/applications': recording('POST /api/applications', () =>
        Response.json(makeApplicationDetail({ id: 7 }), { status: 201 }),
      ),
    })

    await wrapper.get('input[name="organization_search"]').setValue('Initech')
    await flushPromises()
    expect(wrapper.text()).toContain('No matching Organizations.')
    const createButton = wrapper
      .findAll('button')
      .find((button) => button.text().startsWith('Create new Organization'))!
    await createButton.trigger('click')
    expect((wrapper.get('input[name="name"]').element as HTMLInputElement).value).toBe('Initech')
    await wrapper.get('form:not([data-testid="application-form"])').trigger('submit')
    await flushPromises()

    expect(sentBodies['POST /api/organizations']).toMatchObject({ name: 'Initech' })
    expect(wrapper.get('[data-testid="selected-organization"]').text()).toBe('Initech')

    await wrapper.get('input[name="role"]').setValue('Engineer')
    await wrapper.get('form[data-testid="application-form"]').trigger('submit')
    await flushPromises()

    expect(sentBodies['POST /api/applications']).toMatchObject({
      organization_id: initech.id,
      role: 'Engineer',
    })
  })

  it('previews the Job Description as Markdown while typing', async () => {
    const { wrapper } = await mountAt('/applications/new')

    await wrapper.get('textarea[name="job_description"]').setValue('## Responsibilities')

    expect(wrapper.get('[role="region"][aria-label="Job Description preview"] h2').text()).toBe(
      'Responsibilities',
    )
  })
})

describe('Edit Application page', () => {
  it('saves only the changed fields and returns to the detail screen', async () => {
    const existing = makeApplicationDetail({
      id: 5,
      organization: { id: acme.id, name: 'Acme', organization_type: 'company' },
      role: 'Engineer',
      location: 'Madrid',
      vacancy_url: 'https://jobs.example.com/5',
      job_description: '# Engineer\n',
    })
    const { wrapper, router } = await mountAt('/applications/5/edit', {
      'GET /api/applications/:id': () => Response.json(existing),
      'PATCH /api/applications/:id': recording('PATCH /api/applications/:id', (body) =>
        Response.json({ ...existing, ...body }),
      ),
    })

    expect(wrapper.get('h1').text()).toBe('Edit Engineer at Acme')
    expect(wrapper.get('[data-testid="selected-organization"]').text()).toBe('Acme')
    expect((wrapper.get('input[name="location"]').element as HTMLInputElement).value).toBe('Madrid')
    await wrapper.get('input[name="role"]').setValue('Senior Engineer')
    await wrapper.get('input[name="next_action_at"]').setValue('2026-11-20')
    await wrapper.get('form[data-testid="application-form"]').trigger('submit')
    await flushPromises()

    expect(sentBodies['PATCH /api/applications/:id']).toEqual({
      role: 'Senior Engineer',
      next_action_at: '2026-11-20',
    })
    expect(router.currentRoute.value.path).toBe('/applications/5')
  })

  it('can clear an optional field', async () => {
    const existing = makeApplicationDetail({ id: 6, location: 'Madrid' })
    const { wrapper } = await mountAt('/applications/6/edit', {
      'GET /api/applications/:id': () => Response.json(existing),
      'PATCH /api/applications/:id': recording('PATCH /api/applications/:id', (body) =>
        Response.json({ ...existing, ...body }),
      ),
    })

    await wrapper.get('input[name="location"]').setValue('')
    await wrapper.get('form[data-testid="application-form"]').trigger('submit')
    await flushPromises()

    expect(sentBodies['PATCH /api/applications/:id']).toEqual({ location: null })
  })
})
