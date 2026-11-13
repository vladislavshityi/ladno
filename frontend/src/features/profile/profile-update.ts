import type { ProfileUpdate, User } from '@/types/models'

/** The profile endpoint replaces the whole profile, so every save starts from the current values. */
export function toProfileUpdate(me: User, changes: Partial<ProfileUpdate> = {}): ProfileUpdate {
  return {
    house_id: me.house?.id ?? null,
    custom_address: me.custom_address,
    entrance: me.entrance,
    full_name: me.full_name,
    phone: me.phone,
    email: me.email,
    apartment: me.apartment,
    management_company_id: me.management_company?.id ?? null,
    custom_company_name: me.custom_company_name,
    ...changes,
  }
}
