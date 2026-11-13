import { useState } from 'react'
import { MapPin } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { FormField } from '@/components/form-field'
import { useMe } from '@/features/auth/hooks'
import { AddressSearch } from '@/features/houses/components/address-search'
import { StepLayout } from '../step-layout'
import type { IssueLocation, StepProps } from '../../wizard'

const LOCATION_FIELDS = [
  { key: 'entrance', label: 'Подъезд', placeholder: '2' },
  { key: 'floor', label: 'Этаж', placeholder: '5' },
  { key: 'apartment', label: 'Квартира', placeholder: '34' },
] as const

export function AddressStep({ data, setData, onNext, onBack }: StepProps) {
  const { data: me } = useMe()
  const [changing, setChanging] = useState(false)
  const picked = data.house?.address ?? data.customAddress
  const address = picked ?? me?.house?.address ?? me?.custom_address
  const custom = data.house ? false : data.customAddress != null || (!me?.house && Boolean(me?.custom_address))
  const showSearch = changing || !address
  const setLocation = (key: keyof IssueLocation, value: string) =>
    setData((d) => ({ ...d, location: { ...d.location, [key]: value } }))

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
      <fieldset className="grid gap-3">
        <legend className="mb-1 text-sm font-medium">
          Где именно <span className="font-normal text-muted-foreground">— по желанию</span>
        </legend>
        <div className="grid grid-cols-3 gap-3">
          {LOCATION_FIELDS.map((f) => (
            <FormField key={f.key} label={f.label} htmlFor={`location-${f.key}`}>
              <Input
                id={`location-${f.key}`}
                inputMode="numeric"
                maxLength={8}
                value={data.location[f.key]}
                onChange={(e) => setLocation(f.key, e.target.value)}
                placeholder={f.placeholder}
              />
            </FormField>
          ))}
        </div>
        <FormField label="Место" htmlFor="location-place">
          <Input
            id="location-place"
            maxLength={200}
            value={data.location.place}
            onChange={(e) => setLocation('place', e.target.value)}
            placeholder="Например: у лифта, во дворе у детской площадки"
          />
        </FormField>
      </fieldset>
    </StepLayout>
  )
}
