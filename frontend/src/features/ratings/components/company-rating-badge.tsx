import { Link } from 'react-router-dom'
import { Trophy } from 'lucide-react'
import { TONE_CLASSES, scoreTone } from '@/lib/design'
import { cn } from '@/lib/utils'
import { useCompanyRating } from '../hooks'

/** "Rating of your management company: 54" linking to its page; hidden while the score is unknown. */
export function CompanyRatingBadge({ companyId }: { companyId: number | null | undefined }) {
  const { data } = useCompanyRating(companyId)
  if (data?.score == null) return null
  return (
    <Link
      to={`/ratings/${data.id}`}
      className={cn(
        'inline-flex w-fit items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium hover:opacity-80',
        TONE_CLASSES[scoreTone(data.score)],
      )}
    >
      <Trophy className="size-3.5" /> Рейтинг вашей УК: {data.score}
    </Link>
  )
}
