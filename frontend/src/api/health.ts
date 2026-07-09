import { get } from './client'
import type { HealthResponse } from './types'
import type { Language } from '../i18n'

export function getHealth(lang: Language): Promise<HealthResponse> {
  return get<HealthResponse>(`/health?lang=${lang}`)
}
