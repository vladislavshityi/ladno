import { Skeleton } from '@/components/ui/skeleton'
import FaqPage from '@/features/faq/pages/faq-page'
import { useCapabilities } from '@/features/meta/hooks'
import AssistantPage from './assistant-page'

/** Without a language model the assistant tab shows the FAQ instead. */
export default function AssistantRoute() {
  const { loaded, llm } = useCapabilities()
  if (!loaded) return <Skeleton className="mx-auto h-64 max-w-2xl rounded-2xl" />
  return llm ? <AssistantPage /> : <FaqPage />
}
