import { z } from 'zod'

// zod normally probes whether it may compile validators with `new Function`. The site's
// Content-Security-Policy forbids that, and the probe alone is reported as a violation.
z.config({ jitless: true })

/** Shapes of GET /api/v1/model. Names, types, ranges and units come from the server;
 *  nothing here retypes them. */
export type Feature =
  | { api_field: string; type: 'bool' }
  | { api_field: string; type: 'int'; min: number; max: number; unit?: string }
  | { api_field: string; type: 'enum'; values: number[] }

export interface Citation {
  authors: string
  title: string
  journal: string
  year: number
  volume: string
  article: string
  doi: string
}

interface Interval {
  value: number
  ci95: [number, number]
}

/** Parts of model/model_card.json that the About page shows (numbers from the article). */
export interface ModelCard {
  cohort: { n_total: number; n_train: number; n_test: number; centres: number; period: string }
  reported_performance: { c_index: Interval; auc_overall: Interval; integrated_brier_score: number }
}

export interface ModelInfo {
  model_version: string
  feature_spec: { features: Feature[] }
  model_card: ModelCard
  citation: Citation
}

export interface Prediction {
  model_version: string
  log_risk: number
  survival: { day_7: number; day_28: number; day_100: number }
  curve: { day: number; survival: number }[]
  warnings: string[]
}

/** Form state: every field is a string; '' means "not answered yet". */
export type FormValues = Record<string, string>
export type RequestBody = Record<string, number | boolean>

export const emptyValues = (features: Feature[]): FormValues =>
  Object.fromEntries(features.map((f) => [f.api_field, '']))

/** Error code for one field, or null when the value is valid. */
export function fieldError(feature: Feature, raw: string): string | null {
  const value = raw.trim()
  if (feature.type === 'int') {
    if (value === '') return 'required'
    if (!/^\d+$/.test(value)) return 'not_integer'
    const n = Number(value)
    return n < feature.min || n > feature.max ? 'out_of_range' : null
  }
  if (feature.type === 'bool') return value === 'yes' || value === 'no' ? null : 'choose'
  return feature.values.map(String).includes(value) ? null : 'choose'
}

export const isComplete = (features: Feature[], values: FormValues): boolean =>
  features.every((f) => fieldError(f, values[f.api_field] ?? '') === null)

/** Named fields in, named fields out. Call only when `isComplete` is true. */
export function toRequest(features: Feature[], values: FormValues): RequestBody {
  return Object.fromEntries(
    features.map((f) => {
      const raw = values[f.api_field].trim()
      return [f.api_field, f.type === 'bool' ? raw === 'yes' : Number(raw)]
    }),
  )
}

/** zod schema for react-hook-form, generated from the served features. Issue messages
 *  are error codes (i18n keys under `errors.`), not sentences. */
export function buildSchema(features: Feature[]) {
  return z.object(
    Object.fromEntries(
      features.map((f) => [
        f.api_field,
        z.string().superRefine((value, ctx) => {
          const code = fieldError(f, value)
          if (code) ctx.addIssue({ code: 'custom', message: code })
        }),
      ]),
    ),
  )
}

/** How an entered value is shown back to the reader: an i18n key or a plain number. */
export function displayValue(feature: Feature, raw: string): { key: string } | { text: string } {
  if (feature.type === 'bool') return { key: `choices.${raw}` }
  if (feature.type === 'enum') return { key: `choices.grade_${raw}` }
  return { text: raw.trim() }
}

/** Same rule as the server and the database: no spaces, no punctuation. */
export const CASE_CODE_RE = /^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$/

/** Stored inputs (JSON types) back into form strings, for showing a saved calculation. */
export function fromStored(features: Feature[], inputs: Record<string, number | boolean>): FormValues {
  return Object.fromEntries(
    features.map((f) => {
      const value = inputs[f.api_field]
      return [f.api_field, f.type === 'bool' ? (value ? 'yes' : 'no') : String(value)]
    }),
  )
}
