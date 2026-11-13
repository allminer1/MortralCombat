import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router'
import { ApiError, saveCalculation } from '../lib/api'
import { useAuth } from '../lib/auth'
import { CASE_CODE_RE, type RequestBody } from '../lib/spec'

/** Shown under an up-to-date result when signed in. The server recomputes the result
 *  from the inputs; only the inputs and the optional case code are sent. */
export function SaveCalculation({ inputs }: { inputs: RequestBody }) {
  const { t } = useTranslation()
  const auth = useAuth()
  const navigate = useNavigate()
  const [code, setCode] = useState('')
  const [state, setState] = useState<'idle' | 'saving' | 'saved' | 'failed'>('idle')
  if (!auth.user) return null

  const trimmed = code.trim()
  const badFormat = trimmed !== '' && !CASE_CODE_RE.test(trimmed)

  const onSave = async () => {
    setState('saving')
    try {
      await saveCalculation(auth.user!.csrf_token, inputs, trimmed || null)
      setState('saved')
    } catch (error) {
      if (error instanceof ApiError && error.code === 'not_signed_in') {
        auth.expire()
        void navigate('/login', { state: { ended: true } })
        return
      }
      setState('failed')
    }
  }

  return (
    <section aria-labelledby="save-title" className="mt-6 border-t border-rule pt-5 print:hidden">
      <h3 id="save-title" className="font-semibold">
        {t('save.title')}
      </h3>
      {state === 'saved' ? (
        <p role="status" className="mt-2">
          {t('save.saved')}{' '}
          <Link to="/history" className="text-accent underline underline-offset-2 hover:text-accent-strong">
            {t('save.viewHistory')}
          </Link>
        </p>
      ) : (
        <>
          <label htmlFor="case-code" className="mt-2 block font-medium">
            {t('save.caseCode')}
          </label>
          <p id="case-code-help" className="max-w-[60ch] text-[0.9rem] text-muted">
            {t('save.caseCodeHelp')} {t('save.format')}
          </p>
          <div className="mt-1.5 flex flex-wrap items-start gap-3">
            <input
              id="case-code"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              maxLength={32}
              autoComplete="off"
              spellCheck={false}
              aria-describedby={`case-code-help${badFormat ? ' case-code-error' : ''}`}
              aria-invalid={badFormat || undefined}
              className={'h-11 w-56 rounded-md border bg-surface px-3 ' + (badFormat ? 'border-error' : 'border-field')}
            />
            <button
              type="button"
              onClick={onSave}
              disabled={badFormat || state === 'saving'}
              className="min-h-11 rounded-md border border-accent px-5 font-medium text-accent hover:bg-accent-soft disabled:border-rule disabled:text-muted"
            >
              {state === 'saving' ? t('save.saving') : t('save.button')}
            </button>
          </div>
          {badFormat && (
            <p id="case-code-error" className="mt-1 text-[0.9rem] font-medium text-error">
              {t('save.format')}
            </p>
          )}
          {state === 'failed' && (
            <p role="alert" className="mt-2 font-medium text-error">
              {t('save.failed')}
            </p>
          )}
        </>
      )}
    </section>
  )
}
