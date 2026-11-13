// Runs only through `make e2e-accounts`: compose stack with PostgreSQL and ENABLE_ACCOUNTS
// on, two throwaway users whose random passwords arrive in the environment.
import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'
import { fillFigure8 } from './helpers'

const A = { email: 'a@example.test', password: process.env.E2E_PASSWORD_A ?? '' }
const B = { email: 'b@example.test', password: process.env.E2E_PASSWORD_B ?? '' }
const WCAG = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']

async function signIn(page: Page, user: typeof A): Promise<void> {
  await page.goto('/login?lang=en')
  await page.getByLabel('E-mail').fill(user.email)
  await page.getByLabel('Password').fill(user.password)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page.getByRole('button', { name: 'Sign out' })).toBeVisible()
}

async function calculateAndSave(page: Page, code: string): Promise<void> {
  await fillFigure8(page)
  await page.locator('button[type=submit]').click()
  await page.getByTestId('result').waitFor()
  if (code) await page.getByLabel('Case code (optional)').fill(code)
  await page.getByRole('button', { name: 'Save', exact: true }).click()
  await expect(page.getByText('Saved.')).toBeVisible()
}

test.describe.configure({ mode: 'serial' })

test('calculator works without signing in; history asks for sign-in', async ({ page }) => {
  await page.goto('/?lang=en')
  await expect(page.getByRole('link', { name: 'Sign in' })).toBeVisible()
  await fillFigure8(page)
  await page.locator('button[type=submit]').click()
  await expect(page.getByTestId('headline-day-28')).toHaveText(/^40\s?%$/)
  await expect(page.getByRole('button', { name: 'Save', exact: true })).toHaveCount(0)
  await page.goto('/history')
  await expect(page).toHaveURL(/\/login$/)
})

test('wrong password is refused with one message', async ({ page }) => {
  await page.goto('/login?lang=en')
  await page.getByLabel('E-mail').fill(A.email)
  await page.getByLabel('Password').fill('not-the-password-123')
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page.getByRole('alert')).toHaveText('E-mail or password is not correct.')
})

test('save, timeline by case code, open, print view, delete', async ({ page }) => {
  await signIn(page, A)
  await calculateAndSave(page, 'CASE-7')
  // reassessment of the same infant: NEC no longer present
  await page.locator('input[name=nec][value=no]').check({ force: true })
  await page.locator('button[type=submit]').click()
  await expect(page.getByTestId('result')).toHaveAttribute('data-stale', 'false')
  await page.getByLabel('Case code (optional)').fill('CASE-7')
  await page.getByRole('button', { name: 'Save', exact: true }).click()
  await expect(page.getByText('Saved.')).toBeVisible()

  await page.getByRole('link', { name: 'Open history' }).click()
  const group = page.getByTestId('history-group').filter({ hasText: 'Case code CASE-7' })
  await expect(group.getByTestId('history-row')).toHaveCount(2)
  await expect(group.getByTestId('history-row').nth(1)).toContainText('39.5%') // older one: Figure 8
  expect((await new AxeBuilder({ page }).withTags(WCAG).analyze()).violations).toEqual([])

  await group.getByTestId('history-row').nth(1).getByRole('link', { name: 'Open' }).click()
  await expect(page.getByTestId('report-estimates')).toContainText('1.210')
  await expect(page.getByTestId('report-inputs')).toContainText('Birth weight900 g')
  await page.getByRole('link', { name: 'Back to history' }).click()

  page.once('dialog', (dialog) => void dialog.accept())
  await group.getByTestId('history-row').first().getByRole('button', { name: /^Delete/ }).click()
  await expect(group.getByTestId('history-row')).toHaveCount(1)
})

test('case code refuses names and spaces', async ({ page }) => {
  await signIn(page, A)
  await fillFigure8(page)
  await page.locator('button[type=submit]').click()
  await page.getByTestId('result').waitFor()
  await page.getByLabel('Case code (optional)').fill('Ivan Petrov')
  await expect(page.getByRole('button', { name: 'Save', exact: true })).toBeDisabled()
  await expect(page.locator('#case-code-error')).toBeVisible()
  expect((await new AxeBuilder({ page }).withTags(WCAG).analyze()).violations).toEqual([])
})

