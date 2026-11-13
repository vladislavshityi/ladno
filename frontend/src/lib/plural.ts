/** Russian plural form by count: plural(2, 'жилец', 'жильца', 'жильцов') -> 'жильца'. */
export function plural(count: number, one: string, few: string, many: string): string {
  const n = Math.abs(count) % 100
  if (n > 10 && n < 20) return many
  const last = n % 10
  if (last === 1) return one
  return last >= 2 && last <= 4 ? few : many
}
