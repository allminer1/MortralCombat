import { useController, type Control } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import type { Feature, FormValues } from '../lib/spec'

type IntFeature = Extract<Feature, { type: 'int' }>

export function NumberField({ feature, control }: { feature: IntFeature; control: Control<FormValues> }) {
  const { t } = useTranslation()
  const name = feature.api_field
  const { field, fieldState } = useController({ name, control })
  const label = t(`fields.${name}`)
  const unit = feature.unit ? t(`units.${feature.unit}`) : ''
  const range = { min: feature.min, max: feature.max, unit }
  const code = fieldState.error?.message
  const current = /^\d+$/.test(field.value.trim()) ? Number(field.value) : null

  // Steppers adjust an entered value; they never invent one for an empty field.
  const step = (delta: number) => {
    if (current === null) return
    const next = Math.min(feature.max, Math.max(feature.min, current + delta))
    field.onChange(String(next))
  }
  const stepper =
    'grid h-11 w-10 shrink-0 place-items-center text-xl leading-none text-accent hover:bg-accent-soft disabled:text-field disabled:hover:bg-transparent'

  return (
    <div>
      <label htmlFor={name} className="block font-medium">
        {label}
      </label>
      <p id={`${name}-hint`} className="text-[0.9rem] text-muted">
        {t(unit ? 'form.rangeWithUnit' : 'form.range', range)}
      </p>
      <div
        className={
          'mt-1.5 flex w-44 overflow-hidden rounded-md border bg-surface focus-within:outline-3 focus-within:outline-offset-2 focus-within:outline-accent ' +
          (code ? 'border-error' : 'border-field')
        }
      >
        <button
          type="button"
          className={stepper}
          aria-label={t('form.decrease', { field: label })}
          disabled={current === null || current <= feature.min}
          onClick={() => step(-1)}
        >
          −
        </button>
        <input
          id={name}
          name={name}
          ref={field.ref}
          value={field.value}
          onChange={(e) => field.onChange(e.target.value)}
          onBlur={field.onBlur}
          type="text"
          inputMode="numeric"
          autoComplete="off"
          aria-describedby={`${name}-hint${code ? ` ${name}-error` : ''}`}
          aria-invalid={code ? true : undefined}
          aria-required="true"
          className="h-11 w-full min-w-0 border-x border-rule bg-transparent px-2 text-center text-lg tabular-nums outline-none"
        />
        <button
          type="button"
          className={stepper}
          aria-label={t('form.increase', { field: label })}
          disabled={current === null || current >= feature.max}
          onClick={() => step(1)}
        >
          +
        </button>
      </div>
      {code && (
        <p id={`${name}-error`} className="mt-1 text-[0.9rem] font-medium text-error">
          {t(`errors.${code}`, { defaultValue: t('errors.invalid'), ...range })}
        </p>
      )}
    </div>
  )
}
