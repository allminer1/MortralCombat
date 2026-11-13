import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Navigate, useLocation, useNavigate } from 'react-router'
import { ApiError } from '../lib/api'
import { useAuth } from '../lib/auth'

export function Login() {
  const { t } = useTranslation()
  const auth = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const ended = (location.state as { ended?: boolean } | null)?.ended === true
  const [busy, setBusy] = useState(false)
  const [failure, setFailure] = useState<string | null>(null)

  if (auth.user) return <Navigate to="/" replace />

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    setBusy(true)
    setFailure(null)
    try {
      await auth.signIn(String(data.get('email') ?? ''), String(data.get('password') ?? ''))
      void navigate('/', { replace: true })
    } catch (error) {
      const code = error instanceof ApiError ? error.code : 'server'
      setFailure(code === 'invalid_credentials' || code === 'validation' ? 'auth.invalid_credentials' : `errors.${code}`)
    } finally {
      setBusy(false)
    }
  }
  const field = 'mt-1.5 h-11 w-full rounded-md border border-field bg-surface px-3 text-lg'

  return (
    <div className="max-w-sm pt-10">
      <h2 className="text-2xl font-semibold tracking-tight">{t('auth.title')}</h2>
      {ended && (
        <p role="status" className="mt-3 rounded-md border border-notice bg-notice-soft px-3 py-2 font-medium text-notice">
          {t('auth.sessionEnded')}
        </p>
      )}
      <form onSubmit={onSubmit} className="mt-5 space-y-4">
        <div>
          <label htmlFor="email" className="block font-medium">
            {t('auth.email')}
          </label>
          <input id="email" name="email" type="email" autoComplete="username" required className={field} />
        </div>
        <div>
          <label htmlFor="password" className="block font-medium">
            {t('auth.password')}
          </label>
          <input id="password" name="password" type="password" autoComplete="current-password" required className={field} />
        </div>
        {failure && (
          <p role="alert" className="rounded-md border border-error px-3 py-2 font-medium text-error">
            {t(failure)}
          </p>
        )}
        <button
          type="submit"
          disabled={busy}
          className="min-h-12 rounded-md bg-accent px-7 text-lg font-semibold text-white hover:bg-accent-strong disabled:bg-rule disabled:text-muted"
        >
          {busy ? t('auth.signingIn') : t('auth.signIn')}
        </button>
      </form>
      <p className="mt-6 text-[0.95rem] text-muted">{t('auth.inviteOnly')}</p>
    </div>
  )
}
