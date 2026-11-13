import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useLocation } from 'react-router'
import { LANGUAGES } from '../i18n'

const SITE = (import.meta.env.VITE_SITE_URL as string | undefined) ?? window.location.origin
/** Pages a search engine should list. Everything else (report, sign-in, history) is
 *  personal or empty without a calculation and is marked noindex. */
const INDEXED: Record<string, 'home' | 'about'> = { '/': 'home', '/about': 'about' }
const OTHER: [RegExp, string][] = [
  [/^\/report/, 'report'],
  [/^\/login/, 'login'],
  [/^\/history/, 'history'],
]

function setMeta(selector: string, create: () => HTMLElement, attribute: string, value: string | null): void {
  let node = document.head.querySelector<HTMLElement>(selector)
  if (value === null) {
    node?.remove()
    return
  }
  if (!node) {
    node = create()
    document.head.appendChild(node)
  }
  node.setAttribute(attribute, value)
}

const meta = (key: 'name' | 'property', id: string) => () => {
  const node = document.createElement('meta')
  node.setAttribute(key, id)
  return node
}
const link = (rel: string, hreflang?: string) => () => {
  const node = document.createElement('link')
  node.setAttribute('rel', rel)
  if (hreflang) node.setAttribute('hreflang', hreflang)
  return node
}

/** Keeps the title, description, canonical link, language alternates and robots tag in
 *  step with the page and language on screen. Renders nothing. */
export function DocumentHead() {
  const { t, i18n } = useTranslation()
  const { pathname } = useLocation()
  const lang = i18n.resolvedLanguage ?? 'en'

  useEffect(() => {
    const indexed = INDEXED[pathname]
    const page = indexed ?? OTHER.find(([pattern]) => pattern.test(pathname))?.[1] ?? 'home'
    const title = t(`seo.${page}.title`)
    const description = t(`seo.${indexed ?? 'home'}.description`)
    const url = `${SITE}${pathname}${lang === 'en' ? '' : `?lang=${lang}`}`

    document.title = title
    setMeta('meta[name="description"]', meta('name', 'description'), 'content', description)
    setMeta('meta[property="og:title"]', meta('property', 'og:title'), 'content', title)
    setMeta('meta[property="og:description"]', meta('property', 'og:description'), 'content', description)
    setMeta('meta[property="og:url"]', meta('property', 'og:url'), 'content', url)
    setMeta('meta[name="robots"]', meta('name', 'robots'), 'content', indexed ? null : 'noindex')
    setMeta('link[rel="canonical"]', link('canonical'), 'href', indexed ? url : null)

    document.head.querySelectorAll('link[rel="alternate"][hreflang]').forEach((node) => node.remove())
    if (indexed) {
      for (const { code } of LANGUAGES) {
        setMeta(`link[rel="alternate"][hreflang="${code}"]`, link('alternate', code), 'href', `${SITE}${pathname}?lang=${code}`)
      }
      setMeta('link[rel="alternate"][hreflang="x-default"]', link('alternate', 'x-default'), 'href', `${SITE}${pathname}`)
    }
  }, [pathname, lang, t])

  return null
}
