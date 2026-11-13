import { useState } from 'react'
import { Building2, ExternalLink, Mail, Phone, Siren } from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { CompanyPicker } from '@/features/houses/components/company-picker'
import { openExternal } from '@/lib/telegram'
import type { ManagementCompany, User } from '@/types/models'
import { useUpdateProfile } from '../hooks'
import { toProfileUpdate } from '../profile-update'

const SOURCE_LABELS: Record<NonNullable<ManagementCompany['source']>, string> = {
  gis_zhkh: 'По данным ГИС ЖКХ',
  vl_ru: 'По данным VL.ru',
}

export function CompanySection({ me }: { me: User }) {
  const update = useUpdateProfile()
  const [picking, setPicking] = useState(false)

  const save = (changes: Parameters<typeof toProfileUpdate>[1]) => {
    update.mutate(toProfileUpdate(me, changes), { onSuccess: () => toast.success('Компания сохранена') })
    setPicking(false)
  }
  const company = me.management_company
  const hasAddress = Boolean(me.house ?? me.custom_address)

  return (
    <Card className="rounded-2xl border-0 shadow-sm ring-1 ring-border">
      <CardHeader>
        <CardTitle>Управляющая компания</CardTitle>
        <CardDescription>Ей адресуются обращения по дому и заявления на перерасчёт.</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3">
        {company ? (
          <div className="flex items-start gap-3 rounded-xl bg-muted/60 p-3">
            <Building2 className="mt-0.5 size-4 shrink-0 text-primary" />
            <div className="min-w-0 flex-1 space-y-1.5">
              <p className="font-medium">{company.name}</p>
              <Badge variant="secondary" className="font-normal">
                {company.source ? SOURCE_LABELS[company.source] : 'Выбрана вами'}
              </Badge>
              <ul className="space-y-1 pt-1 text-sm text-muted-foreground">
                {company.phones.length > 0 && (
                  <li className="flex items-center gap-2"><Phone className="size-3.5" />{company.phones.join(', ')}</li>
                )}
                {company.emergency_phone && (
                  <li className="flex items-center gap-2"><Siren className="size-3.5" />Аварийная: {company.emergency_phone}</li>
                )}
                {company.email && <li className="flex items-center gap-2"><Mail className="size-3.5" />{company.email}</li>}
                {company.site && (
                  <li>
                    <button type="button" className="flex items-center gap-2 hover:text-foreground hover:underline" onClick={() => openExternal(company.site!)}>
                      <ExternalLink className="size-3.5" />Сайт
                    </button>
                  </li>
                )}
              </ul>
            </div>
          </div>
        ) : me.custom_company_name ? (
          <div className="flex items-start gap-3 rounded-xl bg-muted/60 p-3">
            <Building2 className="mt-0.5 size-4 shrink-0 text-primary" />
            <div className="min-w-0 flex-1 space-y-1.5">
              <p className="font-medium">{me.custom_company_name}</p>
              <Badge variant="secondary" className="font-normal">
                Указана вами
              </Badge>
              <p className="pt-1 text-sm text-muted-foreground">Контакты не найдены в справочнике, уточните у соседей или на сайте УК.</p>
            </div>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">
            {hasAddress ? 'Для этого дома компания не определена — выберите её вручную.' : 'Сначала выберите дом, мы подставим компанию.'}
          </p>
        )}
        <Button variant="outline" className="justify-self-start" onClick={() => setPicking(true)}>
          Изменить УК
        </Button>
      </CardContent>
      <CompanyPicker
        open={picking}
        onOpenChange={setPicking}
        onSelect={(c) => {
          save({ management_company_id: c.id, custom_company_name: null })
        }}
        onCustom={(name) => save({ management_company_id: null, custom_company_name: name })}
      />
    </Card>
  )
}