test('another user sees none of it, in the list, by address or in the export', async ({ page, browser }) => {
  await signIn(page, A)
  await page.goto('/history')
  const href = await page.getByTestId('history-row').first().getByRole('link', { name: 'Open' }).getAttribute('href')
  const exportA = await (await page.request.get('/api/v1/calculations/export.csv')).text()
  expect(exportA).toContain('CASE-7')

  const other = await browser.newContext()
  const pageB = await other.newPage()
  await signIn(pageB, B)
  await pageB.goto('/history')
  await expect(pageB.getByText('Nothing saved yet.')).toBeVisible()
  await pageB.goto(href!)
  await expect(pageB.getByText('This saved calculation does not exist.')).toBeVisible()
  const exportB = await (await pageB.request.get('/api/v1/calculations/export.csv')).text()
  expect(exportB).not.toContain('CASE-7')
  expect(exportB.trim().split('\n')).toHaveLength(1) // header only
  await other.close()
})

test('sign out ends access; login page passes the accessibility scan', async ({ page }) => {
  await signIn(page, A)
  await page.getByRole('button', { name: 'Sign out' }).click()
  await expect(page.getByRole('link', { name: 'Sign in' })).toBeVisible()
  expect((await page.request.get('/api/v1/calculations')).status()).toBe(401)
  await page.goto('/login?lang=ru')
  await expect(page.getByRole('heading', { name: 'Вход' })).toBeVisible()
  expect((await new AxeBuilder({ page }).withTags(WCAG).analyze()).violations).toEqual([])
})

test('session cookie is HttpOnly and nothing clinical is kept in browser storage', async ({ page, context }) => {
  await signIn(page, A)
  await calculateAndSave(page, 'CASE-8')
  const cookie = (await context.cookies()).find((c) => c.name.endsWith('nms_session'))
  expect(cookie?.httpOnly).toBe(true)
  expect(cookie?.sameSite).toBe('Lax')
  const stored = await page.evaluate(() => JSON.stringify([{ ...localStorage }, { ...sessionStorage }]))
  expect(stored).not.toContain('CASE-8')
  expect(stored).not.toContain('900')
  expect(await page.evaluate(() => document.cookie)).not.toContain('nms_session')
})

for (const lang of ['en', 'ru']) {
  for (const width of [375, 768, 1366]) {
    test(`screenshots of login, save box and history, ${lang} ${width}`, async ({ page }) => {
      await page.setViewportSize({ width, height: 900 })
      const fits = async () => expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width)
      await page.goto(`/login?lang=${lang}`)
      await page.locator('#email').waitFor()
      await fits()
      await page.screenshot({ path: `screenshots/${lang}-${width}-login.png`, fullPage: true })
      await page.locator('#email').fill(A.email)
      await page.locator('#password').fill(A.password)
      await page.locator('form button[type=submit]').click()
      await page.locator('#gestational_age_weeks').waitFor()
      await fillFigure8(page)
      await page.locator('button[type=submit]').click()
      await page.locator('#case-code').waitFor()
      await fits()
      await page.locator('#save-title').scrollIntoViewIfNeeded()
      await page.screenshot({ path: `screenshots/${lang}-${width}-save.png` })
      await page.goto(`/history?lang=${lang}`)
      await page.getByTestId('history-row').first().waitFor()
      await fits()
      // every action is on screen without sideways scrolling inside the table
      const box = await page.getByRole('button', { name: /^(Delete|Удалить)/ }).first().boundingBox()
      expect(box!.x + box!.width).toBeLessThanOrEqual(width)
      const last = await page.getByTestId('history-row').first().locator('td').nth(3).boundingBox()
      expect(last!.x + last!.width).toBeLessThanOrEqual(width)
      await page.screenshot({ path: `screenshots/${lang}-${width}-history.png`, fullPage: true })
    })
  }
}
