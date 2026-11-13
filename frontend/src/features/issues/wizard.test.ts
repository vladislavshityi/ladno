import { describe, expect, it } from 'vitest'
import { formatLocation } from './wizard'

describe('formatLocation', () => {
  it('joins filled parts in reading order', () => {
    expect(formatLocation({ entrance: '3', floor: '4', apartment: '12', place: ' у лифта ' })).toBe(
      'подъезд 3, этаж 4, кв. 12, у лифта',
    )
  })

  it('returns null when nothing is filled', () => {
    expect(formatLocation({ entrance: ' ', floor: '', apartment: '', place: '' })).toBeNull()
  })
})
