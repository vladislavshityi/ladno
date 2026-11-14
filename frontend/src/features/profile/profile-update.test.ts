import { describe, expect, it } from 'vitest'
import type { User } from '@/types/models'
import { toProfileUpdate } from './profile-update'

const me = {
  house: null,
  custom_address: 'г Владивосток, ул Новая, д 1',
  management_company: null,
  custom_company_name: 'ТСЖ «Новое»',
  entrance: '2',
  full_name: null,
  phone: null,
  email: null,
  apartment: '12',
} as unknown as User

describe('toProfileUpdate', () => {
  it('keeps manual address and company when saving other fields', () => {
    const update = toProfileUpdate(me, { phone: '+79990001122' })
    expect(update).toMatchObject({
      house_id: null,
      custom_address: 'г Владивосток, ул Новая, д 1',
      management_company_id: null,
      custom_company_name: 'ТСЖ «Новое»',
      phone: '+79990001122',
    })
  })

  it('drops saved values the server would reject', () => {
    const update = toProfileUpdate({ ...me, full_name: 'Иванов', phone: '123', apartment: '12а', email: 'A@B.RU' } as User)
    expect(update).toMatchObject({ full_name: null, phone: null, apartment: '12а', email: 'a@b.ru' })
  })

  it('lets a chosen house replace the manual address', () => {
    const update = toProfileUpdate(me, { house_id: 5, custom_address: null })
    expect(update.house_id).toBe(5)
    expect(update.custom_address).toBeNull()
  })
})
