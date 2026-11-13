import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'
import { fillFigure8 } from './helpers'

const calculate = (page: import('@playwright/test').Page) => page.getByRole('button', { name: /^(Calculate|Рассчитать)$/ })

test('Figure 8 case reads 65 % / 40 % / 6 % and 1.210 in details', async ({ page }) => {
  await page.goto('/?lang=en')
  await fillFigure8(page)
  await calculate(page).click()

  await expect(page.getByTestId('headline-day-7')).toHaveText(/^65\s?%$/)
  await expect(page.getByTestId('headline-day-28')).toHaveText(/^40\s?%$/)
  await expect(page.getByTestId('headline-day-100')).toHaveText(/^6\s?%$/)
  await expect(page.getByTestId('log-risk')).toHaveText('1.210')
  await expect(page.getByTestId('details')).toContainText('deepsurv-vlbw-1.0.0')
  await expect(page.getByTestId('warnings')).toHaveText('None')
  await expect(page.getByRole('heading', { name: 'Limitations' })).toBeVisible()
  await expect(page.getByTestId('curve-readout')).toHaveText('Day 28: 39.5%')
})

test('empty form cannot be submitted and has no pre-filled values', async ({ page }) => {
  let predictCalls = 0
  page.on('request', (r) => {
    if (r.url().includes('/api/v1/predict')) predictCalls += 1
  })
  await page.goto('/?lang=en')
  await expect(calculate(page)).toBeDisabled()
  for (const input of await page.locator('input[type=text]').all()) await expect(input).toHaveValue('')
  expect(await page.locator('input[type=radio]:checked').count()).toBe(0)
  await expect(page.getByTestId('result')).toHaveCount(0)

  // Ten of eleven fields: still disabled.
  await fillFigure8(page)
  await page.locator('#birth_weight_g').fill('')
  await expect(calculate(page)).toBeDisabled()
  await page.keyboard.press('Enter')
  expect(predictCalls).toBe(0)

  // Out of range: disabled, with an inline message.
  await page.locator('#birth_weight_g').fill('2500')
  await page.locator('#birth_weight_g').blur()
  await expect(page.getByText('Enter a value from 400 to 2000.')).toBeVisible()
  await expect(calculate(page)).toBeDisabled()
  await page.locator('#birth_weight_g').fill('12.5')
  await expect(page.getByText('Enter a whole number.')).toBeVisible()

  await page.locator('#birth_weight_g').fill('900')
  await expect(calculate(page)).toBeEnabled()
})

test('changing an input marks the estimate as out of date; reset clears everything', async ({ page }) => {
  await page.goto('/?lang=en')
  await fillFigure8(page)
  await calculate(page).click()
  await expect(page.getByTestId('result')).toHaveAttribute('data-stale', 'false')

  await page.locator('input[name=nec][value=no]').check({ force: true })
  await expect(page.getByTestId('result')).toHaveAttribute('data-stale', 'true')
  await expect(page.getByText('The inputs have changed since this estimate.')).toBeVisible()
  await calculate(page).click()
  await expect(page.getByTestId('result')).toHaveAttribute('data-stale', 'false')
  await expect(page.getByTestId('headline-day-28')).not.toHaveText(/^40\s?%$/)

  await page.getByRole('button', { name: 'Reset' }).click()
  await expect(page.getByTestId('result')).toHaveCount(0)
  await expect(page.locator('#birth_weight_g')).toHaveValue('')
  expect(await page.locator('input[type=radio]:checked').count()).toBe(0)
})

test('weight above 1,500 g shows the cohort warning', async ({ page }) => {
  await page.goto('/?lang=en')
  await fillFigure8(page)
  await page.locator('#birth_weight_g').fill('1600')
  await calculate(page).click()
  await expect(page.getByTestId('warnings')).toContainText('above 1,500 g')
})

