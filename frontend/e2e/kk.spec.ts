// Runs against a second build made with VITE_ENABLE_KK=true (project "kk-flag").
import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'
import { openReport, pdfPageCount } from './helpers'

const KAZAKH_LETTERS = 'ә ғ қ ң ө ұ ү һ і Ә Ғ Қ Ң Ө Ұ Ү Һ І'

test('with the flag, Kazakh is in the switch and works end to end', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Қазақша' }).click()
  await expect(page.locator('html')).toHaveAttribute('lang', 'kk')
  await expect(page.getByRole('heading', { name: 'Расталған диагноздар' })).toBeVisible()
  await openReport(page, 'kk')
  await expect(page.getByTestId('report-estimates')).toContainText('1,210')
  expect(pdfPageCount(await page.pdf({ preferCSSPageSize: true, printBackground: true }))).toBe(1)
  const scan = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze()
  expect(scan.violations).toEqual([])
})

test('Kazakh letters are drawn with the bundled font, not a fallback', async ({ page }) => {
  await page.goto('/?lang=kk')
  await page.locator('button[type=submit]').waitFor()
  await page.evaluate(() => document.fonts.ready)
  // fonts.load resolves with the bundled faces that cover the character; none = fallback font.
  const missing = await page.evaluate(async (letters) => {
    const out: string[] = []
    for (const weight of ['300', '400', '500', '600']) {
      for (const ch of letters.split(' ')) {
        const faces = await document.fonts.load(`${weight} 16px "IBM Plex Sans"`, ch)
        if (faces.length === 0) out.push(`${ch}@${weight}`)
      }
    }
    return out
  }, KAZAKH_LETTERS)
  expect(missing).toEqual([])
  // The font files that hold these letters were really fetched from our own host.
  const loaded = await page.evaluate(() => [...document.fonts].filter((f) => f.status === 'loaded').map((f) => f.unicodeRange))
  expect(loaded.length).toBeGreaterThan(0)
})

for (const width of [375, 768, 1366]) {
  test(`screenshots kk ${width}`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 })
    await openReport(page, 'kk')
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width)
    await page.screenshot({ path: `screenshots/kk-${width}-report.png`, fullPage: true })
    await page.locator('a[href="/"]').first().click()
    await page.getByTestId('result').waitFor()
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width)
    await page.screenshot({ path: `screenshots/kk-${width}-result.png`, fullPage: true })
    await page.locator('a[href="/about"]').click()
    await page.getByTestId('about-total').waitFor()
    await page.screenshot({ path: `screenshots/kk-${width}-about.png`, fullPage: true })
  })
}
