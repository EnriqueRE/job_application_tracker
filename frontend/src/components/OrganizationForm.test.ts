import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import { requestsMade, stubApi, type RouteHandler } from '@/test/fakeApi'
import { makeOrganization } from '@/test/organizations'

import OrganizationForm from './OrganizationForm.vue'

type Props = InstanceType<typeof OrganizationForm>['$props']

function mountForm(props: Props, routes: Record<string, RouteHandler> = {}) {
  const bodies: unknown[] = []
  const recordBody =
    (handler: RouteHandler): RouteHandler =>
    async (request, url, params) => {
      bodies.push(await request.clone().json())
      return handler(request, url, params)
    }
  const fetchMock = stubApi(
    Object.fromEntries(Object.entries(routes).map(([key, handler]) => [key, recordBody(handler)])),
  )
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const wrapper = mount(OrganizationForm, {
    props,
    global: { plugins: [[VueQueryPlugin, { queryClient }]] },
  })
  return { wrapper, fetchMock, bodies }
}

describe('OrganizationForm', () => {
  it('creates an Organization from the filled-in fields and emits it', async () => {
    const created = makeOrganization({ name: 'Hays', organization_type: 'recruiting_firm' })
    const { wrapper, bodies } = mountForm(
      {},
      { 'POST /api/organizations': () => Response.json(created, { status: 201 }) },
    )

    await wrapper.get('input[name="name"]').setValue('Hays')
    await wrapper.get('select[name="organization_type"]').setValue('recruiting_firm')
    await wrapper.get('input[name="industry"]').setValue('Staffing')
    await wrapper.get('input[name="priority"]').setValue('4')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(bodies).toEqual([
      {
        name: 'Hays',
        organization_type: 'recruiting_firm',
        industry: 'Staffing',
        location: null,
        priority: 4,
        website_url: null,
        career_url: null,
        contact_url: null,
        notes: null,
      },
    ])
    expect(wrapper.emitted('saved')).toEqual([[created]])
  })

  it('starts from the given name and type, for creating an Organization inline', () => {
    const { wrapper } = mountForm({ initialName: 'Globex', initialType: 'portal' })

    expect((wrapper.get('input[name="name"]').element as HTMLInputElement).value).toBe('Globex')
    expect(
      (wrapper.get('select[name="organization_type"]').element as HTMLSelectElement).value,
    ).toBe('portal')
  })

  it('requires a name before sending anything', async () => {
    const { wrapper, fetchMock } = mountForm({})

    await wrapper.get('input[name="name"]').setValue('   ')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toContain('Name is required')
    expect(requestsMade(fetchMock)).toEqual([])
    expect(wrapper.emitted('saved')).toBeUndefined()
  })

  it('edits an existing Organization, sending only what changed', async () => {
    const acme = makeOrganization({ name: 'Acme', industry: 'Retail', location: 'Madrid' })
    const { wrapper, bodies } = mountForm(
      { organization: acme },
      {
        'PATCH /api/organizations/:id': () => Response.json({ ...acme, location: null }),
      },
    )

    expect((wrapper.get('input[name="industry"]').element as HTMLInputElement).value).toBe('Retail')
    await wrapper.get('input[name="location"]').setValue('')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(bodies).toEqual([{ location: null }])
    expect(wrapper.emitted('saved')).toEqual([[{ ...acme, location: null }]])
  })

  it('shows the reason the backend rejected the Organization', async () => {
    const { wrapper } = mountForm(
      {},
      {
        'POST /api/organizations': () =>
          Response.json({ detail: "A company named 'Acme' already exists" }, { status: 409 }),
      },
    )

    await wrapper.get('input[name="name"]').setValue('Acme')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toContain("A company named 'Acme' already exists")
    expect(wrapper.emitted('saved')).toBeUndefined()
  })

  it('emits cancel', async () => {
    const { wrapper } = mountForm({})

    await wrapper.get('button[type="button"]').trigger('click')

    expect(wrapper.emitted('cancel')).toHaveLength(1)
  })
})
