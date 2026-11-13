import { Fragment, useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useParams } from 'react-router'
import { ApiError, EXPORT_URL, deleteCalculation, getCalculation, listCalculations, type SavedItem } from '../lib/api'
import { useAuth } from '../lib/auth'
import { dateTime, percent1 } from '../lib/format'
import type { LastCalculation } from '../lib/session'
import { fromStored, type ModelInfo } from '../lib/spec'
import { ReportView } from './Report'

type Load<T> = { state: 'loading' } | { state: 'failed' } | { state: 'missing' } | { state: 'ready'; data: T }

/** Returns a handler that sends the user to the sign-in page when the session is gone. */
function useSessionGuard() {
  const auth = useAuth()
  const navigate = useNavigate()
  return useCallback(
    (error: unknown): boolean => {
      if (error instanceof ApiError && error.code === 'not_signed_in') {
        auth.expire()
        void navigate('/login', { state: { ended: true } })
        return true
      }
      return false
    },
    [auth, navigate],
  )
}

/** Own saved calculations, grouped by case code: a timeline of reassessments per infant. */
export function History() {
  const { t, i18n } = useTranslation()
  const lang = i18n.resolvedLanguage ?? 'en'
  const auth = useAuth()
  const guard = useSessionGuard()
  const [load, setLoad] = useState<Load<SavedItem[]>>({ state: 'loading' })

  useEffect(() => {
    let cancelled = false
    listCalculations().then(
      (data) => !cancelled && setLoad({ state: 'ready', data }),
      (error) => !cancelled && !guard(error) && setLoad({ state: 'failed' }),
    )
    return () => {
      cancelled = true
    }
  }, [guard])

  const onDelete = async (item: SavedItem) => {
    if (!auth.user || !window.confirm(t('history.confirmDelete'))) return
    try {
      await deleteCalculation(auth.user.csrf_token, item.id)
      setLoad((current) =>
        current.state === 'ready' ? { state: 'ready', data: current.data.filter((i) => i.id !== item.id) } : current,
      )
    } catch (error) {
      if (!guard(error)) setLoad({ state: 'failed' })
    }
  }

  const items = load.state === 'ready' ? load.data : []
  const groups = new Map<string, SavedItem[]>()
  for (const item of items) groups.set(item.case_code ?? '', [...(groups.get(item.case_code ?? '') ?? []), item])
  const ordered = [...groups.entries()].sort(([a], [b]) => (a === '' ? 1 : b === '' ? -1 : a.localeCompare(b)))
  const link = 'text-accent underline underline-offset-2 hover:text-accent-strong'

  return (
    <div className="max-w-[52rem] pt-8">
      <h2 className="text-2xl font-semibold tracking-tight">{t('history.title')}</h2>
      <p className="mt-2 text-muted">{t('history.intro')}</p>

      {load.state === 'loading' && <p role="status" className="mt-6 text-muted">{t('history.loading')}</p>}
      {load.state === 'failed' && <p role="alert" className="mt-6 font-medium text-error">{t('history.failed')}</p>}
      {load.state === 'ready' && items.length === 0 && <p className="mt-6">{t('history.empty')}</p>}

      {load.state === 'ready' && items.length > 0 && (
        <p className="mt-4">
          <a href={EXPORT_URL} download className={link}>
            {t('history.export')}
          </a>
        </p>
      )}

      {ordered.map(([code, group]) => (
        <section key={code || '-'} className="mt-8" data-testid="history-group">
          <h3 className="text-lg font-semibold">
            {code ? t('history.caseCode', { code }) : t('history.noCode')}
          </h3>
          <div className="mt-2 overflow-x-auto">
            <table className="w-full border-collapse text-left tabular-nums">
              <thead>
                <tr className="border-b border-ink">
                  <th scope="col" className="py-1.5 pr-4 font-semibold">{t('history.when')}</th>
                  {[7, 28, 100].map((day) => (
                    <th key={day} scope="col" className="py-1.5 pl-3 text-right font-semibold sm:pr-4 sm:pl-0">{t('result.day', { day })}</th>
                  ))}
                  <th scope="col" className="hidden py-1.5 sm:table-cell">
                    <span className="sr-only">
                      {t('history.open')} / {t('history.delete')}
                    </span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {group.map((item) => {
                  const when = dateTime(new Date(item.created_at), lang)
                  const s = item.outputs.survival
                  const actions = (
                    <>
                      <Link to={`/history/${item.id}`} className={link}>
                        {t('history.open')}
                      </Link>
                      <button
                        type="button"
                        onClick={() => void onDelete(item)}
                        aria-label={t('history.deleteLabel', { when })}
                        className="min-h-9 rounded-md border border-field px-3 text-[0.95rem] hover:bg-surface"
                      >
                        {t('history.delete')}
                      </button>
                    </>
                  )
                  return (
                    <Fragment key={item.id}>
                    <tr className="border-rule sm:border-b" data-testid="history-row">
                      <td className="py-2 pr-3">{when}</td>
                      <td className="py-2 pr-3 text-right">{percent1(s.day_7, lang)}</td>
                      <td className="py-2 pr-3 text-right">{percent1(s.day_28, lang)}</td>
                      <td className="py-2 text-right sm:pr-4">{percent1(s.day_100, lang)}</td>
                      <td className="hidden py-2 text-right whitespace-nowrap sm:table-cell">
                        <div className="flex items-center justify-end gap-4">{actions}</div>
                      </td>
                    </tr>
                    {/* Phones: the actions get their own line, so no column is cut off. */}
                    <tr className="border-b border-rule sm:hidden">
                      <td colSpan={4} className="pb-2.5">
                        <div className="flex items-center gap-4">{actions}</div>
                      </td>
                    </tr>
                    </Fragment>
                  )
                })}
              </tbody>
            </table>
          </div>
        </section>
      ))}
    </div>
  )
}

/** One saved calculation, shown with the same sheet as the print report. */
export function HistoryItem({ model }: { model: ModelInfo }) {
  const { t } = useTranslation()
  const { id = '' } = useParams()
  const guard = useSessionGuard()
  const [load, setLoad] = useState<Load<LastCalculation>>({ state: 'loading' })

  useEffect(() => {
    let cancelled = false
    getCalculation(id).then(
      (item) => {
        if (cancelled) return
        setLoad({
          state: 'ready',
          data: {
            values: fromStored(model.feature_spec.features, item.inputs),
            at: new Date(item.created_at),
            prediction: {
              model_version: item.model_version,
              log_risk: item.outputs.log_risk,
              survival: item.outputs.survival,
              curve: (item.outputs.curve ?? []).map((survival, day) => ({ day, survival })),
              warnings: item.outputs.warnings,
            },
          },
        })
      },
      (error) => {
        if (cancelled || guard(error)) return
        setLoad({ state: error instanceof ApiError && error.code === 'not_found' ? 'missing' : 'failed' })
      },
    )
    return () => {
      cancelled = true
    }
  }, [id, guard, model])

  const back = (
    <Link to="/history" className="text-accent underline underline-offset-2 hover:text-accent-strong">
      {t('history.back')}
    </Link>
  )
  if (load.state === 'ready') return <ReportView model={model} calculation={load.data} back={back} />
  return (
    <div className="max-w-xl pt-10">
      {load.state === 'loading' && <p role="status" className="text-muted">{t('history.loading')}</p>}
      {load.state === 'missing' && <p role="alert">{t('history.notFound')}</p>}
      {load.state === 'failed' && <p role="alert" className="font-medium text-error">{t('history.failed')}</p>}
      <p className="mt-4">{back}</p>
    </div>
  )
}