test('curve can be read with the keyboard and as a table', async ({ page }) => {
  await page.goto('/?lang=en')
  await fillFigure8(page)
  await calculate(page).click()
  // After a calculation focus moves to the result heading; wait for that before using the keyboard.
  await expect(page.locator('#result-title')).toBeFocused()
  const slider = page.getByRole('slider', { name: 'Day on the survival curve' })
  await slider.focus()
  await page.keyboard.press('Home')
  await expect(page.getByTestId('curve-readout')).toHaveText('Day 0: 100.0%')
  for (let i = 0; i < 7; i += 1) await page.keyboard.press('ArrowRight')
  await expect(page.getByTestId('curve-readout')).toHaveText('Day 7: 65.2%')
  await slider.fill('100')
  await expect(page.getByTestId('curve-readout')).toHaveText('Day 100: 5.6%')
  await page.getByText('Show the curve as a table').click()
  await expect(page.getByRole('table')).toBeVisible()
  expect(await page.getByRole('table').locator('tbody tr').count()).toBe(101)
})

test('language: switch, remembered choice, ?lang= override', async ({ page }) => {
  await page.goto('/')
  await expect(page.locator('html')).toHaveAttribute('lang', 'en')
  await page.getByRole('button', { name: 'Русский' }).click()
  await expect(page.locator('html')).toHaveAttribute('lang', 'ru')
  await expect(page.getByRole('heading', { name: 'Подтверждённые диагнозы' })).toBeVisible()
  await expect(page.getByText('Отягощенный акушерский анамнез')).toBeVisible()

  await fillFigure8(page)
  await calculate(page).click()
  await expect(page.getByTestId('headline-day-7')).toHaveText(/^65\s?%$/)
  await expect(page.getByTestId('log-risk')).toHaveText('1,210')

  await page.goto('/')
  await expect(page.locator('html')).toHaveAttribute('lang', 'ru') // remembered
  await page.goto('/?lang=en')
  await expect(page.locator('html')).toHaveAttribute('lang', 'en') // override
})

test('first visit follows the browser language', async ({ browser }) => {
  const context = await browser.newContext({ locale: 'ru-RU' })
  const page = await context.newPage()
  await page.goto('/')
  await expect(page.locator('html')).toHaveAttribute('lang', 'ru')
  await context.close()
})

test('no third-party requests, no console errors, no Content-Security-Policy violations', async ({ page, baseURL }) => {
  const own = new URL(baseURL!).host
  const foreign: string[] = []
  const problems: string[] = []
  page.on('request', (r) => {
    if (new URL(r.url()).host !== own && !r.url().startsWith('data:')) foreign.push(r.url())
  })
  page.on('console', (m) => {
    if (m.type() === 'error') problems.push(m.text())
  })
  page.on('pageerror', (e) => problems.push(String(e)))
  await page.goto('/?lang=ru')
  await fillFigure8(page)
  await calculate(page).click()
  await expect(page.getByTestId('result')).toBeVisible()
  await page.locator('a[href="/report"]').click()
  await page.getByTestId('report-sheet').waitFor()
  await page.locator('a[href="/about"]').click()
  await page.getByTestId('about-total').waitFor()
  // Direct visits to the app's own routes are answered with the app (single-page fallback).
  await page.goto('/about')
  await page.getByTestId('about-total').waitFor()
  expect(foreign).toEqual([])
  expect(problems).toEqual([])
})

test('API documentation page loads its own files only', async ({ page, baseURL }) => {
  const own = new URL(baseURL!).host
  const foreign: string[] = []
  const problems: string[] = []
  page.on('request', (r) => {
    if (new URL(r.url()).host !== own && !r.url().startsWith('data:')) foreign.push(r.url())
  })
  page.on('console', (m) => {
    if (m.type() === 'error') problems.push(m.text())
  })
  await page.goto('/api/docs')
  await expect(page.getByText('/api/v1/predict')).toBeVisible()
  expect(foreign).toEqual([])
  expect(problems).toEqual([])
})

for (const lang of ['en', 'ru']) {
  test(`accessibility (axe, WCAG 2.1 A + AA), ${lang}`, async ({ page }) => {
    const scan = () => new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze()
    await page.goto(`/?lang=${lang}`)
    await expect(calculate(page)).toBeVisible()
    expect((await scan()).violations).toEqual([])

    await page.locator('#birth_weight_g').fill('9999')
    await page.locator('#birth_weight_g').blur()
    expect((await scan()).violations).toEqual([]) // with a validation error on screen

    await fillFigure8(page)
    await calculate(page).click()
    await expect(page.getByTestId('result')).toBeVisible()
    await page.locator('details summary').click()
    expect((await scan()).violations).toEqual([]) // with a result and the table open
  })
}
