import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import en from './en.json'
import ru from './ru.json'

// `kk` joins in Phase 4, behind a build flag until a clinician has reviewed it.
export const LANGUAGES = [
  { code: 'en', name: 'English' },
  { code: 'ru', name: 'Русский' },
] as const
export type Language = (typeof LANGUAGES)[number]['code']

const STORAGE_KEY = 'neomortalsurv.lang'
const isLanguage = (v: string | null | undefined): v is Language =>
  LANGUAGES.some((l) => l.code === v)

/** `?lang=` wins, then the remembered choice, then the browser language, then English. */
export function pickLanguage(search: string, stored: string | null, browser: readonly string[]): Language {
  const fromUrl = new URLSearchParams(search).get('lang')?.toLowerCase()
  if (isLanguage(fromUrl)) return fromUrl
  if (isLanguage(stored)) return stored
  for (const tag of browser) {
    const base = tag.toLowerCase().split('-')[0]
    if (isLanguage(base)) return base
  }
  return 'en'
}

function readStored(): string | null {
  try {
    return window.localStorage.getItem(STORAGE_KEY)
  } catch {
    return null
  }
}

export function rememberLanguage(lang: Language): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, lang)
  } catch {
    // private mode or blocked storage: the choice lasts for this page only
  }
}

const initial = pickLanguage(window.location.search, readStored(), window.navigator.languages ?? [])

void i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, ru: { translation: ru } },
  lng: initial,
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
})
document.documentElement.lang = initial
i18n.on('languageChanged', (lng) => {
  document.documentElement.lang = lng
})

export default i18n
