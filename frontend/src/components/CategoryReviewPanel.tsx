import { useEffect, useState } from 'react'
import { useEscapeKey } from '../hooks/useEscapeKey'
import { useAppStore } from '../store/useAppStore'

interface CategoryReviewPanelProps {
  onClose: () => void
}

const COLOR_PRESETS = [
  '#2b8fef',
  '#22b8a6',
  '#f0a94e',
  '#ee7d8c',
  '#94a3b8',
  '#6d8dfa',
  '#1f9d6b',
  '#a855f7',
]

function BackIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
      <path d="M15 5l-7 7 7 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function CloseIcon() {
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
      <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

function PlusIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
      <path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

function CheckIcon() {
  return (
    <svg width="10" height="10" viewBox="0 0 24 24" fill="none">
      <path d="M5 12l5 5L20 7" stroke="#fff" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

interface NewCategoryDialogProps {
  onClose: () => void
  onCreate: (name: string, color: string) => Promise<void>
}

function NewCategoryDialog({ onClose, onCreate }: NewCategoryDialogProps) {
  const [name, setName] = useState('')
  const [color, setColor] = useState(COLOR_PRESETS[0])
  const [saving, setSaving] = useState(false)
  useEscapeKey(onClose)

  const submit = async () => {
    const trimmed = name.trim()
    if (!trimmed || saving) return
    setSaving(true)
    await onCreate(trimmed, color)
    setSaving(false)
  }

  return (
    <div
      onClick={onClose}
      className="animate-fa-pop fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: 'rgba(15,23,42,.45)', backdropFilter: 'blur(2px)' }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-[360px] max-w-[90vw] rounded-2xl border p-[22px]"
        style={{ background: 'var(--color-sheet)', borderColor: 'var(--color-border)', boxShadow: '0 24px 60px rgba(15,23,42,.3)' }}
      >
        <div className="mb-4 text-[15px] font-semibold" style={{ color: 'var(--color-ink)' }}>
          Новая категория
        </div>

        <label className="mb-1.5 block text-[12px] font-medium" style={{ color: 'var(--color-muted)' }}>
          Название
        </label>
        <input
          autoFocus
          value={name}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && void submit()}
          placeholder="Например, «Подписки»"
          className="mb-4 w-full rounded-[10px] border px-3 py-2 text-[13.5px] outline-none"
          style={{ borderColor: 'var(--color-accent)', background: 'var(--color-surface)', color: 'var(--color-ink)' }}
        />

        <label className="mb-2 block text-[12px] font-medium" style={{ color: 'var(--color-muted)' }}>
          Цвет
        </label>
        <div className="mb-5 flex flex-wrap gap-2">
          {COLOR_PRESETS.map((preset) => (
            <button
              key={preset}
              type="button"
              onClick={() => setColor(preset)}
              className="flex h-7 w-7 items-center justify-center rounded-full"
              style={{ background: preset, boxShadow: color === preset ? '0 0 0 2px var(--color-sheet), 0 0 0 4px var(--color-accent)' : undefined }}
            >
              {color === preset && <CheckIcon />}
            </button>
          ))}
        </div>

        <div className="flex justify-end gap-2.5">
          <button
            type="button"
            onClick={onClose}
            className="rounded-[9px] border px-4 py-2 text-[13px] font-medium"
            style={{ background: 'var(--color-surface)', borderColor: 'var(--color-border)', color: 'var(--color-ink)' }}
          >
            Отмена
          </button>
          <button
            type="button"
            onClick={() => void submit()}
            disabled={!name.trim() || saving}
            className="rounded-[9px] px-4 py-2 text-[13px] font-semibold text-white"
            style={{ background: 'var(--color-accent)', opacity: name.trim() && !saving ? 1 : 0.5 }}
          >
            Создать
          </button>
        </div>
      </div>
    </div>
  )
}

export function CategoryReviewPanel({ onClose }: CategoryReviewPanelProps) {
  const categories = useAppStore((s) => s.categories)
  const merchants = useAppStore((s) => s.merchantsNeedingReview)
  const loading = useAppStore((s) => s.reviewLoading)
  const loadCategories = useAppStore((s) => s.loadCategories)
  const loadMerchantsNeedingReview = useAppStore((s) => s.loadMerchantsNeedingReview)
  const createCategory = useAppStore((s) => s.createCategory)
  const recategorizeMerchant = useAppStore((s) => s.recategorizeMerchant)

  const [createOpen, setCreateOpen] = useState(false)
  const [pendingAssignFor, setPendingAssignFor] = useState<string | null>(null)
  useEscapeKey(onClose)

  useEffect(() => {
    void loadCategories()
    void loadMerchantsNeedingReview()
  }, [loadCategories, loadMerchantsNeedingReview])

  const handleAssign = (merchantId: string, categoryId: string) => {
    if (!categoryId) return
    void recategorizeMerchant(merchantId, categoryId)
  }

  const handleCreateCategory = async (name: string, color: string) => {
    const category = await createCategory(name, color)
    setCreateOpen(false)
    if (pendingAssignFor) {
      void recategorizeMerchant(pendingAssignFor, category.id)
      setPendingAssignFor(null)
    }
  }

  return (
    <div
      className="animate-fa-in absolute inset-0 z-30 flex flex-col"
      style={{ background: 'var(--color-panel)', backdropFilter: 'blur(30px) saturate(140%)' }}
    >
      <header
        className="flex h-[54px] flex-shrink-0 items-center gap-3 border-b px-[18px]"
        style={{ borderColor: 'var(--color-border)' }}
      >
        <button
          type="button"
          onClick={onClose}
          className="inline-flex items-center gap-1.5 rounded-[9px] border px-2.5 py-1.5 text-[13px]"
          style={{ borderColor: 'var(--color-border)', color: 'var(--color-muted)' }}
        >
          <BackIcon />В чат
        </button>
        <span className="text-sm font-semibold" style={{ color: 'var(--color-ink)' }}>
          Требуют категории
        </span>
        <button
          type="button"
          onClick={() => {
            setPendingAssignFor(null)
            setCreateOpen(true)
          }}
          className="ml-auto inline-flex items-center gap-1.5 rounded-[9px] border px-2.5 py-1.5 text-[13px] font-medium"
          style={{ borderColor: 'var(--color-border)', color: 'var(--color-accent)' }}
        >
          <PlusIcon />
          Новая категория
        </button>
        <button
          type="button"
          onClick={onClose}
          className="flex h-8 w-8 items-center justify-center rounded-lg"
          style={{ color: 'var(--color-muted)' }}
        >
          <CloseIcon />
        </button>
      </header>

      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-[760px] p-6">
          {loading && (
            <div className="py-10 text-center text-sm" style={{ color: 'var(--color-muted)' }}>
              Загрузка…
            </div>
          )}
          {!loading && merchants.length === 0 && (
            <div className="py-10 text-center text-sm" style={{ color: 'var(--color-muted)' }}>
              Все продавцы категоризированы
            </div>
          )}
          {!loading &&
            merchants.map((merchant) => (
              <div
                key={merchant.id}
                className="mb-3 flex items-center gap-2.5 rounded-[14px] border p-3.5"
                style={{ background: 'var(--color-surface)', borderColor: 'var(--color-border)' }}
              >
                <div className="min-w-0 flex-1">
                  <div className="overflow-hidden text-ellipsis whitespace-nowrap text-[13.5px] font-semibold" style={{ color: 'var(--color-ink)' }}>
                    {merchant.displayName ?? merchant.normalizedKey}
                  </div>
                  {merchant.sampleDescription && (
                    <div className="mt-0.5 overflow-hidden text-ellipsis whitespace-nowrap text-[11.5px]" style={{ color: 'var(--color-faint)' }}>
                      {merchant.sampleDescription}
                      {merchant.transactionCount > 1 && ` · ${merchant.transactionCount} операций`}
                    </div>
                  )}
                </div>
                <select
                  defaultValue=""
                  onChange={(e) => {
                    if (e.target.value === '__new__') {
                      setPendingAssignFor(merchant.id)
                      setCreateOpen(true)
                      e.target.value = ''
                      return
                    }
                    handleAssign(merchant.id, e.target.value)
                  }}
                  className="flex-shrink-0 rounded-md border px-2 py-1.5 text-[12.5px]"
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
                  <option value="__new__">+ Новая категория…</option>
                </select>
              </div>
            ))}
        </div>
      </div>

      {createOpen && (
        <NewCategoryDialog
          onClose={() => {
            setCreateOpen(false)
            setPendingAssignFor(null)
          }}
          onCreate={handleCreateCategory}
        />
      )}
    </div>
  )
}
