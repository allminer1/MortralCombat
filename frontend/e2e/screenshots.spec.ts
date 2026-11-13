import { expect, test } from '@playwright/test'
import { fillFigure8 } from './helpers'

// Review screenshots at the three widths of spec 7.6, both languages, empty and filled.
// Written to frontend/screenshots/ (not committed).
for (const lang of ['en', 'ru']) {
  for (const [width, height] of [[375, 812], [768, 1024], [1366, 768]] as const) {
    test(`screenshot ${lang} ${width}`, async ({ page }) => {
      await page.setViewportSize({ width, height })
      await page.goto(`/?lang=${lang}`)
      await page.getByRole('button', { name: /^(Calculate|Рассчитать)$/ }).waitFor()
      await page.screenshot({ path: `screenshots/${lang}-${width}-empty.png`, fullPage: true })
      await fillFigure8(page)
      await page.getByRole('button', { name: /^(Calculate|Рассчитать)$/ }).click()
      await page.getByTestId('result').waitFor()
      // Nothing may be wider than the screen (no sideways scrolling).
      expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width)
      await page.screenshot({ path: `screenshots/${lang}-${width}-result.png`, fullPage: true })
      await page.screenshot({ path: `screenshots/${lang}-${width}-result-viewport.png` })
    })
  }
}
