/** Language list and choice. Kept free of browser globals so that it can be unit-tested. */
export interface LanguageOption {
  code: string
  name: string
}

/** Kazakh is a draft awaiting clinical review: listed only when the build flag is on. */
export function availableLanguages(kkEnabled: boolean): LanguageOption[] {
  const base = [
    { code: 'en', name: 'English' },
    { code: 'ru', name: 'Русский' },
  ]
  return kkEnabled ? [...base, { code: 'kk', name: 'Қазақша' }] : base
}

/** `?lang=` wins, then the remembered choice, then the browser language, then English. */
export function pickLanguage(
  allowed: readonly string[],
  search: string,
  stored: string | null,
  browser: readonly string[],
): string {
  const ok = (v: string | null | undefined): v is string => !!v && allowed.includes(v)
  const fromUrl = new URLSearchParams(search).get('lang')?.toLowerCase()
  if (ok(fromUrl)) return fromUrl
  if (ok(stored)) return stored
  for (const tag of browser) {
    const base = tag.toLowerCase().split('-')[0]
    if (ok(base)) return base
  }
  return 'en'
}
