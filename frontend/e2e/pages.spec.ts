import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'
import { openReport, pdfPageCount } from './helpers'

const WCAG = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']

for (const lang of ['en', 'ru']) {
  test(`report prints on one A4 page, ${lang}`, async ({ page }) => {
    await openReport(page, lang)
    const pdf = await page.pdf({ preferCSSPageSize: true, printBackground: true })
    expect(pdfPageCount(pdf)).toBe(1)
  })

  test(`report still fits one page with the weight warning, ${lang}`, async ({ page }) => {
    await page.goto(`/?lang=${lang}`)
    const { fillFigure8 } = await import('./helpers')
    await fillFigure8(page)
    await page.locator('#birth_weight_g').fill('1600')
    await page.locator('button[type=submit]').click()
    await page.getByTestId('result').waitFor()
    await page.locator('a[href="/report"]').click()
    await expect(page.getByTestId('report-warnings')).toContainText('1')
    expect(pdfPageCount(await page.pdf({ preferCSSPageSize: true, printBackground: true }))).toBe(1)
  })

  test(`report and about pages pass the accessibility scan, ${lang}`, async ({ page }) => {
    await openReport(page, lang)
    expect((await new AxeBuilder({ page }).withTags(WCAG).analyze()).violations).toEqual([])
    await page.locator('a[href="/about"]').click()
    await page.getByTestId('about-total').waitFor()
    expect((await new AxeBuilder({ page }).withTags(WCAG).analyze()).violations).toEqual([])
  })
}

test('report shows the inputs, estimates, model version, limitations and citation', async ({ page }) => {
  await openReport(page, 'en')
  const sheet = page.getByTestId('report-sheet')
  const inputs = page.getByTestId('report-inputs')
  await expect(inputs.locator('dt')).toHaveCount(11)
  await expect(inputs).toContainText('Birth weight900 g')
  await expect(inputs).toContainText('Gestational age27 weeks')
  await expect(inputs).toContainText('Respiratory failure gradeIII')
  await expect(inputs).toContainText('Necrotising enterocolitis (NEC)Yes')
  const estimates = page.getByTestId('report-estimates')
  await expect(estimates).toContainText('Day 765.2%')
  await expect(estimates).toContainText('Day 2839.5%')
  await expect(estimates).toContainText('Day 1005.6%')
  await expect(estimates).toContainText('1.210')
  await expect(estimates).toContainText('deepsurv-vlbw-1.0.0')
  await expect(page.getByTestId('report-warnings')).toHaveText('None')
  await expect(page.getByTestId('report-when')).toContainText(String(new Date().getFullYear()))
  await expect(sheet.locator('svg path').first()).toBeVisible()
  await expect(sheet).toContainText('Limitations')
  await expect(sheet).toContainText('doi:10.3389/fped.2026.1801840')
  await expect(sheet).toContainText('Case code')
  // No field to type a name, a note or anything else into.
  await expect(page.locator('main input, main textarea, main [contenteditable]')).toHaveCount(0)
})

test('report: inputs stay out of the URL and storage; a direct visit has nothing to show', async ({ page }) => {
  await openReport(page, 'en')
  expect(new URL(page.url()).search).toBe('')
  const stored = await page.evaluate(() => JSON.stringify([{ ...localStorage }, { ...sessionStorage }]))
  expect(stored).not.toContain('900')
  expect(JSON.parse(stored)[1]).toEqual({})

  // Going back keeps the form and the result (same tab, in memory).
  await page.getByRole('link', { name: 'Back to the calculator' }).click()
  await expect(page.locator('#birth_weight_g')).toHaveValue('900')
  await expect(page.getByTestId('headline-day-28')).toHaveText(/^40\s?%$/)

  await page.goto('/report')
  await expect(page.getByText('There is no estimate to print yet.')).toBeVisible()
  await expect(page.getByTestId('report-sheet')).toHaveCount(0)
})

