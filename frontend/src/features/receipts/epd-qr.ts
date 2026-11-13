/** Payment-document QR code (GOST R 56042-2014): `ST00012|Name=...|PayeeINN=...|Sum=123456|...`. */

export interface EpdQr {
  /** Amount in rubles, e.g. "1234.56". */
  total: string | null
  /** YYYY-MM */
  period: string | null
  inn: string | null
  /** Payee name. */
  name: string | null
  /** Only the last four digits of the personal account are ever kept. */
  accountLast4: string | null
}

// Format id (ST0001 or ST0002), encoding digit (1 win-1251, 2 UTF-8, 3 KOI8-R), then the separator.
const FORMAT_ID = /^ST000[12][123]/

/** Kopecks ("123456") to rubles ("1234.56"). */
function kopecksToRubles(value: string | undefined): string | null {
  if (!value || !/^\d+$/.test(value)) return null
  const padded = value.padStart(3, '0')
  const rubles = padded.slice(0, -2).replace(/^0+(?=\d)/, '')
  return `${rubles}.${padded.slice(-2)}`
}

/** "MMYYYY", "MM.YYYY" and similar to "YYYY-MM". */
function toPeriod(value: string | undefined): string | null {
  const match = value?.trim().match(/^(\d{2})\D?(\d{4})$/)
  if (!match) return null
  const month = Number(match[1])
  return month >= 1 && month <= 12 ? `${match[2]}-${match[1]}` : null
}

/** Returns null when the text is not a payment-document QR code. */
export function parseEpdQr(raw: string): EpdQr | null {
  const text = raw.trim()
  if (!FORMAT_ID.test(text)) return null
  const fields = new Map<string, string>()
  for (const part of text.slice(8).split(text[7])) {
    const at = part.indexOf('=')
    if (at > 0) fields.set(part.slice(0, at).trim().toLowerCase(), part.slice(at + 1).trim())
  }
  const account = fields.get('persacc')?.replace(/\D/g, '') ?? ''
  const inn = fields.get('payeeinn')
  return {
    total: kopecksToRubles(fields.get('sum')),
    period: toPeriod(fields.get('paymperiod')),
    inn: inn && /^\d{10}(\d{2})?$/.test(inn) ? inn : null,
    name: fields.get('name') || null,
    accountLast4: account.slice(-4) || null,
  }
}
