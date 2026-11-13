/** Finds the payment-document QR code in an image or a video frame with ZXing (WebAssembly). */
import { parseEpdQr } from './epd-qr'

/** Larger canvases only slow the decoder down. */
const MAX_SIDE = 4000

type Source = HTMLVideoElement | HTMLImageElement

// The reader and its wasm file are loaded on first use, so they stay out of the main bundle.
async function loadReader() {
  const [reader, { default: wasmUrl }] = await Promise.all([import('zxing-wasm/reader'), import('zxing-wasm/reader/zxing_reader.wasm?url')])
  reader.prepareZXingModule({ overrides: { locateFile: (name: string, prefix: string) => (name.endsWith('.wasm') ? wasmUrl : prefix + name) } })
  return reader.readBarcodes
}

let readerPromise: ReturnType<typeof loadReader> | undefined

function sizeOf(source: Source) {
  return source instanceof HTMLVideoElement
    ? { width: source.videoWidth, height: source.videoHeight }
    : { width: source.naturalWidth, height: source.naturalHeight }
}

type Filter = 'none' | 'sharpen' | 'contrast'

/** Draws the source scaled by `scale` (capped at MAX_SIDE) and applies the filter. */
function render(source: Source, scale: number, filter: Filter = 'none'): ImageData | null {
  const { width, height } = sizeOf(source)
  if (!width || !height) return null
  const k = Math.min(scale, MAX_SIDE / Math.max(width, height))
  const canvas = document.createElement('canvas')
  canvas.width = Math.round(width * k)
  canvas.height = Math.round(height * k)
  const context = canvas.getContext('2d', { willReadFrequently: true })
  if (!context) return null
  context.imageSmoothingEnabled = true
  context.imageSmoothingQuality = 'high'
  context.drawImage(source, 0, 0, canvas.width, canvas.height)
  const image = context.getImageData(0, 0, canvas.width, canvas.height)
  if (filter !== 'none') {
    const gray = toGray(image)
    if (filter === 'sharpen') unsharp(gray, image.width, image.height, Math.max(2, Math.round(k)))
    else stretchContrast(gray)
    fromGray(gray, image)
  }
  return image
}

function toGray(image: ImageData): Float32Array {
  const gray = new Float32Array(image.width * image.height)
  const data = image.data
  for (let i = 0; i < gray.length; i++) gray[i] = (data[i * 4] * 299 + data[i * 4 + 1] * 587 + data[i * 4 + 2] * 114) / 1000
  return gray
}

function fromGray(gray: Float32Array, image: ImageData) {
  const data = image.data
  for (let i = 0; i < gray.length; i++) {
    data[i * 4] = data[i * 4 + 1] = data[i * 4 + 2] = Math.max(0, Math.min(255, gray[i]))
    data[i * 4 + 3] = 255
  }
}

/** Box blur along one axis: `step` is 1 for rows and the width for columns. */
function blurLine(src: Float32Array, dst: Float32Array, start: number, count: number, step: number, radius: number) {
  let sum = 0
  for (let i = -radius; i <= radius; i++) sum += src[start + Math.min(Math.max(i, 0), count - 1) * step]
  for (let i = 0; i < count; i++) {
    dst[start + i * step] = sum / (2 * radius + 1)
    sum += src[start + Math.min(i + radius + 1, count - 1) * step] - src[start + Math.max(i - radius, 0) * step]
  }
}

/** Sharpens blurry modules of an enlarged photo: gray + 1.5 * (gray - blurred). */
function unsharp(gray: Float32Array, width: number, height: number, radius: number) {
  const tmp = new Float32Array(gray.length)
  const blurred = new Float32Array(gray.length)
  for (let y = 0; y < height; y++) blurLine(gray, tmp, y * width, width, 1, radius)
  for (let x = 0; x < width; x++) blurLine(tmp, blurred, x, height, width, radius)
  for (let i = 0; i < gray.length; i++) gray[i] += 1.5 * (gray[i] - blurred[i])
}

/** Stretches brightness between the 2nd and 98th percentiles, then thresholds in the middle. */
function stretchContrast(gray: Float32Array) {
  const histogram = new Uint32Array(256)
  for (const value of gray) histogram[Math.min(255, Math.max(0, Math.round(value)))]++
  const percentile = (share: number) => {
    let sum = 0
    for (let level = 0; level < 256; level++) {
      sum += histogram[level]
      if (sum >= gray.length * share) return level
    }
    return 255
  }
  const middle = (percentile(0.02) + percentile(0.98)) / 2
  for (let i = 0; i < gray.length; i++) gray[i] = gray[i] < middle ? 0 : 255
}

async function paymentCode(image: ImageData): Promise<string | null> {
  readerPromise ??= loadReader()
  const readBarcodes = await readerPromise
  const found = await readBarcodes(image, {
    formats: ['QRCode'],
    tryHarder: true,
    tryRotate: true,
    tryInvert: true,
    maxNumberOfSymbols: 8,
  })
  // A receipt carries several codes (service links among them): take the payment one.
  return found.find((code) => parseEpdQr(code.text))?.text ?? null
}

/** Payment QR text in one video frame (a single quick pass), or null. */
export async function decodeQr(source: Source): Promise<string | null> {
  const image = render(source, 1)
  return image ? paymentCode(image) : null
}

/** Payment QR text on a photo: as is, enlarged x2 and x3 (a dense code needs sharpening), then black and white. */
async function decodePhoto(source: Source): Promise<string | null> {
  const attempts: [number, Filter][] = [[1, 'none'], [2, 'none'], [3, 'none'], [3, 'sharpen'], [4, 'sharpen'], [2, 'contrast']]
  for (const [scale, filter] of attempts) {
    const image = render(source, scale, filter)
    const text = image && (await paymentCode(image))
    if (text) return text
  }
  return null
}

/** Payment QR text on a photo chosen from the device. */
export async function decodeQrFile(file: File): Promise<string | null> {
  const url = URL.createObjectURL(file)
  try {
    const image = new Image()
    image.src = url
    await image.decode()
    return await decodePhoto(image)
  } finally {
    URL.revokeObjectURL(url)
  }
}
