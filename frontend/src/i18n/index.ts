import i18n, { type Resource } from 'i18next'
import { initReactI18next } from 'react-i18next'
import en from './en.json'
import { availableLanguages, pickLanguage } from './languages'
import ru from './ru.json'

// Build flag (spec 7.5): VITE_ENABLE_KK=true. Without it the Kazakh file is not even
// part of the bundle, because the bundler drops the unreachable import below.
const KK_ENABLED = import.meta.env.VITE_ENABLE_KK === 'true'
export const LANGUAGES = availableLanguages(KK_ENABLED)

const resources: Resource = { en: { translation: en }, ru: { translation: ru } }
if (import.meta.env.VITE_ENABLE_KK === 'true') {
  resources.kk = { translation: (await import('./kk.json')).default }
}

const STORAGE_KEY = 'neomortalsurv.lang'

function readStored(): string | null {
  try {
    return window.localStorage.getItem(STORAGE_KEY)
  } catch {
    return null
  }
}

export function rememberLanguage(lang: string): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, lang)
  } catch {
    // private mode or blocked storage: the choice lasts for this page only
  }
}

const initial = pickLanguage(
  LANGUAGES.map((l) => l.code),
  window.location.search,
  readStored(),
  window.navigator.languages ?? [],
)

void i18n.use(initReactI18next).init({
  resources,
  lng: initial,
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
})
document.documentElement.lang = initial
i18n.on('languageChanged', (lng) => {
  document.documentElement.lang = lng
})

export default i18n
