import { useEffect, useRef, useState } from 'react'
import { ImageUp } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { parseEpdQr, type EpdQr } from '../epd-qr'
import { decodeQr, decodeQrFile } from '../qr-decode'

const SCAN_INTERVAL_MS = 400
const NOT_FOUND = 'Не нашли платёжный QR-код. Снимите крупнее, чтобы код занимал треть кадра, или введите вручную'

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  onScanned: (qr: EpdQr) => void
}

/** Scans the payment QR code with the camera, or reads it from a photo. */
export function QrScannerDialog({ open, onOpenChange, onScanned }: Props) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Сканировать QR-код</DialogTitle>
          <DialogDescription>Наведите камеру на QR-код в нижней части квитанции. Из него возьмём получателя и то, что в нём есть: итог и период, если они указаны.</DialogDescription>
        </DialogHeader>
        <Scanner
          onText={(text) => {
            const qr = parseEpdQr(text)
            if (qr) {
              onScanned(qr)
              onOpenChange(false)
            }
            return qr !== null
          }}
        />
      </DialogContent>
    </Dialog>
  )
}

/** Mounted only while the dialog is open, so the camera starts and stops with it. */
function Scanner({ onText }: { onText: (text: string) => boolean }) {
  const video = useRef<HTMLVideoElement>(null)
  const file = useRef<HTMLInputElement>(null)
  const [message, setMessage] = useState('')
  const handle = useRef(onText)
  useEffect(() => {
    handle.current = onText
  })

  useEffect(() => {
    let stopped = false
    let stream: MediaStream | undefined
    let timer: number | undefined

    const scan = async () => {
      const element = video.current
      if (stopped || !element) return
      const text = element.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA ? await decodeQr(element) : null
      if (text && handle.current(text)) return
      timer = window.setTimeout(() => void scan(), SCAN_INTERVAL_MS)
    }

    navigator.mediaDevices
      ?.getUserMedia({ video: { facingMode: 'environment' } })
      .then(async (media) => {
        if (stopped) return media.getTracks().forEach((t) => t.stop())
        stream = media
        if (video.current) {
          video.current.srcObject = media
          await video.current.play()
        }
        void scan()
      })
      .catch(() => setMessage('Камера недоступна. Выберите фото с QR-кодом.'))

    return () => {
      stopped = true
      window.clearTimeout(timer)
      stream?.getTracks().forEach((t) => t.stop())
    }
  }, [])

  const readPhoto = async (photo: File) => {
    try {
      const text = await decodeQrFile(photo)
      if (!text || !onText(text)) setMessage(NOT_FOUND)
    } catch {
      setMessage('Не удалось открыть фото')
    }
  }

  return (
    <>
      <video ref={video} muted playsInline className="aspect-square w-full rounded-xl bg-muted object-cover" />
      {message && (
        <p role="alert" className="text-sm text-muted-foreground">
          {message}
        </p>
      )}
      <Button type="button" variant="outline" onClick={() => file.current?.click()}>
        <ImageUp /> Выбрать фото с QR-кодом
      </Button>
      <input
        ref={file}
        type="file"
        accept="image/*"
        hidden
        onChange={(e) => {
          const photo = e.target.files?.[0]
          if (photo) void readPhoto(photo)
          e.target.value = ''
        }}
      />
    </>
  )
}
