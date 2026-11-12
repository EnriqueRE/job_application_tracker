import { describe, expect, it } from 'vitest'

import { blankToNull } from './text'

describe('blankToNull', () => {
  it('turns empty or whitespace-only text into null', () => {
    expect(blankToNull('')).toBeNull()
    expect(blankToNull('  \n\t')).toBeNull()
    expect(blankToNull('  \n', { keepWhitespace: true })).toBeNull()
  })

  it('trims text that has content', () => {
    expect(blankToNull('  Acme  ')).toBe('Acme')
  })

  it('can keep surrounding whitespace, for Markdown', () => {
    expect(blankToNull('    code\n', { keepWhitespace: true })).toBe('    code\n')
  })
})
