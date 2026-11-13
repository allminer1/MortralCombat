import { zodResolver } from '@hookform/resolvers/zod'
import { useMemo, useRef, useState } from 'react'
import { useForm, useWatch } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { ApiError, predict } from '../lib/api'
import { GROUPS } from '../lib/fields'
import { buildSchema, emptyValues, isComplete, toRequest } from '../lib/spec'
import type { FormValues, ModelInfo, Prediction } from '../lib/spec'
import { ChoiceField } from './ChoiceField'
import { NumberField } from './NumberField'
import { ResultPanel } from './ResultPanel'

export function Calculator({ model }: { model: ModelInfo }) {
  const { t } = useTranslation()
  const features = model.feature_spec.features
  const byName = useMemo(() => new Map(features.map((f) => [f.api_field, f])), [features])
  const schema = useMemo(() => buildSchema(features), [features])
  const { control, handleSubmit, reset, setError, setFocus } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: emptyValues(features),
    mode: 'onTouched',
  })
  const values = useWatch({ control }) as FormValues
  const complete = isComplete(features, values)

  const [busy, setBusy] = useState(false)
  const [failure, setFailure] = useState<string | null>(null)
  const [result, setResult] = useState<{ prediction: Prediction; inputs: string } | null>(null)
  const resultHeading = useRef<HTMLHeadingElement>(null)
  const stale = result !== null && result.inputs !== JSON.stringify(toComparable(values))

  const onSubmit = handleSubmit(async (submitted) => {
    setBusy(true)
    setFailure(null)
    try {
      const prediction = await predict(toRequest(features, submitted))
      setResult({ prediction, inputs: JSON.stringify(toComparable(submitted)) })
      requestAnimationFrame(() => {
        resultHeading.current?.focus({ preventScroll: true })
        resultHeading.current?.scrollIntoView({ block: 'nearest' })
      })
    } catch (error) {
      const api = error instanceof ApiError ? error : new ApiError('server')
      const fieldIssues = api.issues.filter((i) => i.field !== null && byName.has(i.field))
      for (const issue of fieldIssues) setError(issue.field!, { message: issue.code })
      if (api.code !== 'validation' || fieldIssues.length === 0) {
        setFailure(api.code === 'validation' ? 'server' : api.code)
      }
    } finally {
      setBusy(false)
    }
  })

  const onReset = () => {
    reset(emptyValues(features))
    setResult(null)
    setFailure(null)
    setFocus(GROUPS[0].fields[0])
  }

  return (
    <div className="grid gap-x-12 gap-y-10 pt-8 lg:grid-cols-[minmax(0,26rem)_minmax(0,1fr)]">
      <form onSubmit={onSubmit} noValidate className="min-w-0 space-y-9">
        {GROUPS.map((group) => (
          <section key={group.id} aria-labelledby={`group-${group.id}`}>
            <h2 id={`group-${group.id}`} className="text-lg font-semibold">
              {t(`groups.${group.id}.title`)}
            </h2>
            <p className="mt-1 text-[0.95rem] text-muted">{t(`groups.${group.id}.help`)}</p>
            <div
              className={
                group.id === 'admission'
                  ? 'mt-5 grid grid-cols-1 gap-x-6 gap-y-5 min-[26rem]:grid-cols-2'
                  : 'mt-5 space-y-3.5'
              }
            >
              {group.fields.map((name) => {
                const feature = byName.get(name)!
                return feature.type === 'int' ? (
                  <NumberField key={name} feature={feature} control={control} />
                ) : (
                  <div key={name} className="col-span-full">
                    <ChoiceField feature={feature} control={control} />
                  </div>
                )
              })}
            </div>
          </section>
        ))}

        <div className="border-t border-rule pt-6">
          {failure && (
            <p role="alert" className="mb-4 rounded-md border border-error px-3 py-2 font-medium text-error">
              {t(`errors.${failure}`)}
            </p>
          )}
          <div className="flex flex-wrap gap-3">
            <button
              type="submit"
              disabled={!complete || busy}
              aria-describedby={complete ? undefined : 'incomplete-hint'}
              className="min-h-12 rounded-md bg-accent px-7 text-lg font-semibold text-white hover:bg-accent-strong disabled:bg-rule disabled:text-muted"
            >
              {busy ? t('form.calculating') : t('form.calculate')}
            </button>
            <button
              type="button"
              onClick={onReset}
              className="min-h-12 rounded-md border border-field px-5 font-medium text-ink hover:bg-surface"
            >
              {t('form.reset')}
            </button>
          </div>
          {!complete && (
            <p id="incomplete-hint" className="mt-3 text-[0.95rem] text-muted">
              {t('form.incomplete', { count: features.length })}
            </p>
          )}
        </div>
      </form>

      <ResultPanel
        prediction={result?.prediction ?? null}
        stale={stale}
        headingRef={resultHeading}
      />
    </div>
  )
}

/** Trimmed values, so that a stray space does not mark the result as out of date. */
function toComparable(values: FormValues): [string, string][] {
  return Object.keys(values)
    .sort()
    .map((key) => [key, (values[key] ?? '').trim()])
}
