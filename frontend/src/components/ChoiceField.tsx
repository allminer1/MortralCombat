import { useController, type Control } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import type { Feature, FormValues } from '../lib/spec'

type ChoiceFeature = Extract<Feature, { type: 'bool' | 'enum' }>

/** No / Yes (or grade II / III) as a radio group that starts with nothing selected. */
export function ChoiceField({ feature, control }: { feature: ChoiceFeature; control: Control<FormValues> }) {
  const { t } = useTranslation()
  const name = feature.api_field
  const { field, fieldState } = useController({ name, control })
  const code = fieldState.error?.message
  const options =
    feature.type === 'bool'
      ? [
          { value: 'no', label: t('choices.no') },
          { value: 'yes', label: t('choices.yes') },
        ]
      : feature.values.map((v) => ({ value: String(v), label: t(`choices.grade_${v}`, { defaultValue: String(v) }) }))

  return (
    <div role="radiogroup" aria-labelledby={`${name}-label`} aria-describedby={code ? `${name}-error` : undefined} aria-required="true">
      <div className="flex items-center justify-between gap-x-4">
        <span id={`${name}-label`} className="min-w-0 font-medium [overflow-wrap:anywhere]">
          {t(`fields.${name}`)}
        </span>
        <div className="flex shrink-0 rounded-md border border-field bg-surface p-0.5">
          {options.map((option, i) => (
            <label key={option.value} className="relative">
              <input
                type="radio"
                name={name}
                value={option.value}
                ref={i === 0 ? field.ref : undefined}
                checked={field.value === option.value}
                onChange={() => field.onChange(option.value)}
                onBlur={field.onBlur}
                className="peer absolute inset-0 cursor-pointer opacity-0"
              />
              <span className="grid h-10 min-w-16 place-items-center rounded px-3 text-ink peer-checked:bg-accent peer-checked:font-semibold peer-checked:text-white peer-hover:bg-accent-soft peer-checked:peer-hover:bg-accent peer-focus-visible:outline-3 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-accent">
                {option.label}
              </span>
            </label>
          ))}
        </div>
      </div>
      {code && (
        <p id={`${name}-error`} className="mt-1 text-[0.9rem] font-medium text-error">
          {t(`errors.${code}`, { defaultValue: t('errors.invalid') })}
        </p>
      )}
    </div>
  )
}
