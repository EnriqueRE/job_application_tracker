import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { createMemoryHistory } from 'vue-router'

import type { Schemas } from '@/api/client'
import App from '@/App.vue'
import { createAppRouter } from '@/router'
import { makeApplicationDetail, makeTimelineEvent } from '@/test/applications'
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
    expect(wrapper.find('a[href="https://jobs.example.com/42"]').exists()).toBe(true)
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

  describe('timeline', () => {
    it('lists the Application Events', async () => {
      const { wrapper } = await mountDetail(
        makeApplicationDetail({
          events: [
            makeTimelineEvent({ event_type: 'applied', notes: 'Via referral' }),
            makeTimelineEvent({ event_type: 'screening', notes: 'Call with recruiter' }),
          ],
        }),
      )

      const timeline = section(wrapper, 'Timeline')
      expect(timeline.text()).toContain('Applied')
      expect(timeline.text()).toContain('Via referral')
      expect(timeline.text()).toContain('Screening')
      expect(timeline.text()).toContain('Call with recruiter')
    })

    it('adds an Application Event and shows the new Pipeline Status', async () => {
      const application = makeApplicationDetail({ current_status: 'saved' })
      let posted: unknown
      const { wrapper } = await mountDetail(application, {
        'POST /api/applications/:id/events': async (request) => {
          posted = await request.json()
          const event = makeTimelineEvent({ event_type: 'applied', notes: 'Sent CV' })
          application.events = [...application.events, event]
          application.current_status = 'applied'
          return Response.json(
            {
              event: { ...event, application_id: application.id },
              application: {
                id: application.id,
                current_status: 'applied',
                status_overridden: false,
              },
            },
            { status: 201 },
          )
        },
      })

      const timeline = section(wrapper, 'Timeline')
      await buttonIn(timeline, 'Add event').trigger('click')
      await timeline.get('select[name="event_type"]').setValue('applied')
      await timeline.get('input[name="occurred_at"]').setValue('2026-11-05T14:30')
      await timeline.get('textarea[name="notes"]').setValue('Sent CV')
      await buttonIn(timeline, 'Save event').trigger('click')
      await flushPromises()

      expect(posted).toEqual({
        event_type: 'applied',
        occurred_at: new Date('2026-11-05T14:30').toISOString(),
        notes: 'Sent CV',
      })
      expect(section(wrapper, 'Timeline').text()).toContain('Sent CV')
      expect(wrapper.get('[data-testid="pipeline-status"]').text()).toContain('Applied')
    })

    it('edits an Application Event', async () => {
      const event = makeTimelineEvent({ event_type: 'note', notes: 'Old note' })
      const application = makeApplicationDetail({ events: [event] })
      let patched: unknown
      const { fetchMock, wrapper } = await mountDetail(application, {
        'PATCH /api/applications/:id/events/:eventId': async (request) => {
          patched = await request.json()
          Object.assign(event, patched)
          return Response.json({
            event: { ...event, application_id: application.id },
            application: { id: application.id, current_status: 'saved', status_overridden: false },
          })
        },
      })

      const timeline = section(wrapper, 'Timeline')
      await buttonIn(timeline, 'Edit').trigger('click')
      const notes = timeline.get('textarea[name="notes"]')
      expect((notes.element as HTMLTextAreaElement).value).toBe('Old note')
      await notes.setValue('New note')
      await buttonIn(timeline, 'Save event').trigger('click')
      await flushPromises()

      expect(requestsMade(fetchMock)).toContain(
        `PATCH /api/applications/${application.id}/events/${event.id}`,
      )
      expect(patched).toMatchObject({ event_type: 'note', notes: 'New note' })
      expect(section(wrapper, 'Timeline').text()).toContain('New note')
    })

    it('deletes an Application Event after confirming', async () => {
      const event = makeTimelineEvent({ notes: 'Mistake' })
      const application = makeApplicationDetail({ events: [event] })
      const { fetchMock, wrapper } = await mountDetail(application, {
        'DELETE /api/applications/:id/events/:eventId': () => {
          application.events = []
          return Response.json({
            id: application.id,
            current_status: 'saved',
            status_overridden: false,
          })
        },
      })

      const timeline = section(wrapper, 'Timeline')
      await buttonIn(timeline, 'Delete').trigger('click')
      expect(requestsMade(fetchMock).some((r) => r.startsWith('DELETE'))).toBe(false)
      await buttonIn(timeline, 'Delete event').trigger('click')
      await flushPromises()

      expect(requestsMade(fetchMock)).toContain(
        `DELETE /api/applications/${application.id}/events/${event.id}`,
      )
      expect(section(wrapper, 'Timeline').text()).not.toContain('Mistake')
    })
  })

  describe('Status Override', () => {
    it('sets a Status Override', async () => {
      const application = makeApplicationDetail({ current_status: 'applied' })
      let body: unknown
      const { wrapper } = await mountDetail(application, {
        'PUT /api/applications/:id/status-override': async (request) => {
          body = await request.json()
          application.current_status = 'offer'
          application.status_overridden = true
          return Response.json({
            id: application.id,
            current_status: 'offer',
            status_overridden: true,
          })
        },
      })

      await wrapper.get('select[name="override_status"]').setValue('offer')
      await buttonIn(wrapper, 'Set override').trigger('click')
      await flushPromises()

      expect(body).toEqual({ status: 'offer' })
      const status = wrapper.get('[data-testid="pipeline-status"]').text()
      expect(status).toContain('Offer')
      expect(status).toContain('Status Override')
    })

    it('clears a Status Override', async () => {
      const application = makeApplicationDetail({
        current_status: 'offer',
        status_overridden: true,
      })
      const { fetchMock, wrapper } = await mountDetail(application, {
        'DELETE /api/applications/:id/status-override': () => {
          application.current_status = 'applied'
          application.status_overridden = false
          return Response.json({
            id: application.id,
            current_status: 'applied',
            status_overridden: false,
          })
        },
      })

      await buttonIn(wrapper, 'Clear override').trigger('click')
      await flushPromises()

      expect(requestsMade(fetchMock)).toContain(
        `DELETE /api/applications/${application.id}/status-override`,
      )
      expect(wrapper.get('[data-testid="pipeline-status"]').text()).not.toContain('Status Override')
    })
  })

  describe('archiving', () => {
    it('archives the Application after confirming', async () => {
      const application = makeApplicationDetail()
      const { fetchMock, wrapper } = await mountDetail(application, {
        'POST /api/applications/:id/archive': () => {
          application.archived_at = '2026-11-12T10:00:00Z'
          return Response.json(application)
        },
      })

      await buttonIn(wrapper, 'Archive').trigger('click')
      expect(requestsMade(fetchMock).some((r) => r.endsWith('/archive'))).toBe(false)
      await buttonIn(wrapper, 'Archive Application').trigger('click')
      await flushPromises()

      expect(requestsMade(fetchMock)).toContain(`POST /api/applications/${application.id}/archive`)
      expect(wrapper.get('[data-testid="pipeline-status"]').text()).toContain('Archived')
      expect(buttonIn(wrapper, 'Restore').exists()).toBe(true)
    })

    it('can back out of archiving', async () => {
      const { fetchMock, wrapper } = await mountDetail(makeApplicationDetail())

      await buttonIn(wrapper, 'Archive').trigger('click')
      await buttonIn(wrapper, 'Keep').trigger('click')

      expect(requestsMade(fetchMock).some((r) => r.endsWith('/archive'))).toBe(false)
      expect(wrapper.findAll('button').some((b) => b.text() === 'Archive Application')).toBe(false)
    })

    it('restores an archived Application', async () => {
      const application = makeApplicationDetail({ archived_at: '2026-11-12T10:00:00Z' })
      const { fetchMock, wrapper } = await mountDetail(application, {
        'POST /api/applications/:id/restore': () => {
          application.archived_at = null
          return Response.json(application)
        },
      })

      await buttonIn(wrapper, 'Restore').trigger('click')
      await flushPromises()

      expect(requestsMade(fetchMock)).toContain(`POST /api/applications/${application.id}/restore`)
      expect(wrapper.get('[data-testid="pipeline-status"]').text()).not.toContain('Archived')
    })
  })

  it('says so when the Application does not exist', async () => {
    const { wrapper } = await mountDetail(makeApplicationDetail({ id: 999 }), {
      'GET /api/applications/:id': () =>
        Response.json({ detail: 'Application 999 was not found' }, { status: 404 }),
    })

    expect(wrapper.get('[role="alert"]').text()).toContain('Application 999 was not found')
  })
})
