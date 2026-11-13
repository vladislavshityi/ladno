import { useState } from 'react'
import { Check, Copy } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'

export function CopyButton({ text, label = 'Скопировать' }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      toast.error('Не удалось скопировать — выделите текст вручную')
    }
  }
  return (
    <Button variant="outline" size="sm" onClick={() => void copy()}>
      {copied ? <Check className="text-success" /> : <Copy />}
      {copied ? 'Скопировано' : label}
    </Button>
  )
}
