import { checkAddress, checkApartment, checkCompanyName, checkEmail, checkEntrance, checkFullName, checkPhone, type Checked } from '@/lib/validation'
import type { ProfileUpdate, User } from '@/types/models'

/** A saved value the server would now reject (older, looser data) is left out instead of blocking every save. */
const kept = (value: string | null, check: (raw: string) => Checked) => {
  const result = check(value ?? '')
  return result.ok ? result.value : null
}

/** The profile endpoint replaces the whole profile, so every save starts from the current values. */
export function toProfileUpdate(me: User, changes: Partial<ProfileUpdate> = {}): ProfileUpdate {
  return {
    house_id: me.house?.id ?? null,
    custom_address: kept(me.custom_address, checkAddress),
    entrance: kept(me.entrance, checkEntrance),
    full_name: kept(me.full_name, checkFullName),
    phone: kept(me.phone, checkPhone),
    email: kept(me.email, checkEmail),
    apartment: kept(me.apartment, checkApartment),
    management_company_id: me.management_company?.id ?? null,
    custom_company_name: kept(me.custom_company_name, checkCompanyName),
    ...changes,
  }
}
