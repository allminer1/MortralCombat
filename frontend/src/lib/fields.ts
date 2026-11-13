import type { Feature } from './spec'

/** On-screen grouping and order (spec 7.2). This is presentation only: the model's
 *  input order lives in model/feature_spec.json and never passes through here. */
export const GROUPS = [
  {
    id: 'admission',
    fields: [
      'gestational_age_weeks',
      'birth_weight_g',
      'apgar_5min',
      'heart_rate_bpm',
      'spo2_percent',
      'bad_obstetric_history',
    ],
  },
  { id: 'diagnoses', fields: ['respiratory_failure_grade', 'rds', 'ivh', 'dic', 'nec'] },
] as const

/** True when the server's fields are exactly the ones the form knows how to show. */
export function layoutMatches(features: Feature[]): boolean {
  const shown: string[] = GROUPS.flatMap((g) => [...g.fields])
  const served = features.map((f) => f.api_field)
  return shown.length === served.length && shown.every((name) => served.includes(name))
}
