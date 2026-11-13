import { useTranslation } from 'react-i18next'
import { NavLink } from 'react-router'
import { LANGUAGES, rememberLanguage } from '../i18n'
import { useAuth } from '../lib/auth'

const NAV = [
  { to: '/', key: 'nav.calculator' },
  { to: '/about', key: 'nav.about' },
] as const

export function Header() {
  const { t, i18n } = useTranslation()
  const auth = useAuth()
  const nav = auth.enabled && auth.user ? [...NAV, { to: '/history', key: 'nav.history' } as const] : NAV
  const pill = (active: boolean) =>
    'inline-flex min-h-11 items-center rounded-md px-3 text-[0.95rem] ' +
    (active
      ? 'bg-accent-soft font-semibold text-accent-strong underline decoration-2 underline-offset-4'
      : 'text-muted hover:bg-page hover:text-ink')
  return (
    <header className="border-b border-rule bg-surface print:hidden">
      <div className="mx-auto flex w-full max-w-[76rem] flex-wrap items-end justify-between gap-x-8 gap-y-3 px-4 py-5 sm:px-8">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-accent-strong">{t('app.name')}</h1>
          <p className="mt-0.5 max-w-[60ch] text-[0.95rem] text-muted">{t('app.tagline')}</p>
        </div>
        <div className="flex flex-wrap items-center gap-x-6 gap-y-1">
          <nav aria-label={t('nav.main')} className="flex flex-wrap gap-1">
            {nav.map((item) => (
              <NavLink key={item.to} to={item.to} end={item.to === '/'} className={({ isActive }) => pill(isActive)}>
                {t(item.key)}
              </NavLink>
            ))}
            {auth.enabled && !auth.user && (
              <NavLink to="/login" className={({ isActive }) => pill(isActive)}>
                {t('auth.signIn')}
              </NavLink>
            )}
            {auth.enabled && auth.user && (
              <button
                type="button"
                onClick={() => void auth.signOut()}
                title={t('auth.signedInAs', { email: auth.user.email })}
                className={pill(false)}
              >
                {t('auth.signOut')}
              </button>
            )}
          </nav>
          <div role="group" aria-label={t('app.language')} className="flex flex-wrap gap-1 sm:border-l sm:border-rule sm:pl-5">
            {LANGUAGES.map((lang) => {
              const active = i18n.resolvedLanguage === lang.code
              return (
                <button
                  key={lang.code}
                  type="button"
                  lang={lang.code}
                  aria-pressed={active}
                  onClick={() => {
                    rememberLanguage(lang.code)
                    void i18n.changeLanguage(lang.code)
                  }}
                  className={pill(active)}
                >
                  {lang.name}
                </button>
              )
            })}
          </div>
        </div>
      </div>
    </header>
  )
}
