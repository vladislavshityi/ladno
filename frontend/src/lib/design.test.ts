import { describe, expect, it } from 'vitest'
import { scoreTone } from './design'

describe('scoreTone', () => {
  it('maps score ranges to tones', () => {
    expect(scoreTone(85)).toBe('success')
    expect(scoreTone(70)).toBe('success')
    expect(scoreTone(54)).toBe('warning')
    expect(scoreTone(40)).toBe('warning')
    expect(scoreTone(39)).toBe('danger')
  })
})
