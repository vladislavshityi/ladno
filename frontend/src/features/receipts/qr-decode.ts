/** Reads a QR code from an image or video frame: the browser's BarcodeDetector, else jsQR. */

interface Detector {
  detect: (source: ImageBitmapSource) => Promise<{ rawValue: string }[]>
}

declare global {
  interface Window {
    BarcodeDetector?: new (options: { formats: string[] }) => Detector
  }
}

let detector: Detector | null | undefined

function nativeDetector() {
  if (detector === undefined) detector = window.BarcodeDetector ? new window.BarcodeDetector({ formats: ['qr_code'] }) : null
  return detector
}

async function decodeWithJsQr(source: CanvasImageSource, width: number, height: number) {
  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const context = canvas.getContext('2d', { willReadFrequently: true })
  if (!context) return null
  context.drawImage(source, 0, 0, width, height)
  const { default: jsQR } = await import('jsqr')
  return jsQR(context.getImageData(0, 0, width, height).data, width, height)?.data ?? null
}

/** Text of the first QR code in the frame, or null when there is none. */
export async function decodeQr(source: HTMLVideoElement | HTMLImageElement): Promise<string | null> {
  const native = nativeDetector()
  if (native) {
    try {
      return (await native.detect(source))[0]?.rawValue ?? null
    } catch {
      /* fall back to jsQR below */
    }
  }
  const width = source instanceof HTMLVideoElement ? source.videoWidth : source.naturalWidth
  const height = source instanceof HTMLVideoElement ? source.videoHeight : source.naturalHeight
  return width && height ? decodeWithJsQr(source, width, height) : null
}

/** Text of the QR code on a photo chosen from the device. */
export async function decodeQrFile(file: File): Promise<string | null> {
  const url = URL.createObjectURL(file)
  try {
    const image = new Image()
    image.src = url
    await image.decode()
    return await decodeQr(image)
  } finally {
    URL.revokeObjectURL(url)
  }
}
