import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

import MarkdownSection from './MarkdownSection.vue'

function mountSection(source: string | null, save = vi.fn().mockResolvedValue(undefined)) {
  const wrapper = mount(MarkdownSection, {
    props: { title: 'Interview Notes', source, save },
  })
  return { wrapper, save }
}

function button(wrapper: ReturnType<typeof mountSection>['wrapper'], label: string) {
  const match = wrapper.findAll('button').find((b) => b.text() === label)
  if (!match) throw new Error(`No "${label}" button`)
  return match
}

describe('MarkdownSection', () => {
  it('renders the Markdown by default', () => {
    const { wrapper } = mountSection('## Questions\n\n- Team size?')

    expect(wrapper.get('h2').text()).toBe('Interview Notes')
    expect(wrapper.find('textarea').exists()).toBe(false)
    expect(wrapper.get('.markdown h2').text()).toBe('Questions')
    expect(wrapper.get('.markdown li').text()).toBe('Team size?')
  })

  it('prompts to add content when empty', () => {
    const { wrapper } = mountSection(null)

    expect(wrapper.text()).toContain('No Interview Notes yet.')
    expect(button(wrapper, 'Add').exists()).toBe(true)
  })

  it('edits in a textarea with a live preview', async () => {
    const { wrapper } = mountSection('Old text')

    await button(wrapper, 'Edit').trigger('click')
    const textarea = wrapper.get('textarea')
    expect((textarea.element as HTMLTextAreaElement).value).toBe('Old text')

    await textarea.setValue('**Bold** idea')
    expect(wrapper.get('[data-testid="markdown-preview"] strong').text()).toBe('Bold')
  })

  it('cancelling discards the draft', async () => {
    const { wrapper, save } = mountSection('Old text')

    await button(wrapper, 'Edit').trigger('click')
    await wrapper.get('textarea').setValue('Changed')
    await button(wrapper, 'Cancel').trigger('click')

    expect(save).not.toHaveBeenCalled()
    expect(wrapper.find('textarea').exists()).toBe(false)
    expect(wrapper.get('.markdown').text()).toBe('Old text')
  })

  it('saves the draft and returns to reading', async () => {
    const { wrapper, save } = mountSection('Old text')

    await button(wrapper, 'Edit').trigger('click')
    await wrapper.get('textarea').setValue('New text')
    await button(wrapper, 'Save').trigger('click')
    await flushPromises()

    expect(save).toHaveBeenCalledWith('New text')
    expect(wrapper.find('textarea').exists()).toBe(false)
  })

  it('saves an emptied section as null', async () => {
    const { wrapper, save } = mountSection('Old text')

    await button(wrapper, 'Edit').trigger('click')
    await wrapper.get('textarea').setValue('   ')
    await button(wrapper, 'Save').trigger('click')
    await flushPromises()

    expect(save).toHaveBeenCalledWith(null)
  })

  it('keeps editing and shows the error when saving fails', async () => {
    const { wrapper } = mountSection('Old text', vi.fn().mockRejectedValue(new Error('Boom')))

    await button(wrapper, 'Edit').trigger('click')
    await wrapper.get('textarea').setValue('New text')
    await button(wrapper, 'Save').trigger('click')
    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toContain('Boom')
    expect((wrapper.get('textarea').element as HTMLTextAreaElement).value).toBe('New text')
  })
})
