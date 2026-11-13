import { Skeleton } from '@/components/ui/skeleton'
import { useAuthedImage } from '../hooks'

export function AuthedImage({ url, alt, className }: { url: string; alt: string; className?: string }) {
  const src = useAuthedImage(url)
  return src ? <img src={src} alt={alt} className={className} /> : <Skeleton className={className} />
}
