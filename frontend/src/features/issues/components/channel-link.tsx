import { ArrowUpRight, Globe, Mail, MessageSquare, Phone, Send } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { openExternal } from '@/lib/telegram'
import type { RouteResult } from '@/types/models'

type Channel = RouteResult['addressee']['channels'][number]

const ICONS = { phone: Phone, email: Mail, url: Globe, pos: MessageSquare, gis_zhkh: Globe, telegram: Send }

/** A contact of the addressee: clearly a button — call, write or open the site. */
export function ChannelLink({ channel }: { channel: Channel }) {
  const Icon = ICONS[channel.type]
  const content = (
    <>
      <Icon />
      <span>{channel.label}</span>
      {channel.type === 'phone' || channel.type === 'email' ? (
        <span className="font-normal text-muted-foreground">{channel.value}</span>
      ) : (
        <ArrowUpRight className="text-muted-foreground" />
      )}
    </>
  )
  if (channel.type === 'phone') {
    return (
      <Button variant="outline" asChild>
        <a href={`tel:${channel.value.replace(/[^\d+]/g, '')}`}>{content}</a>
      </Button>
    )
  }
  if (channel.type === 'email') {
    return (
      <Button variant="outline" asChild>
        <a href={`mailto:${channel.value}`}>{content}</a>
      </Button>
    )
  }
  return (
    <Button variant="outline" onClick={() => openExternal(channel.value)}>
      {content}
    </Button>
  )
}
