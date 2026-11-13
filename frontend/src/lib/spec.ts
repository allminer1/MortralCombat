import { z } from 'zod'

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

export interface ModelInfo {
  model_version: string
  feature_spec: { features: Feature[] }
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
