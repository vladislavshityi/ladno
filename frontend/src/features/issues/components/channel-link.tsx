import { Globe, Mail, MessageSquare, Phone, Send } from 'lucide-react'
import { openExternal } from '@/lib/telegram'
import type { RouteResult } from '@/types/models'

type Channel = RouteResult['addressee']['channels'][number]

const ICONS = { phone: Phone, email: Mail, url: Globe, pos: MessageSquare, gis_zhkh: Globe, telegram: Send }

const rowClass =
  'inline-flex items-center gap-2 rounded-full bg-muted px-3 py-1.5 text-sm transition-colors hover:bg-accent focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none'

export function ChannelLink({ channel }: { channel: Channel }) {
  const Icon = ICONS[channel.type]
  const content = (
    <>
      <Icon className="size-3.5 text-muted-foreground" />
      <span>{channel.label}</span>
      {channel.type === 'phone' || channel.type === 'email' ? (
        <span className="text-muted-foreground">{channel.value}</span>
      ) : null}
    </>
  )
  if (channel.type === 'phone') {
    return <a className={rowClass} href={`tel:${channel.value.replace(/[^\d+]/g, '')}`}>{content}</a>
  }
  if (channel.type === 'email') {
    return <a className={rowClass} href={`mailto:${channel.value}`}>{content}</a>
  }
  return (
    <button type="button" className={rowClass} onClick={() => openExternal(channel.value)}>
      {content}
    </button>
  )
}