test('print link disappears when the result is out of date', async ({ page }) => {
  await openReport(page, 'en')
  await page.getByRole('link', { name: 'Back to the calculator' }).click()
  await expect(page.locator('a[href="/report"]')).toHaveCount(1)
  await page.locator('input[name=nec][value=no]').check({ force: true })
  await expect(page.locator('a[href="/report"]')).toHaveCount(0)
})

test('/about numbers match spec Section 1 exactly', async ({ page }) => {
  await page.goto('/about?lang=en')
  await expect(page.getByTestId('about-total')).toHaveText('958')
  await expect(page.getByTestId('about-centres')).toHaveText('4')
  await expect(page.getByTestId('about-period')).toHaveText('January 2021 – May 2025')
  await expect(page.getByTestId('about-train')).toHaveText('672')
  await expect(page.getByTestId('about-test')).toHaveText('286')
  await expect(page.getByTestId('about-predictors')).toHaveText('11')
  await expect(page.getByTestId('about-cindex')).toHaveText('0.86 (95% CI 0.81–0.90)')
  await expect(page.getByTestId('about-auc')).toHaveText('0.95 (95% CI 0.91–0.98)')
  await expect(page.getByTestId('about-ibs')).toHaveText('0.071')
  await expect(page.getByRole('article')).toContainText('above 1,500 g')
  await expect(page.getByRole('article')).toContainText('severe congenital malformations')
  await expect(page.getByRole('article')).toContainText('not been validated externally')
  await expect(page.getByRole('article')).toContainText('doi:10.3389/fped.2026.1801840')
})

test('Kazakh is absent from a build made without the flag', async ({ page, request }) => {
  // The deployed stack is built with the flag on; this is about the mechanism itself.
  test.skip(!!process.env.E2E_BASE_URL, 'the compose stack is built with Kazakh enabled')
  await page.goto('/?lang=kk')
  await expect(page.locator('html')).toHaveAttribute('lang', 'en')
  await expect(page.getByRole('button', { name: 'Қазақша' })).toHaveCount(0)
  // ... and the Kazakh text is not shipped at all.
  const html = await (await request.get('/')).text()
  const scripts = [...html.matchAll(/src="([^"]+\.js)"/g)].map((m) => m[1])
  expect(scripts.length).toBeGreaterThan(0)
  for (const src of scripts) expect(await (await request.get(src)).text()).not.toContain('Расталған диагноздар')
})

for (const lang of ['en', 'ru']) {
  for (const width of [375, 768, 1366]) {
    test(`screenshots of report and about, ${lang} ${width}`, async ({ page }) => {
      await page.setViewportSize({ width, height: 900 })
      await openReport(page, lang)
      expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width)
      await page.screenshot({ path: `screenshots/${lang}-${width}-report.png`, fullPage: true })
      await page.locator('a[href="/about"]').click()
      await page.getByTestId('about-total').waitFor()
      expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width)
      await page.screenshot({ path: `screenshots/${lang}-${width}-about.png`, fullPage: true })
    })
  }
}

test('printed report as an image, for review', async ({ page }) => {
  await openReport(page, 'ru')
  await page.emulateMedia({ media: 'print' })
  await page.setViewportSize({ width: 703, height: 1032 }) // A4 minus 12 mm margins at 96 dpi
  await page.screenshot({ path: 'screenshots/ru-print.png', fullPage: true })
})

test('accounts are hidden when the server has them switched off', async ({ page, request }) => {
  expect(await (await request.get('/api/v1/features')).json()).toEqual({ accounts: false })
  await page.goto('/?lang=en')
  await page.locator('button[type=submit]').waitFor()
  await expect(page.getByRole('link', { name: 'Sign in' })).toHaveCount(0)
  await expect(page.getByRole('link', { name: 'History' })).toHaveCount(0)
  for (const path of ['/login', '/history']) {
    await page.goto(path)
    await expect(page).toHaveURL(/\/$/) // unknown here: back to the calculator
  }
  expect((await request.get('/api/v1/auth/me')).status()).toBe(404)
})

