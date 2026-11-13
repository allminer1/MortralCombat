import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router'
import { About } from './components/About'
import { Calculator } from './components/Calculator'
import { Footer } from './components/Footer'
import { Header } from './components/Header'
import { History, HistoryItem } from './components/History'
import { Login } from './components/Login'
import { Report } from './components/Report'
import { getModel } from './lib/api'
import { AuthProvider, useAuth } from './lib/auth'
import { layoutMatches } from './lib/fields'
import { SessionProvider } from './lib/session'
import type { ModelInfo } from './lib/spec'

type Load = { state: 'loading' } | { state: 'failed' } | { state: 'ready'; model: ModelInfo }

export default function App() {
  const { t } = useTranslation()
  const [load, setLoad] = useState<Load>({ state: 'loading' })

  const fetchModel = useCallback(() => {
    getModel().then(
      (model) => setLoad({ state: 'ready', model }),
      () => setLoad({ state: 'failed' }),
    )
  }, [])
  useEffect(fetchModel, [fetchModel])
  const retry = () => {
    setLoad({ state: 'loading' })
    fetchModel()
  }

  const model = load.state === 'ready' ? load.model : null
  const usable = model !== null && layoutMatches(model.feature_spec.features)

  return (
    <BrowserRouter>
      <AuthProvider>
      <SessionProvider>
        <div className="flex min-h-screen flex-col print:min-h-0">
          <Header />
          <main className="mx-auto w-full max-w-[76rem] flex-1 px-4 pb-16 sm:px-8 print:max-w-none print:p-0">
            {load.state === 'loading' && (
              <p role="status" className="py-16 text-muted">
                {t('app.loading')}
              </p>
            )}
            {load.state === 'failed' && (
              <div role="alert" className="max-w-xl py-16">
                <p>{t('app.loadFailed')}</p>
                <button
                  type="button"
                  onClick={retry}
                  className="mt-4 rounded-md border border-accent px-4 py-2 font-medium text-accent hover:bg-accent-soft"
                >
                  {t('app.retry')}
                </button>
              </div>
            )}
            {model !== null && !usable && (
              <p role="alert" className="max-w-xl py-16">
                {t('app.configMismatch')}
              </p>
            )}
            {model !== null && usable && (
              <Pages model={model} />
            )}
          </main>
          <Footer model={model} />
        </div>
      </SessionProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}

/** Account pages exist only when the server has the feature on; history needs a session. */
function Pages({ model }: { model: ModelInfo }) {
  const auth = useAuth()
  const signedIn = auth.enabled === true && auth.user !== null
  return (
    <Routes>
      <Route path="/" element={<Calculator model={model} />} />
      <Route path="/about" element={<About model={model} />} />
      <Route path="/report" element={<Report model={model} />} />
      {auth.enabled === true && <Route path="/login" element={<Login />} />}
      {auth.enabled === true && (
        <Route path="/history" element={signedIn ? <History /> : <Navigate to="/login" replace />} />
      )}
      {auth.enabled === true && (
        <Route
          path="/history/:id"
          element={signedIn ? <HistoryItem model={model} /> : <Navigate to="/login" replace />}
        />
      )}
      {/* While the feature state is loading, do not redirect account links away. */}
      {auth.enabled !== null && <Route path="*" element={<Navigate to="/" replace />} />}
    </Routes>
  )
}
