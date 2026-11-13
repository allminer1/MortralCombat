import type { RefObject } from 'react'
import { useTranslation } from 'react-i18next'
import { fixed3, percent0, percent1 } from '../lib/format'
import type { Prediction } from '../lib/spec'
import { SurvivalCurve } from './SurvivalCurve'

const LIMITATIONS = ['cohort', 'validation', 'calibration', 'judgement'] as const

export function ResultPanel({
  prediction,
  stale,
  headingRef,
}: {
  prediction: Prediction | null
  stale: boolean
  headingRef: RefObject<HTMLHeadingElement | null>
}) {
  const { t, i18n } = useTranslation()
  const lang = i18n.resolvedLanguage ?? 'en'
  const s = prediction?.survival

  return (
    <section aria-labelledby="result-title" className="min-w-0 lg:sticky lg:top-6 lg:self-start">
      <div className="rounded-lg border border-rule bg-surface p-5 sm:p-7">
        <h2 id="result-title" ref={headingRef} tabIndex={-1} className="text-lg font-semibold outline-none">
          {t('result.title')}
        </h2>

        {!prediction && <p className="mt-2 max-w-[52ch] text-muted">{t('result.empty')}</p>}

        {prediction && stale && (
          <p role="status" className="mt-3 rounded-md border border-notice bg-notice-soft px-3 py-2 font-medium text-notice">
            {t('result.stale')}
          </p>
        )}

        {prediction && s && (
          <div className={stale ? 'opacity-55' : undefined} data-testid="result" data-stale={stale}>
            <dl className="mt-4 flex flex-wrap items-end gap-x-12 gap-y-4">
              {([7, 28] as const).map((day) => (
                <div key={day}>
                  <dt className="font-medium text-muted" title={t('result.probability', { day })}>
                    {t('result.day', { day })}
                  </dt>
                  <dd className="m-0 text-[4.5rem] font-light leading-none tracking-tight tabular-nums sm:text-[5.5rem]" data-testid={`headline-day-${day}`}>
                    {percent0(s[`day_${day}`], lang)}
                  </dd>
                </div>
              ))}
              <div className="pb-1.5">
                <dt className="font-medium text-muted">{t('result.day', { day: 100 })}</dt>
                <dd className="m-0 text-[2rem] leading-none tabular-nums" data-testid="headline-day-100">
                  {percent0(s.day_100, lang)}
                </dd>
              </div>
            </dl>
            <p className="mt-2 text-[0.9rem] text-muted">{t('result.probability', { day: '7 / 28 / 100' })}</p>
          </div>
        )}

        <div className={'mt-6 ' + (prediction && stale ? 'opacity-55' : '')}>
          <SurvivalCurve key={prediction ? 'curve' : 'empty'} points={prediction?.curve ?? null} marked={[7, 28]} />
        </div>

        {prediction && s && (
          <>
            <section aria-labelledby="details-title" className="mt-6 border-t border-rule pt-5">
              <h3 id="details-title" className="font-semibold">
                {t('result.details')}
              </h3>
              <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-6 gap-y-1 tabular-nums" data-testid="details">
                {([7, 28, 100] as const).map((day) => (
                  <div key={day} className="col-span-2 grid grid-cols-subgrid">
                    <dt className="text-muted">{t('result.day', { day })}</dt>
                    <dd className="m-0">{percent1(s[`day_${day}`], lang)}</dd>
                  </div>
                ))}
                <div className="col-span-2 grid grid-cols-subgrid">
                  <dt className="text-muted">{t('result.logRisk')}</dt>
                  <dd className="m-0" data-testid="log-risk">{fixed3(prediction.log_risk, lang)}</dd>
                </div>
                <div className="col-span-2 grid grid-cols-subgrid">
                  <dt className="text-muted">{t('result.modelVersion')}</dt>
                  <dd className="m-0">{prediction.model_version}</dd>
                </div>
                <div className="col-span-2 grid grid-cols-subgrid">
                  <dt className="text-muted">{t('result.warnings')}</dt>
                  <dd className="m-0" data-testid="warnings">
                    {prediction.warnings.length === 0
                      ? t('result.noWarnings')
                      : prediction.warnings.map((code) => (
                          <p key={code} className="m-0 max-w-[60ch] font-medium text-notice">
                            {t(`warnings.${code}`, { defaultValue: t('warnings.unknown', { code }) })}
                          </p>
                        ))}
                  </dd>
                </div>
              </dl>
            </section>

            <section aria-labelledby="limitations-title" className="mt-6 rounded-md border border-field bg-page px-4 py-3.5">
              <h3 id="limitations-title" className="font-semibold">
                {t('limitations.title')}
              </h3>
              <ul className="mt-1.5 list-disc space-y-0.5 pl-5">
                {LIMITATIONS.map((key) => (
                  <li key={key} className="max-w-[70ch]">{t(`limitations.${key}`)}</li>
                ))}
              </ul>
            </section>
          </>
        )}
      </div>
    </section>
  )
}
