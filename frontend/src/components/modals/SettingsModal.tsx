import { useEffect, useState } from 'react'
import { listCategories, listMerchants, recategorizeMerchant } from '../../api/categorization'
import { useAppStore } from '../../store/useAppStore'
import type { CategoryOut, MerchantOut } from '../../api/types'

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

  const [categories, setCategories] = useState<CategoryOut[]>([])
  const [reviewMerchants, setReviewMerchants] = useState<MerchantOut[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    Promise.all([listCategories(), listMerchants(true)])
      .then(([cats, merchants]) => {
        if (cancelled) return
        setCategories(cats)
        setReviewMerchants(merchants)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const handleAssign = async (merchantId: string, categoryId: string) => {
    if (!categoryId) return
    await recategorizeMerchant(merchantId, categoryId)
    setReviewMerchants((prev) => prev.filter((m) => m.id !== merchantId))
  }

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
            Настройки
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
              Провайдер LLM
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
              Провайдер задаётся переменными окружения на сервере (LLM_PROVIDER, OPENAI_API_KEY / OLLAMA_HOST).
            </p>
          </div>

          <div>
            <div className="mb-2.5 flex items-center justify-between text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--color-faint)' }}>
              <span>Требуют категории</span>
              {!loading && <span>{reviewMerchants.length}</span>}
            </div>
            <div className="overflow-hidden rounded-xl border" style={{ borderColor: 'var(--color-border)', background: 'var(--color-surface)' }}>
              {loading && (
                <div className="px-3.5 py-4 text-center text-[12.5px]" style={{ color: 'var(--color-muted)' }}>
                  Загрузка…
                </div>
              )}
              {!loading && reviewMerchants.length === 0 && (
                <div className="px-3.5 py-4 text-center text-[12.5px]" style={{ color: 'var(--color-muted)' }}>
                  Все продавцы категоризированы
                </div>
              )}
              {reviewMerchants.map((merchant, i) => (
                <div
                  key={merchant.id}
                  className="flex items-center gap-2.5 px-3.5 py-2.5 text-[13px]"
                  style={{ borderTop: i > 0 ? '1px solid var(--color-border)' : undefined }}
                >
                  <span className="font-mono text-xs" style={{ color: 'var(--color-muted)' }}>
                    {merchant.displayName ?? merchant.normalizedKey}
                  </span>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" style={{ color: 'var(--color-faint)', flexShrink: 0 }}>
                    <path d="M5 12h14m0 0-5-5m5 5-5 5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  <select
                    defaultValue=""
                    onChange={(e) => handleAssign(merchant.id, e.target.value)}
                    className="ml-auto rounded-md border px-2 py-1 text-[12.5px]"
                    style={{ borderColor: 'var(--color-border)', background: 'var(--color-sheet)', color: 'var(--color-ink)' }}
                  >
                    <option value="" disabled>
                      Выбрать категорию
                    </option>
                    {categories.map((cat) => (
                      <option key={cat.id} value={cat.id}>
                        {cat.name}
                      </option>
                    ))}
                  </select>
                </div>
              ))}
            </div>
          </div>

          <div>
            <div className="mb-2.5 text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--color-faint)' }}>
              Тема
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
                ☀ Светлая
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
                ☾ Тёмная
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
