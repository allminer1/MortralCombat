import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { decimal, integer, monthRange } from '../lib/format'
import type { ModelInfo } from '../lib/spec'

const LIMITATIONS = ['cohort', 'validation', 'calibration', 'judgement'] as const

function Row({ label, children, id }: { label: string; children: ReactNode; id: string }) {
  return (
    <div className="col-span-2 grid grid-cols-subgrid border-t border-rule py-2">
      <dt className="text-muted">{label}</dt>
      <dd className="m-0 tabular-nums" data-testid={id}>
        {children}
      </dd>
    </div>
  )
}

/** Every number on this page is read from the model card served by the API. */
export function About({ model }: { model: ModelInfo }) {
  const { t, i18n } = useTranslation()
  const lang = i18n.resolvedLanguage ?? 'en'
  const { cohort, reported_performance: perf } = model.model_card
  const c = model.citation
  const withCi = (m: { value: number; ci95: [number, number] }) =>
    `${decimal(m.value, 2, lang)} (${t('about.performance.ci', { low: decimal(m.ci95[0], 2, lang), high: decimal(m.ci95[1], 2, lang) })})`
  const heading = 'mt-9 text-lg font-semibold'

  return (
    <article className="max-w-[46rem] pt-8">
      <h2 className="text-2xl font-semibold tracking-tight">{t('about.title')}</h2>

      <h3 className={heading}>{t('about.what.title')}</h3>
      <p className="mt-2">{t('about.what.body')}</p>

      <h3 className={heading}>{t('about.cohort.title')}</h3>
      <dl className="mt-2 grid grid-cols-[minmax(0,1fr)_auto] gap-x-8 border-b border-rule sm:grid-cols-[minmax(0,22rem)_1fr]">
        <Row id="about-total" label={t('about.cohort.infants')}>{integer(cohort.n_total, lang)}</Row>
        <Row id="about-centres" label={t('about.cohort.centres')}>{integer(cohort.centres, lang)}</Row>
        <Row id="about-period" label={t('about.cohort.period')}>{monthRange(cohort.period, lang)}</Row>
        <Row id="about-train" label={t('about.cohort.train')}>{integer(cohort.n_train, lang)}</Row>
        <Row id="about-test" label={t('about.cohort.test')}>{integer(cohort.n_test, lang)}</Row>
        <Row id="about-predictors" label={t('about.cohort.predictors')}>
          {integer(model.feature_spec.features.length, lang)}
        </Row>
      </dl>
      <p className="mt-3">
        <span className="font-medium">{t('about.cohort.exclusions')}:</span> {t('about.cohort.exclusionsText')}
      </p>

      <h3 className={heading}>{t('about.performance.title')}</h3>
      <dl className="mt-2 grid grid-cols-[minmax(0,1fr)_auto] gap-x-8 border-b border-rule sm:grid-cols-[minmax(0,22rem)_1fr]">
        <Row id="about-cindex" label={t('about.performance.cIndex')}>{withCi(perf.c_index)}</Row>
        <Row id="about-auc" label={t('about.performance.auc')}>{withCi(perf.auc_overall)}</Row>
        <Row id="about-ibs" label={t('about.performance.ibs')}>{decimal(perf.integrated_brier_score, 3, lang)}</Row>
      </dl>
      <p className="mt-3">{t('about.performance.note')}</p>

      <h3 className={heading}>{t('about.use.title')}</h3>
      <p className="mt-2">{t('about.use.body')}</p>

      <h3 className={heading}>{t('limitations.title')}</h3>
      <ul className="mt-2 list-disc space-y-0.5 pl-5">
        {LIMITATIONS.map((key) => (
          <li key={key}>{t(`limitations.${key}`)}</li>
        ))}
      </ul>

      <h3 className={heading}>{t('footer.citation')}</h3>
      <p lang="en" className="mt-2">
        {c.authors} {c.title} {c.journal} {c.year};{c.volume}:{c.article}.{' '}
        <a href={`https://doi.org/${c.doi}`} rel="noreferrer" className="text-accent underline underline-offset-2 hover:text-accent-strong">
          doi:{c.doi}
        </a>
      </p>
    </article>
  )
}
