import { FlaskConical } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useLoadSample, useSamples } from '../hooks'

/** Demo receipts let a visitor try the service without a real paper receipt at hand. */
export function SamplePicker({ onLoaded }: { onLoaded: (receiptId: string) => void }) {
  const { data: samples } = useSamples()
  const load = useLoadSample()
  return (
    <div className="grid gap-2">
      <p className="text-sm font-medium">Или попробуйте на примере</p>
      <div className="flex flex-wrap gap-2">
        {samples?.map((s) => (
          <Button
            key={s.id}
            variant="outline"
            disabled={load.isPending}
            onClick={() => load.mutate(s.id, { onSuccess: (r) => onLoaded(r.id) })}
          >
            <FlaskConical /> {s.title}
          </Button>
        ))}
      </div>
    </div>
  )
}
