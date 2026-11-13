import { useTranslation } from 'react-i18next'
import type { ModelInfo, Prediction } from '../lib/spec'

/** The sentences for a result's warning codes. Field names, units and the study ranges
 *  come from the server; nothing is typed here. */
export function useWarningTexts(model: ModelInfo, prediction: Prediction): string[] {
  const { t } = useTranslation()
  return prediction.warnings.map((code) => {
    if (code !== 'OUTSIDE_TRAINING_RANGE') {
      return t(`warnings.${code}`, { defaultValue: t('warnings.unknown', { code }) })
    }
    const items = (prediction.outside_training_range ?? []).map((name) => {
      const feature = model.feature_spec.features.find((f) => f.api_field === name)
      const range = model.training_ranges?.[name]
      const unit = feature?.type === 'int' && feature.unit ? ` ${t(`units.${feature.unit}`)}` : ''
      const field = t(`fields.${name}`, { defaultValue: name })
      return range ? t('warnings.rangeItem', { field, min: range.min, max: range.max, unit }) : field
    })
    return t('warnings.OUTSIDE_TRAINING_RANGE', { list: items.join('; ') })
  })
}
