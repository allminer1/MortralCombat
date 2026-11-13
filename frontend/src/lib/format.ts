/** Headline numbers: whole percent (spec 7.3). */
export const percent0 = (fraction: number, lang: string): string =>
  new Intl.NumberFormat(lang, { style: 'percent', maximumFractionDigits: 0 }).format(fraction)

/** Details and curve read-out: one decimal. */
export const percent1 = (fraction: number, lang: string): string =>
  new Intl.NumberFormat(lang, {
    style: 'percent',
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }).format(fraction)

export const fixed3 = (value: number, lang: string): string =>
  new Intl.NumberFormat(lang, { minimumFractionDigits: 3, maximumFractionDigits: 3 }).format(value)
