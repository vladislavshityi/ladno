import { describe, expect, it } from 'vitest'
import { plural } from './plural'

describe('plural', () => {
  it.each([
    [0, 'жильцов'],
    [1, 'жилец'],
    [2, 'жильца'],
    [4, 'жильца'],
    [5, 'жильцов'],
    [11, 'жильцов'],
    [14, 'жильцов'],
    [21, 'жилец'],
    [23, 'жильца'],
    [111, 'жильцов'],
  ])('%i -> %s', (count, word) => {
    expect(plural(count, 'жилец', 'жильца', 'жильцов')).toBe(word)
  })
})
