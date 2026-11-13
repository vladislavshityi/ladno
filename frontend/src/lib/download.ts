/** Saves a blob through a temporary link; works in regular browsers (Telegram webviews may ignore it).
 *  A name without an extension gets one from the blob type (image/jpeg -> jpg). */
export function saveBlob(blob: Blob, filename: string) {
  if (!filename.includes('.')) filename += `.${blob.type.split('/')[1]?.replace('jpeg', 'jpg') ?? 'bin'}`
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.append(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 10_000)
}
