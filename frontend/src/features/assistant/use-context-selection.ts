import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useIssues } from '@/features/issues/hooks'
import { useReceipts } from '@/features/receipts/hooks'
import type { ChatContext } from './api'

export const MAX_ISSUES = 5
export const MAX_RECEIPTS = 3
const DEFAULT_RECEIPTS = 2

/**
 * What the assistant may see. Defaults to the latest receipts and issues, or to the single item
 * from a deep link (?issue=<id> / ?receipt=<id>) until the user edits the selection.
 */
export function useContextSelection() {
  const [params] = useSearchParams()
  const issues = useIssues()
  const receipts = useReceipts()
  const [edited, setEdited] = useState<ChatContext | null>(null)

  const initial = useMemo<ChatContext>(() => {
    const issue = params.get('issue')
    const receipt = params.get('receipt')
    if (issue || receipt) return { issue_ids: issue ? [issue] : [], receipt_ids: receipt ? [receipt] : [] }
    return {
      issue_ids: (issues.data ?? []).slice(0, MAX_ISSUES).map((i) => i.id),
      receipt_ids: (receipts.data ?? []).slice(0, DEFAULT_RECEIPTS).map((r) => r.id),
    }
  }, [params, issues.data, receipts.data])

  return {
    selection: edited ?? initial,
    setSelection: setEdited,
    issues: issues.data ?? [],
    receipts: receipts.data ?? [],
    ready: !issues.isPending && !receipts.isPending,
  }
}