// ---- What a search engine sees -------------------------------------------------------

const head = (page: import('@playwright/test').Page) =>
  page.evaluate(() => ({
    title: document.title,
    description: document.querySelector('meta[name="description"]')?.getAttribute('content') ?? null,
    canonical: document.querySelector('link[rel="canonical"]')?.getAttribute('href') ?? null,
    robots: document.querySelector('meta[name="robots"]')?.getAttribute('content') ?? null,
    ogTitle: document.querySelector('meta[property="og:title"]')?.getAttribute('content') ?? null,
    alternates: [...document.querySelectorAll('link[rel="alternate"][hreflang]')].map(
      (n) => `${n.getAttribute('hreflang')} ${n.getAttribute('href')}`,
    ),
  }))

test('search: title, description, canonical and language links follow the page and language', async ({ page }) => {
  await page.goto('/?lang=en')
  await page.locator('button[type=submit]').waitFor()
  const en = await head(page)
  expect(en.title).toContain('survival calculator for very-low-birth-weight')
  expect(en.description).toContain('DeepSurv')
  expect(en.ogTitle).toBe(en.title)
  expect(en.canonical).toBe('https://neomortalsurv.net/')
  expect(en.robots).toBeNull()
  expect(en.alternates).toContain('en https://neomortalsurv.net/?lang=en')
  expect(en.alternates).toContain('ru https://neomortalsurv.net/?lang=ru')
  expect(en.alternates).toContain('x-default https://neomortalsurv.net/')

  await page.getByRole('button', { name: 'Русский' }).click()
  await expect(page).toHaveTitle(/калькулятор выживаемости/)
  const ru = await head(page)
  expect(ru.description).toContain('DeepSurv')
  expect(ru.description).not.toBe(en.description)
  expect(ru.canonical).toBe('https://neomortalsurv.net/?lang=ru')

  await page.locator('a[href="/about"]').click()
  await expect(page).toHaveTitle(/О модели/)
  const about = await head(page)
  expect(about.canonical).toBe('https://neomortalsurv.net/about?lang=ru')
  expect(about.alternates).toContain('en https://neomortalsurv.net/about?lang=en')
})

test('search: the report page is marked noindex and the mark goes away again', async ({ page }) => {
  await openReport(page, 'en')
  const report = await head(page)
  expect(report.robots).toBe('noindex')
  expect(report.canonical).toBeNull()
  expect(report.alternates).toEqual([])
  await page.getByRole('link', { name: 'Back to the calculator' }).click()
  await page.locator('button[type=submit]').waitFor()
  expect((await head(page)).robots).toBeNull()
})

test('search: the page says what it is before any script runs', async ({ request }) => {
  const html = await (await request.get('/')).text()
  expect(html).toContain('<title>NeoMortalSurv – survival calculator for very-low-birth-weight (VLBW) infants</title>')
  expect(html).toContain('very-low-birth-weight (VLBW)')
  expect(html).toContain('doi:10.3389/fped.2026.1801840')
  expect(html).toContain('application/ld+json')
  expect(html).not.toContain('%VITE_SITE_URL%')
})

test('search: robots.txt, sitemap.xml and the preview image are served', async ({ request }) => {
  const robots = await request.get('/robots.txt')
  expect(robots.status()).toBe(200)
  expect(await robots.text()).toContain('Sitemap: https://neomortalsurv.net/sitemap.xml')
  const sitemap = await request.get('/sitemap.xml')
  expect(sitemap.status()).toBe(200)
  expect(await sitemap.text()).toContain('<loc>https://neomortalsurv.net/about?lang=kk</loc>')
  const image = await request.get('/og.png')
  expect(image.status()).toBe(200)
  expect(image.headers()['content-type']).toContain('image/png')
})
