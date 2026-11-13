/** Kazakh numbers are written like Russian ones (decimal comma, space before %), and
 *  not every browser ships Kazakh rules: some claim to and then print English forms.
 *  Numbers therefore always use the Russian rules for Kazakh. */
const NUMBER_LOCALE: Record<string, string> = { kk: 'ru' }
export const locale = (lang: string): string => NUMBER_LOCALE[lang] ?? lang

/** Dates: Kazakh month names when the browser really has them, Russian otherwise. */
function dateLocale(lang: string): string {
  if (lang !== 'kk') return lang
  const month = (l: string) => new Intl.DateTimeFormat(l, { month: 'long', timeZone: 'UTC' }).format(new Date(Date.UTC(2021, 0, 1)))
  return month('kk') === month('en') ? 'ru' : 'kk'
}

/** Headline numbers: whole percent (spec 7.3). */
export const percent0 = (fraction: number, lang: string): string =>
  new Intl.NumberFormat(locale(lang), { style: 'percent', maximumFractionDigits: 0 }).format(fraction)

/** Details and curve read-out: one decimal. */
export const percent1 = (fraction: number, lang: string): string =>
  new Intl.NumberFormat(locale(lang), {
    style: 'percent',
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }).format(fraction)

export const fixed3 = (value: number, lang: string): string =>
  new Intl.NumberFormat(locale(lang), { minimumFractionDigits: 3, maximumFractionDigits: 3 }).format(value)

export const decimal = (value: number, digits: number, lang: string): string =>
  new Intl.NumberFormat(locale(lang), { minimumFractionDigits: digits, maximumFractionDigits: digits }).format(value)

export const integer = (value: number, lang: string): string => new Intl.NumberFormat(locale(lang)).format(value)

export const dateTime = (when: Date, lang: string): string =>
  new Intl.DateTimeFormat(dateLocale(lang), { dateStyle: 'long', timeStyle: 'short' }).format(when)

/** "2021-01 to 2025-05" (model card) -> "January 2021 – May 2025" in the interface language. */
export function monthRange(period: string, lang: string): string {
  const months = [...period.matchAll(/(\d{4})-(\d{2})/g)].map(([, y, m]) => new Date(Date.UTC(Number(y), Number(m) - 1, 1)))
  if (months.length !== 2) return period
  const format = new Intl.DateTimeFormat(dateLocale(lang), { month: 'long', year: 'numeric', timeZone: 'UTC' })
  return `${format.format(months[0])} – ${format.format(months[1])}`
}
