import { describe, expect, it } from 'vitest'
import en from './en.json'
import ru from './ru.json'

const keys = (node: unknown, prefix = ''): string[] =>
  node !== null && typeof node === 'object'
    ? Object.entries(node).flatMap(([k, v]) => keys(v, prefix ? `${prefix}.${k}` : k))
    : [prefix]

describe('translations', () => {
  it('have the same keys in every language', () => {
    expect(keys(ru).sort()).toEqual(keys(en).sort())
  })
  it('carry the clinical-review marker', () => {
    expect(en._todo_clinical_review).toContain('TODO(clinical-review)')
    expect(ru._todo_clinical_review).toContain('TODO(clinical-review)')
  })
  it('spell the obstetric-history label correctly', () => {
    expect(en.fields.bad_obstetric_history).toBe('Bad obstetric history')
  })
})
