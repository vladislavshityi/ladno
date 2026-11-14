import { useState } from 'react'
import { toast } from 'sonner'
import { useMe } from '@/features/auth/hooks'
import { errorMessage } from '@/lib/api-client'
import { type LetterKey } from './letter-fields'
import { useUpdateProfile } from './hooks'
import { toProfileUpdate } from './profile-update'
import { useLetterForm } from './use-letter-form'

const NEEDED: readonly LetterKey[] = ['full_name', 'apartment', 'phone']

/**
 * The "data for the letter" step before a letter is made: asks only for what the profile lacks
 * and saves the answer to the profile. The resident may skip it.
 */
export function useApplicantPrompt() {
  const { data: me } = useMe()
  const update = useUpdateProfile()
  const [skipped, setSkipped] = useState(false)
  const keys = NEEDED.filter((key) => !me?.[key])
  const visible = Boolean(me) && keys.length > 0 && !skipped
  const form = useLetterForm(me, NEEDED, ['full_name'])

  /** Saves the typed data. True when there is nothing to save or it was saved; false keeps the resident on the form. */
  const save = async (): Promise<boolean> => {
    if (!visible || !me) return true
    const changes = form.validate()
    if (!changes) return false
    // Fields the profile already has are not touched.
    const missing = Object.fromEntries(keys.map((key) => [key, changes[key]]))
    try {
      await update.mutateAsync(toProfileUpdate(me, missing))
      return true
    } catch (err) {
      if (!form.showServerErrors(err)) toast.error(errorMessage(err))
      return false
    }
  }

  return { me, visible, keys, form, saving: update.isPending, save, skip: () => setSkipped(true) }
}
