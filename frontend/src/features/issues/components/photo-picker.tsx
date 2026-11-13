import { useRef } from 'react'
import { ImagePlus, Loader2, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

export interface PickedPhoto {
  /** Server id once uploaded. */
  id?: string
  preview: string
}

interface Props {
  photos: PickedPhoto[]
  max: number
  onAdd: (files: File[]) => void
  onRemove: (index: number) => void
  disabled?: boolean
}

export function PhotoPicker({ photos, max, onAdd, onRemove, disabled }: Props) {
  const input = useRef<HTMLInputElement>(null)
  return (
    <div className="flex flex-wrap gap-3">
      {photos.map((p, i) => (
        <div key={p.preview} className="group relative size-24 overflow-hidden rounded-xl ring-1 ring-border animate-in zoom-in-90 duration-200">
          <img src={p.preview} alt={`Фото ${i + 1}`} className={cn('size-full object-cover', !p.id && 'opacity-50')} />
          {!p.id && <Loader2 className="absolute inset-0 m-auto size-5 animate-spin" />}
          <Button
            type="button"
            variant="secondary"
            size="icon-xs"
            className="absolute top-1 right-1 rounded-full shadow"
            aria-label={`Удалить фото ${i + 1}`}
            onClick={() => onRemove(i)}
          >
            <X />
          </Button>
        </div>
      ))}
      {photos.length < max && (
        <button
          type="button"
          disabled={disabled}
          onClick={() => input.current?.click()}
          className="flex size-24 flex-col items-center justify-center gap-1 rounded-xl border border-dashed text-xs text-muted-foreground transition-colors hover:bg-muted focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
        >
          <ImagePlus className="size-5" />
          Добавить фото
        </button>
      )}
      <input
        ref={input}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        multiple
        hidden
        data-testid="photo-input"
        onChange={(e) => {
          onAdd(Array.from(e.target.files ?? []).slice(0, max - photos.length))
          e.target.value = ''
        }}
      />
    </div>
  )
}
