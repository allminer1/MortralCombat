import { useTranslation } from 'react-i18next'
import type { ModelInfo } from '../lib/spec'

export function Footer({ model }: { model: ModelInfo | null }) {
  const { t } = useTranslation()
  const c = model?.citation
  return (
    <footer className="border-t border-rule bg-surface">
      <div className="mx-auto grid w-full max-w-[76rem] gap-x-12 gap-y-5 px-4 py-8 text-[0.9rem] text-muted sm:px-8 lg:grid-cols-[minmax(0,26rem)_minmax(0,1fr)]">
        <div className="space-y-2">
          <p className="font-medium text-ink">{t('footer.intendedUse')}</p>
          {model && <p>{t('footer.modelVersion', { version: model.model_version })}</p>}
          <p>
            <a href="/api/docs" className="text-accent underline underline-offset-2 hover:text-accent-strong">
              {t('footer.apiDocs')}
            </a>
          </p>
        </div>
        {c && (
          <div>
            <h2 className="font-medium text-ink">{t('footer.citation')}</h2>
            {/* Bibliographic reference: kept in the language of publication. */}
            <p lang="en" className="mt-1 max-w-[75ch]">
              {c.authors} {c.title} {c.journal} {c.year};{c.volume}:{c.article}.{' '}
              <a
                href={`https://doi.org/${c.doi}`}
                rel="noreferrer"
                className="text-accent underline underline-offset-2 hover:text-accent-strong"
              >
                doi:{c.doi}
              </a>
            </p>
          </div>
        )}
      </div>
    </footer>
  )
}
