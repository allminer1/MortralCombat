import { describe, expect, it } from 'vitest'
import { dayAt, stepPath, xOf, yOf, type Frame } from './curve'
import { layoutMatches } from './fields'
import { fixed3, monthRange, percent0, percent1 } from './format'
import { emptyValues, fieldError, isComplete, toRequest, type Feature } from './spec'

const weight: Feature = { api_field: 'w', type: 'int', min: 400, max: 2000, unit: 'g' }
const flag: Feature = { api_field: 'b', type: 'bool' }
const grade: Feature = { api_field: 'g', type: 'enum', values: [2, 3] }
const features = [weight, flag, grade]

describe('field validation', () => {
  it('starts empty and incomplete', () => {
    const values = emptyValues(features)
    expect(values).toEqual({ w: '', b: '', g: '' })
    expect(isComplete(features, values)).toBe(false)
  })
  it('checks integers against the served range', () => {
    expect(fieldError(weight, '')).toBe('required')
    expect(fieldError(weight, '12.5')).toBe('not_integer')
    expect(fieldError(weight, '-5')).toBe('not_integer')
    expect(fieldError(weight, 'abc')).toBe('not_integer')
    expect(fieldError(weight, '399')).toBe('out_of_range')
    expect(fieldError(weight, '2001')).toBe('out_of_range')
    expect(fieldError(weight, '400')).toBeNull()
    expect(fieldError(weight, ' 2000 ')).toBeNull()
  })
  it('requires an explicit choice', () => {
    expect(fieldError(flag, '')).toBe('choose')
    expect(fieldError(flag, 'no')).toBeNull()
    expect(fieldError(grade, '')).toBe('choose')
    expect(fieldError(grade, '4')).toBe('choose')
    expect(fieldError(grade, '3')).toBeNull()
  })
  it('builds a named request with JSON types', () => {
    const values = { w: '900', b: 'yes', g: '3' }
    expect(isComplete(features, values)).toBe(true)
    expect(toRequest(features, values)).toEqual({ w: 900, b: true, g: 3 })
    expect(toRequest(features, { ...values, b: 'no' }).b).toBe(false)
  })
})

describe('layout', () => {
  it('rejects a server that serves other fields than the form shows', () => {
    expect(layoutMatches(features)).toBe(false)
  })
})

describe('formatting', () => {
  it('rounds headline numbers to whole percent', () => {
    expect(percent0(0.6522, 'en')).toBe('65%')
    expect(percent0(0.3952, 'en')).toBe('40%')
    expect(percent0(0.0563, 'en')).toBe('6%')
  })
  it('uses one decimal in details and three for the log-risk', () => {
    expect(percent1(0.3952, 'en')).toBe('39.5%')
    expect(fixed3(1.2099, 'en')).toBe('1.210')
    expect(fixed3(1.2099, 'ru')).toBe('1,210')
  })
})

describe('Kazakh and dates', () => {
  it('formats Kazakh numbers with a decimal comma', () => {
    expect(fixed3(1.2099, 'kk')).toBe('1,210')
    expect(percent1(0.3952, 'kk')).toBe(percent1(0.3952, 'ru'))
  })
  it('turns the model-card period into month names', () => {
    expect(monthRange('2021-01 to 2025-05', 'en')).toBe('January 2021 – May 2025')
    expect(monthRange('unexpected', 'en')).toBe('unexpected')
  })
})

describe('curve geometry', () => {
  const f: Frame = { width: 200, height: 100, left: 0, right: 0, top: 0, bottom: 0, maxDay: 100 }
  it('maps days and survival to the frame', () => {
    expect(xOf(f, 50)).toBe(100)
    expect(yOf(f, 1)).toBe(0)
    expect(yOf(f, 0)).toBe(100)
  })
  it('draws steps, never slopes', () => {
    const path = stepPath(f, [
      { day: 0, survival: 1 },
      { day: 1, survival: 0.5 },
      { day: 2, survival: 0.5 },
    ])
    expect(path).toBe('M0,0H2V50H4V50')
  })
  it('finds and clamps the day under a position', () => {
    expect(dayAt(f, 56)).toBe(28)
    expect(dayAt(f, -20)).toBe(0)
    expect(dayAt(f, 999)).toBe(100)
  })
})
