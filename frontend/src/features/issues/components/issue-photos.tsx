import type { Issue } from '@/types/models'
import { AuthedImage } from './authed-image'

export function IssuePhotos({ photos }: { photos: Issue['photos'] }) {
  if (photos.length === 0) return null
  return (
    <div className="flex flex-wrap gap-3">
      {photos.map((p, i) => (
        <AuthedImage key={p.id} url={p.url} alt={`Фото ${i + 1}`} className="size-28 rounded-xl object-cover ring-1 ring-border" />
      ))}
    </div>
  )
}
