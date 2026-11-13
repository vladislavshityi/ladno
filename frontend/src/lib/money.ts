const rub = new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', minimumFractionDigits: 2 })
const num = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 3 })

/** The API sends money as decimal strings. */
export const formatMoney = (v: string | number | null | undefined) => (v == null ? '—' : rub.format(Number(v)))

export const formatNumber = (v: string | number | null | undefined) => (v == null ? '—' : num.format(Number(v)))

export const formatSigned = (v: string | number) => {
  const n = Number(v)
  return `${n > 0 ? '+' : ''}${rub.format(n)}`
}
