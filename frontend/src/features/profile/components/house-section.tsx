import { useState } from 'react'
import { Loader2, MapPin } from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { FormField } from '@/components/form-field'
import { AddressSearch } from '@/features/houses/components/address-search'
import type { User } from '@/types/models'
import { useUpdateProfile } from '../hooks'
import { toProfileUpdate } from '../profile-update'

export function HouseSection({ me }: { me: User }) {
  const update = useUpdateProfile()
  const address = me.house?.address ?? me.custom_address
  const [changing, setChanging] = useState(!address)
  const [entrance, setEntrance] = useState(me.entrance ?? '')

  const save = (changes: Parameters<typeof toProfileUpdate>[1], message: string) =>
    update.mutate(toProfileUpdate(me, changes), { onSuccess: () => toast.success(message) })

  return (
    <Card className="rounded-2xl border-0 shadow-sm ring-1 ring-border">
      <CardHeader>
        <CardTitle>Адрес дома</CardTitle>
        <CardDescription>Нужен, чтобы подставлять адрес и управляющую компанию в обращения.</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        {address && !changing && (
          <div className="flex items-start gap-3 rounded-xl bg-muted/60 p-3">
            <MapPin className="mt-0.5 size-4 shrink-0 text-primary" />
            <div className="min-w-0 flex-1">
              <p className="font-medium">{address}</p>
              {me.house?.district && <p className="text-sm text-muted-foreground">{me.house.district}</p>}
              {!me.house && (
                <Badge variant="secondary" className="mt-1 font-normal">
                  Указан вами
                </Badge>
              )}
            </div>
            <Button variant="outline" size="sm" onClick={() => setChanging(true)}>
              Изменить
            </Button>
          </div>
        )}
        {changing && (
          <AddressSearch
            autoFocus={Boolean(address)}
            onSelect={(a) => {
              // A new house brings its own management company, so the old override is dropped.
              save({ house_id: a.house_id, custom_address: null, management_company_id: null, custom_company_name: null }, 'Адрес сохранён')
              setChanging(false)
            }}
            onCustom={(text) => {
              save({ house_id: null, custom_address: text, management_company_id: null, custom_company_name: null }, 'Адрес сохранён')
              setChanging(false)
            }}
          />
        )}
        {address && (
          <form
            className="flex items-end gap-2"
            onSubmit={(e) => {
              e.preventDefault()
              save({ entrance: entrance.trim() || null }, 'Подъезд сохранён')
            }}
          >
            <FormField label="Подъезд" htmlFor="entrance">
              <Input id="entrance" value={entrance} onChange={(e) => setEntrance(e.target.value)} maxLength={8} className="w-28" inputMode="numeric" />
            </FormField>
            <Button type="submit" variant="secondary" size="lg" disabled={update.isPending || entrance === (me.entrance ?? '')}>
              {update.isPending && <Loader2 className="animate-spin" />}
              Сохранить
            </Button>
          </form>
        )}
      </CardContent>
    </Card>
  )
}
