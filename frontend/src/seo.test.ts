import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import en from './i18n/en.json'

const read = (path: string) => readFileSync(new URL(path, import.meta.url), 'utf-8')
const html = read('../index.html')
const card = JSON.parse(read('../../model/model_card.json'))
const SITE = 'https://neomortalsurv.net'

describe('static page head', () => {
  it('carries the English title and description of the translation file', () => {
    expect(html).toContain(`<title>${en.seo.home.title}</title>`)
    expect(html).toContain(`<meta name="description" content="${en.seo.home.description}" />`)
    expect(html).toContain(`<meta property="og:title" content="${en.seo.home.title}" />`)
  })
  it('keeps titles and descriptions within what search results show', () => {
    for (const page of [en.seo.home, en.seo.about]) {
      expect(page.title.length).toBeLessThanOrEqual(80)
      expect(page.description.length).toBeGreaterThanOrEqual(110)
      expect(page.description.length).toBeLessThanOrEqual(200)
    }
  })
  it('describes the tool and cites the article as the model card does', () => {
    const block = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)
    const data = JSON.parse(block![1].replaceAll('%VITE_SITE_URL%', SITE))
    expect(data['@type']).toBe('WebApplication')
    expect(data.applicationCategory).toBe('HealthApplication')
    expect(data.url).toBe(`${SITE}/`)
    expect(data.citation.headline).toBe(card.citation.title)
    expect(data.citation.identifier).toBe(`doi:${card.citation.doi}`)
    expect(html).toContain(`doi:${card.citation.doi}`)
    expect(html).toContain(card.citation.authors.replace(/\s+/g, ' ').slice(0, 40))
  })
  it('loads nothing from another site', () => {
    const sources = [...html.matchAll(/(?:src|href)="(https?:[^"]+)"/g)].map((m) => m[1])
    // the DOI link is a link for the reader, not something the page loads
    expect(sources.filter((u) => !u.startsWith('https://doi.org/'))).toEqual([])
  })
})

describe('robots.txt and sitemap.xml', () => {
  const robots = read('../public/robots.txt')
  const sitemap = read('../public/sitemap.xml')
  it('point at the site and do not block the API the page needs', () => {
    expect(robots).toContain(`Sitemap: ${SITE}/sitemap.xml`)
    expect(robots).not.toMatch(/Disallow:\s*\/api/)
  })
  it('list the calculator and the About page in three languages, and nothing personal', () => {
    const locs = [...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => m[1])
    const expected = ['/', '/about'].flatMap((p) => ['en', 'ru', 'kk'].map((l) => `${SITE}${p}?lang=${l}`))
    expect(locs).toEqual(expected)
    expect(sitemap).not.toMatch(/report|login|history/)
  })
})
