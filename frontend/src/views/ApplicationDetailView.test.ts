import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { createMemoryHistory } from 'vue-router'

import type { Schemas } from '@/api/client'
import App from '@/App.vue'
import { createAppRouter } from '@/router'
import { makeApplicationDetail } from '@/test/applications'
import { requestsMade, stubApi, type RouteHandler } from '@/test/fakeApi'

type ApplicationDetail = Schemas['ApplicationDetail']

/** Mount the app at an Application's page with a fake backend that serves `application`. */
async function mountDetail(
  application: ApplicationDetail,
  routes: Record<string, RouteHandler> = {},
) {
  const fetchMock = stubApi({
    'GET /api/applications/:id': () => Response.json(application),
    ...routes,
  })
  const router = createAppRouter(createMemoryHistory())
  await router.push(`/applications/${application.id}`)
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const wrapper = mount(App, {
    global: { plugins: [router, [VueQueryPlugin, { queryClient }]] },
  })
  await flushPromises()
  return { wrapper, router, fetchMock }
}

function buttonIn(wrapper: VueWrapper | ReturnType<VueWrapper['get']>, label: string) {
  const match = wrapper.findAll('button').find((b) => b.text() === label)
  if (!match) throw new Error(`No "${label}" button`)
  return match
}

function section(wrapper: VueWrapper, title: string) {
  const match = wrapper.findAll('section').find((s) => s.find('h2').text() === title)
  if (!match) throw new Error(`No "${title}" section`)
  return match
}

describe('Application detail page', () => {
  it('shows the Application, its Organization, Pipeline Status and vacancy URL', async () => {
    const { wrapper } = await mountDetail(
      makeApplicationDetail({
        role: 'Staff Engineer',
        organization: { id: 4, name: 'Globex', organization_type: 'company' },
        location: 'Madrid',
        work_arrangement: 'hybrid',
        current_status: 'technical_interview',
        status_overridden: true,
        vacancy_url: 'https://jobs.example.com/42',
      }),
    )

    expect(wrapper.get('h1').text()).toBe('Staff Engineer')
    expect(wrapper.text()).toContain('Globex')
    expect(wrapper.text()).toContain('Madrid')
    expect(wrapper.text()).toContain('Hybrid')
    expect(wrapper.get('[data-testid="pipeline-status"]').text()).toContain('Technical interview')
    expect(wrapper.get('[data-testid="pipeline-status"]').text()).toContain('Status Override')
    expect(wrapper.get('a[href="https://jobs.example.com/42"]').exists()).toBe(true)
  })

  it('renders the Job Description and prompts for empty Interview Notes', async () => {
    const { wrapper } = await mountDetail(
      makeApplicationDetail({ job_description: '## About the role\n\nBuild things.' }),
    )

    expect(section(wrapper, 'Job Description').get('.markdown h2').text()).toBe('About the role')
    expect(section(wrapper, 'Interview Notes').text()).toContain('No Interview Notes yet.')
    expect(section(wrapper, 'Application Notes').text()).toContain('No Application Notes yet.')
  })

  it('saves edited Interview Notes', async () => {
    const application = makeApplicationDetail({ interview_notes: 'Old' })
    let patched: unknown
    const { wrapper, fetchMock } = await mountDetail(application, {
      'PATCH /api/applications/:id': async (request) => {
        patched = await request.json()
        Object.assign(application, patched)
        return Response.json(application)
      },
    })

    const notes = section(wrapper, 'Interview Notes')
    await buttonIn(notes, 'Edit').trigger('click')
    await notes.get('textarea').setValue('- Ask about on-call')
    await buttonIn(notes, 'Save').trigger('click')
    await flushPromises()

    expect(patched).toEqual({ interview_notes: '- Ask about on-call' })
    expect(requestsMade(fetchMock)).toContain(`PATCH /api/applications/${application.id}`)
    const updated = section(wrapper, 'Interview Notes')
    expect(updated.find('textarea').exists()).toBe(false)
    expect(updated.get('.markdown li').text()).toBe('Ask about on-call')
  })

  it('says so when the Application does not exist', async () => {
    const { wrapper } = await mountDetail(makeApplicationDetail({ id: 999 }), {
      'GET /api/applications/:id': () =>
        Response.json({ detail: 'Application 999 was not found' }, { status: 404 }),
    })

    expect(wrapper.get('[role="alert"]').text()).toContain('Application 999 was not found')
  })
})
