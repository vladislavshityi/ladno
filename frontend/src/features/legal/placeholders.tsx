import type { ReactNode } from 'react'

/** Wraps `[placeholders]` that the operator must fill in before launch. */
export function withPlaceholders(text: string): ReactNode {
  return text.split(/(\[[^\]]+\])/).map((part, i) => (part.startsWith('[') ? <mark key={i}>{part}</mark> : part))
}
