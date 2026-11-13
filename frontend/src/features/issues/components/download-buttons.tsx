import { useState } from 'react'
import { Download, FileText, Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { errorMessage } from '@/lib/api-client'
import { saveBlob } from '@/lib/download'
import { isTelegramWebApp } from '@/lib/telegram'
import type { Issue } from '@/types/models'
import { issuesApi } from '../api'

/** Letter PDF and the photos as files: evidence to attach to a paper or e-mail complaint. */
export function DownloadButtons({ issue }: { issue: Issue }) {
  const [busy, setBusy] = useState<string | null>(null)

  async function run(key: string, filename: string, load: () => Promise<Blob>) {
    setBusy(key)
    try {
      saveBlob(await load(), filename)
    } catch (err) {
      toast.error(errorMessage(err))
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="grid gap-2">
      <div className="flex flex-wrap gap-2">
        <Button variant="outline" disabled={busy !== null} onClick={() => run('pdf', 'letter.pdf', () => issuesApi.letterPdf(issue.id))}>
          {busy === 'pdf' ? <Loader2 className="animate-spin" /> : <FileText />} Скачать письмо (PDF)
        </Button>
        {issue.photos.map((photo, i) => (
          <Button
            key={photo.id}
            variant="outline"
            disabled={busy !== null}
            onClick={() => run(photo.id, `photo-${i + 1}`, () => issuesApi.photoBlob(photo.url))}
          >
            {busy === photo.id ? <Loader2 className="animate-spin" /> : <Download />} Скачать фото {i + 1}
          </Button>
        ))}
      </div>
      {isTelegramWebApp() && (
        <p className="text-xs text-muted-foreground">
          В Telegram скачивание файлов может не сработать. Если так, откройте сайт в браузере.
        </p>
      )}
    </div>
  )
}
