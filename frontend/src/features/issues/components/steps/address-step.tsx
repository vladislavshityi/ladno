import { useState } from 'react'
import { MapPin } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { FormField } from '@/components/form-field'
import { useMe } from '@/features/auth/hooks'
import { AddressSearch } from '@/features/houses/components/address-search'
import { StepLayout } from '../step-layout'
import type { StepProps } from '../../wizard'

export function AddressStep({ data, setData, onNext, onBack }: StepProps) {
  const { data: me } = useMe()
  const [changing, setChanging] = useState(false)
  const picked = data.house?.address ?? data.customAddress
  const address = picked ?? me?.house?.address ?? me?.custom_address
  const custom = data.house ? false : data.customAddress != null || (!me?.house && Boolean(me?.custom_address))
  const showSearch = changing || !address

  return (
    <StepLayout
      title="Где это произошло?"
      description="По адресу определим управляющую компанию."
      onBack={onBack}
      onNext={onNext}
      nextDisabled={!address}
    >
      {showSearch ? (
        <AddressSearch
          autoFocus
          onSelect={(house) => {
            setData((d) => ({ ...d, house, customAddress: null }))
            setChanging(false)
          }}
          onCustom={(customAddress) => {
            setData((d) => ({ ...d, house: null, customAddress }))
            setChanging(false)
          }}
        />
      ) : (
        <div className="flex items-center gap-3 rounded-xl bg-muted/60 p-3">
          <MapPin className="size-4 shrink-0 text-primary" />
          <div className="min-w-0 flex-1">
            <p className="font-medium">{address}</p>
            <p className="text-xs text-muted-foreground">{custom ? 'Указан вами' : picked ? 'Выбран для этого обращения' : 'Из вашего профиля'}</p>
          </div>
          <Button variant="outline" size="sm" onClick={() => setChanging(true)}>
            Изменить
          </Button>
        </div>
      )}
      <FormField label="Где именно" htmlFor="location" hint="Подъезд, этаж, место — по желанию">
        <Input
          id="location"
          value={data.location}
          maxLength={300}
          onChange={(e) => setData((d) => ({ ...d, location: e.target.value }))}
          placeholder="Например: 2 подъезд, 3 этаж"
        />
      </FormField>
    </StepLayout>
  )
}
