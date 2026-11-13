import type { Page } from '@playwright/test'

/** Article Figure 8 (spec 2.4), by field name. */
export const FIGURE_8 = {
  numbers: {
    gestational_age_weeks: '27',
    birth_weight_g: '900',
    apgar_5min: '3',
    heart_rate_bpm: '80',
    spo2_percent: '55',
  },
  choices: {
    bad_obstetric_history: 'yes',
    respiratory_failure_grade: '3',
    rds: 'yes',
    ivh: 'yes',
    dic: 'yes',
    nec: 'yes',
  },
} as const

export async function fillFigure8(page: Page): Promise<void> {
  for (const [name, value] of Object.entries(FIGURE_8.numbers)) await page.locator(`#${name}`).fill(value)
  for (const [name, value] of Object.entries(FIGURE_8.choices)) {
    await page.locator(`input[type=radio][name=${name}][value="${value}"]`).check({ force: true })
  }
}

/** Number of pages in a PDF produced by Chromium. */
export function pdfPageCount(pdf: Buffer): number {
  return (pdf.toString('latin1').match(/\/Type\s*\/Page\b(?!s)/g) ?? []).length
}

/** Fill Figure 8, calculate, open the report through the Print report link. */
export async function openReport(page: Page, lang: string): Promise<void> {
  await page.goto(`/?lang=${lang}`)
  await fillFigure8(page)
  await page.locator('button[type=submit]').click()
  await page.getByTestId('result').waitFor()
  await page.locator('a[href="/report"]').click()
  await page.getByTestId('report-sheet').waitFor()
}
