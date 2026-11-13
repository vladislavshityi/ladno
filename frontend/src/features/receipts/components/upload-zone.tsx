import { useRef, useState } from 'react'
import { Loader2, UploadCloud } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Props {
  onFile: (file: File) => void
  pending: boolean
}

export function UploadZone({ onFile, pending }: Props) {
  const input = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)

  return (
    <button
      type="button"
      disabled={pending}
      onClick={() => input.current?.click()}
      onDragOver={(e) => {
        e.preventDefault()
        setDragging(true)
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault()
        setDragging(false)
        const file = e.dataTransfer.files[0]
        if (file) onFile(file)
      }}
      className={cn(
        'flex w-full flex-col items-center gap-2 rounded-2xl border-2 border-dashed px-6 py-10 text-center transition-all focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none',
        dragging ? 'scale-[1.01] border-primary bg-primary/8' : 'hover:bg-muted/60',
      )}
    >
      {pending ? <Loader2 className="size-7 animate-spin text-primary" /> : <UploadCloud className="size-7 text-primary" />}
      <span className="font-medium">{pending ? 'Разбираем квитанцию…' : 'Перетащите фото или PDF квитанции'}</span>
      <span className="text-sm text-muted-foreground">{pending ? 'Это занимает до минуты' : 'или нажмите, чтобы выбрать файл · до 10 МБ'}</span>
      <input
        ref={input}
        type="file"
        accept="image/jpeg,image/png,image/webp,application/pdf"
        hidden
        data-testid="receipt-input"
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (file) onFile(file)
          e.target.value = ''
        }}
      />
    </button>
  )
}
