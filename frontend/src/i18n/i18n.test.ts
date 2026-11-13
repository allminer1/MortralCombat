import { describe, expect, it } from 'vitest'
import en from './en.json'
import kk from './kk.json'
import { availableLanguages, pickLanguage } from './languages'
import ru from './ru.json'

const keys = (node: unknown, prefix = ''): string[] =>
  node !== null && typeof node === 'object'
    ? Object.entries(node).flatMap(([k, v]) => keys(v, prefix ? `${prefix}.${k}` : k))
    : [prefix]
const textKeys = (node: unknown) => keys(node).filter((k) => !k.startsWith('_')).sort()

describe('translations', () => {
  it('have the same keys in every language', () => {
    expect(textKeys(ru)).toEqual(textKeys(en))
    expect(textKeys(kk)).toEqual(textKeys(en))
  })
  it('record the review state of each language', () => {
    // All three languages were reported reviewed on 2026-11-13 (docs/DECISIONS.md).
    for (const file of [en, ru, kk]) {
      expect(file._clinical_review).toContain('2026-11-13')
      // The only draft marker left names the search texts awaiting the owner's approval.
      expect(file._todo_clinical_review).toMatch(/^TODO\(owner\): the seo\.\* texts/)
    }
    // Text added after the EN / RU review was accepted by the owner, and says so.
    for (const file of [en, ru]) expect(file._owner_accepted).toContain('warnings.OUTSIDE_TRAINING_RANGE')
  })
  it('list the Kazakh clinical terms next to the labels they come from', () => {
    for (const [field, label] of Object.entries(kk.fields)) {
      expect(kk._clinical_terms[`fields.${field}` as keyof typeof kk._clinical_terms]).toBe(label)
    }
  })
  it('spell the obstetric-history label correctly', () => {
    expect(en.fields.bad_obstetric_history).toBe('Bad obstetric history')
  })
})

describe('language choice', () => {
  it('hides Kazakh unless the build flag is on', () => {
    expect(availableLanguages(false).map((l) => l.code)).toEqual(['en', 'ru'])
    expect(availableLanguages(true).map((l) => l.code)).toEqual(['en', 'ru', 'kk'])
  })
  it('prefers ?lang=, then the stored choice, then the browser, then English', () => {
    const all = ['en', 'ru']
    expect(pickLanguage(all, '?lang=ru', 'en', ['en-GB'])).toBe('ru')
    expect(pickLanguage(all, '', 'ru', ['en-GB'])).toBe('ru')
    expect(pickLanguage(all, '', null, ['de-DE', 'ru-RU'])).toBe('ru')
    expect(pickLanguage(all, '', null, ['de-DE'])).toBe('en')
  })
  it('ignores Kazakh everywhere when it is not enabled', () => {
    expect(pickLanguage(['en', 'ru'], '?lang=kk', 'kk', ['kk-KZ', 'ru-RU'])).toBe('ru')
    expect(pickLanguage(['en', 'ru', 'kk'], '?lang=kk', null, [])).toBe('kk')
  })
})
