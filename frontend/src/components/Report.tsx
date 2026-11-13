import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'
import { GROUPS } from '../lib/fields'
import { dateTime, fixed3, percent1 } from '../lib/format'
import { useSession, type LastCalculation } from '../lib/session'
import { displayValue, type ModelInfo } from '../lib/spec'
import { SurvivalCurve } from './SurvivalCurve'

const LIMITATIONS = ['cohort', 'validation', 'calibration', 'judgement'] as const

/** Print view of the last calculation: one A4 page through print CSS (spec 7.4). */
export function Report({ model }: { model: ModelInfo }) {
  const { t } = useTranslation()
  const { last } = useSession()
  const back = (
    <Link to="/" className="text-accent underline underline-offset-2 hover:text-accent-strong">
      {t('report.back')}
    </Link>
  )
  if (!last) {
    return (
      <div className="max-w-xl pt-10">
        <h2 className="text-2xl font-semibold tracking-tight">{t('report.title')}</h2>
        <p className="mt-3">{t('report.empty')}</p>
        <p className="mt-4">{back}</p>
      </div>
    )
  }
  return <ReportView model={model} calculation={last} back={back} />
}

/** The sheet itself; also used to show a saved calculation from the history. */
export function ReportView({
  model,
  calculation,
  back,
}: {
  model: ModelInfo
  calculation: LastCalculation
  back: ReactNode
}) {
  const { t, i18n } = useTranslation()
  const lang = i18n.resolvedLanguage ?? 'en'
  const { prediction, values, at } = calculation

  const byName = new Map(model.feature_spec.features.map((f) => [f.api_field, f]))
  const c = model.citation
  const s = prediction.survival
  const h3 = 'text-[10.5pt] font-semibold'

  return (
    <div className="pt-6 print:pt-0">
      <div className="mb-5 flex flex-wrap items-center gap-x-6 gap-y-2 print:hidden">
        <button
          type="button"
          onClick={() => window.print()}
          className="min-h-11 rounded-md bg-accent px-6 font-semibold text-white hover:bg-accent-strong"
        >
          {t('report.print')}
        </button>
        {back}
        <p className="w-full text-[0.9rem] text-muted">{t('report.printHint')}</p>
      </div>

      <article
        data-testid="report-sheet"
        className="max-w-[186mm] rounded-lg border border-rule bg-surface p-5 text-[9.5pt] leading-snug sm:p-8 print:max-w-none print:rounded-none print:border-0 print:p-0"
      >
        <header className="flex flex-wrap items-baseline justify-between gap-x-6 border-b border-ink pb-2">
          <h2 className="text-[15pt] font-semibold tracking-tight">
            {t('app.name')}: {t('report.title')}
          </h2>
          <p data-testid="report-when">{t('report.generated', { when: dateTime(at, lang) })}</p>
        </header>
        <p className="mt-3 flex items-end gap-2">
          <span>{t('report.caseCode')}:</span>
          <span aria-hidden="true" className="h-4 min-w-24 flex-1 border-b border-field" />
        </p>

        <div className="mt-4 grid gap-x-8 gap-y-4 sm:grid-cols-2 print:grid-cols-2">
          <section>
            <h3 className={h3}>{t('report.inputs')}</h3>
            <dl className="mt-1 grid grid-cols-[minmax(0,1fr)_auto] gap-x-4 tabular-nums" data-testid="report-inputs">
              {GROUPS.flatMap((g) => [...g.fields]).map((name) => {
                const feature = byName.get(name)!
                const shown = displayValue(feature, values[name])
                const unit = feature.type === 'int' && feature.unit ? ` ${t(`units.${feature.unit}`)}` : ''
                return (
                  <div key={name} className="col-span-2 grid grid-cols-subgrid border-t border-rule py-0.5">
                    <dt>{t(`fields.${name}`)}</dt>
                    <dd className="m-0 text-right font-medium">{'key' in shown ? t(shown.key) : shown.text + unit}</dd>
                  </div>
                )
              })}
            </dl>
          </section>

          <section>
            <h3 className={h3}>{t('report.estimates')}</h3>
            <dl className="mt-1 grid grid-cols-[minmax(0,1fr)_auto] gap-x-4 tabular-nums" data-testid="report-estimates">
              {([7, 28, 100] as const).map((day) => (
                <div key={day} className="col-span-2 grid grid-cols-subgrid border-t border-rule py-0.5">
                  <dt>{t('result.day', { day })}</dt>
                  <dd className="m-0 text-right text-[13pt] font-semibold">{percent1(s[`day_${day}`], lang)}</dd>
                </div>
              ))}
              <div className="col-span-2 grid grid-cols-subgrid border-t border-rule py-0.5">
                <dt>{t('result.logRisk')}</dt>
                <dd className="m-0 text-right">{fixed3(prediction.log_risk, lang)}</dd>
              </div>
              <div className="col-span-2 grid grid-cols-subgrid border-t border-rule py-0.5">
                <dt>{t('result.modelVersion')}</dt>
                <dd className="m-0 text-right">{prediction.model_version}</dd>
              </div>
            </dl>
            <h3 className={`${h3} mt-3`}>{t('result.warnings')}</h3>
            <div data-testid="report-warnings">
              {prediction.warnings.length === 0
                ? t('result.noWarnings')
                : prediction.warnings.map((code) => (
                    <p key={code} className="m-0 font-medium">
                      {t(`warnings.${code}`, { defaultValue: t('warnings.unknown', { code }) })}
                    </p>
                  ))}
            </div>
          </section>
        </div>

        <div className="mt-4 max-w-[150mm]">
          <SurvivalCurve points={prediction.curve} marked={[7, 28]} printable />
        </div>

        <section className="mt-3 border border-field px-3 py-2">
          <h3 className={h3}>{t('limitations.title')}</h3>
          <ul className="mt-0.5 list-disc pl-5">
            {LIMITATIONS.map((key) => (
              <li key={key}>{t(`limitations.${key}`)}</li>
            ))}
          </ul>
        </section>

        <footer className="mt-3 border-t border-rule pt-2 text-[8.5pt] text-muted">
          <p className="font-medium text-ink">{t('footer.intendedUse')}</p>
          <p lang="en" className="mt-0.5">
            {c.authors} {c.title} {c.journal} {c.year};{c.volume}:{c.article}. doi:{c.doi}
          </p>
        </footer>
      </article>
    </div>
  )
}
