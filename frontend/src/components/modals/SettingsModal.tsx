import { useEscapeKey } from '../../hooks/useEscapeKey'
import { useT } from '../../hooks/useT'
import { useAppStore } from '../../store/useAppStore'

interface SettingsModalProps {
  onClose: () => void
}

function CloseIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

export function SettingsModal({ onClose }: SettingsModalProps) {
  const health = useAppStore((s) => s.health)
  const theme = useAppStore((s) => s.theme)
  const setTheme = useAppStore((s) => s.setTheme)
  const language = useAppStore((s) => s.language)
  const setLanguage = useAppStore((s) => s.setLanguage)
  const t = useT()
  useEscapeKey(onClose)

  return (
    <div
      onClick={onClose}
      className="animate-fa-pop fixed inset-0 z-40 flex items-center justify-center"
      style={{ background: 'rgba(15,23,42,.45)', backdropFilter: 'blur(2px)' }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="max-h-[86vh] w-[560px] max-w-[94vw] overflow-y-auto rounded-[18px] border"
        style={{ background: 'var(--color-sheet)', borderColor: 'var(--color-border)', boxShadow: '0 24px 60px rgba(15,23,42,.3)' }}
      >
        <div
          className="sticky top-0 flex items-center border-b px-[22px] py-[14px]"
          style={{ borderColor: 'var(--color-border)', background: 'var(--color-sheet)' }}
        >
          <span className="text-[15px] font-semibold" style={{ color: 'var(--color-ink)' }}>
            {t('settings')}
          </span>
          <button
            type="button"
            onClick={onClose}
            className="ml-auto flex h-[30px] w-[30px] items-center justify-center rounded-lg"
            style={{ color: 'var(--color-muted)' }}
          >
            <CloseIcon />
          </button>
        </div>

        <div className="flex flex-col gap-6 px-[22px] py-5">
          <div>
            <div className="mb-2.5 text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--color-faint)' }}>
              {t('llmProvider')}
            </div>
            <div className="flex items-center gap-2.5 rounded-[10px] border px-3 py-2.5" style={{ borderColor: 'var(--color-border)', background: 'var(--color-surface)' }}>
              <span
                className="h-2 w-2 flex-shrink-0 rounded-full"
                style={{ background: health?.llm.ok ? 'var(--color-pos)' : 'var(--color-neg)' }}
              />
              <span className="text-[13.5px] font-semibold" style={{ color: 'var(--color-ink)' }}>
                {health?.llm.provider === 'ollama' ? 'Ollama' : 'OpenAI'}
              </span>
              <span className="text-xs" style={{ color: 'var(--color-muted)' }}>
                {health?.llm.model}
              </span>
              <span className="ml-auto text-right text-[11.5px]" style={{ color: 'var(--color-faint)' }}>
                {health?.llm.detail}
              </span>
            </div>
            <p className="mt-2 text-[11.5px]" style={{ color: 'var(--color-faint)' }}>
              {t('llmProviderNote')}
            </p>
          </div>

          <div>
            <div className="mb-2.5 text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--color-faint)' }}>
              {t('theme')}
            </div>
            <div className="flex max-w-[280px] gap-2">
              <button
                type="button"
                onClick={() => setTheme('light')}
                className="flex-1 rounded-[10px] border px-3 py-2 text-[13px] font-medium"
                style={{
                  borderColor: theme === 'light' ? 'var(--color-accent)' : 'var(--color-border)',
                  color: theme === 'light' ? 'var(--color-accent)' : 'var(--color-muted)',
                  background: theme === 'light' ? 'var(--color-accent-soft)' : 'var(--color-surface)',
                }}
              >
                {t('themeLight')}
              </button>
              <button
                type="button"
                onClick={() => setTheme('dark')}
                className="flex-1 rounded-[10px] border px-3 py-2 text-[13px] font-medium"
                style={{
                  borderColor: theme === 'dark' ? 'var(--color-accent)' : 'var(--color-border)',
                  color: theme === 'dark' ? 'var(--color-accent)' : 'var(--color-muted)',
                  background: theme === 'dark' ? 'var(--color-accent-soft)' : 'var(--color-surface)',
                }}
              >
                {t('themeDark')}
              </button>
            </div>
          </div>

          <div>
            <div className="mb-2.5 text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--color-faint)' }}>
              {t('language')}
            </div>
            <div className="flex max-w-[280px] gap-2">
              {(
                [
                  ['en', 'English'],
                  ['ru', 'Русский'],
                ] as const
              ).map(([value, label]) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setLanguage(value)}
                  className="flex-1 rounded-[10px] border px-3 py-2 text-[13px] font-medium"
                  style={{
                    borderColor: language === value ? 'var(--color-accent)' : 'var(--color-border)',
                    color: language === value ? 'var(--color-accent)' : 'var(--color-muted)',
                    background: language === value ? 'var(--color-accent-soft)' : 'var(--color-surface)',
                  }}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
