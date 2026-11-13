export const percent = (share: number | null | undefined) => (share == null ? '—' : `${Math.round(share * 100)}%`)
