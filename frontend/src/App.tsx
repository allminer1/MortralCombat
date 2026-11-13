import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Calculator } from './components/Calculator'
import { Footer } from './components/Footer'
import { Header } from './components/Header'
import { getModel } from './lib/api'
import { layoutMatches } from './lib/fields'
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
    <div className="flex min-h-screen flex-col">
      <Header />
      <main className="mx-auto w-full max-w-[76rem] flex-1 px-4 pb-16 sm:px-8">
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
        {model !== null && usable && <Calculator model={model} />}
      </main>
      <Footer model={model} />
    </div>
  )
}
