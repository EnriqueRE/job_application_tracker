import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import MarkdownView from './MarkdownView.vue'

describe('MarkdownView', () => {
  it('renders Markdown as HTML', () => {
    const wrapper = mount(MarkdownView, {
      props: { source: '# Backend Engineer\n\n- **Python**\n- [site](https://example.com)' },
    })

    expect(wrapper.find('h1').text()).toBe('Backend Engineer')
    expect(wrapper.find('li strong').text()).toBe('Python')
    expect(wrapper.find('a').attributes('href')).toBe('https://example.com')
  })

  it('does not let raw HTML in the Markdown execute', () => {
    const wrapper = mount(MarkdownView, {
      props: {
        source:
          'Hi <img src="x" onerror="alert(1)"> <script>alert(2)</script>\n\n[click](javascript:alert(3))',
      },
    })

    expect(wrapper.find('script').exists()).toBe(false)
    expect(wrapper.find('img').attributes('onerror')).toBeUndefined()
    expect(wrapper.find('a[href^="javascript:"]').exists()).toBe(false)
  })

  it('renders nothing for empty source', () => {
    const wrapper = mount(MarkdownView, { props: { source: '' } })

    expect(wrapper.text()).toBe('')
  })
})
