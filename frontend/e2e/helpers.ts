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
