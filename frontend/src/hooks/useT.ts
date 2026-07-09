import { useCallback } from 'react'
import { LOCALES, translate } from '../i18n'
import type { TranslateParams, TranslationKey } from '../i18n'
import { useAppStore } from '../store/useAppStore'

export function useT() {
  const language = useAppStore((s) => s.language)
  return useCallback(
    (key: TranslationKey, params?: TranslateParams) => translate(language, key, params),
    [language],
  )
}

// Intl locale matching the current UI language, for date/number formatting.
export function useLocale(): string {
  return LOCALES[useAppStore((s) => s.language)]
}
