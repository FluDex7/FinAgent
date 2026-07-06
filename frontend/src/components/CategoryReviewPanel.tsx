import { useEffect, useState } from 'react'
import { useEscapeKey } from '../hooks/useEscapeKey'
import { useAppStore } from '../store/useAppStore'

interface CategoryReviewPanelProps {
  onClose: () => void
}

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

export function CategoryReviewPanel({ onClose }: CategoryReviewPanelProps) {
  const categories = useAppStore((s) => s.categories)
  const merchants = useAppStore((s) => s.merchantsNeedingReview)
  const loading = useAppStore((s) => s.reviewLoading)
  const loadCategories = useAppStore((s) => s.loadCategories)
  const loadMerchantsNeedingReview = useAppStore((s) => s.loadMerchantsNeedingReview)
  const createCategory = useAppStore((s) => s.createCategory)
  const recategorizeMerchant = useAppStore((s) => s.recategorizeMerchant)

  const [creatingFor, setCreatingFor] = useState<string | null>(null)
  const [newCategoryName, setNewCategoryName] = useState('')
  const [newCategoryColor, setNewCategoryColor] = useState('#6d8dfa')
  useEscapeKey(onClose)

  useEffect(() => {
    void loadCategories()
    void loadMerchantsNeedingReview()
  }, [loadCategories, loadMerchantsNeedingReview])

  const handleAssign = (merchantId: string, categoryId: string) => {
    if (!categoryId) return
    void recategorizeMerchant(merchantId, categoryId)
  }

  const handleCreateCategory = async (merchantId: string) => {
    const name = newCategoryName.trim()
    if (!name) return
    const category = await createCategory(name, newCategoryColor)
    setCreatingFor(null)
    setNewCategoryName('')
    void recategorizeMerchant(merchantId, category.id)
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
          onClick={onClose}
          className="ml-auto flex h-8 w-8 items-center justify-center rounded-lg"
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
            merchants.map((merchant) => {
              const isCreating = creatingFor === merchant.id
              return (
                <div
                  key={merchant.id}
                  className="mb-3 rounded-[14px] border p-3.5"
                  style={{ background: 'var(--color-surface)', borderColor: 'var(--color-border)' }}
                >
                  <div className="flex items-center gap-2.5">
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
                    {!isCreating && (
                      <select
                        defaultValue=""
                        onChange={(e) => handleAssign(merchant.id, e.target.value)}
                        className="rounded-md border px-2 py-1.5 text-[12.5px]"
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
                    )}
                    <button
                      type="button"
                      onClick={() => {
                        setCreatingFor(isCreating ? null : merchant.id)
                        setNewCategoryName('')
                      }}
                      className="flex flex-shrink-0 items-center gap-1 rounded-md border px-2 py-1.5 text-[12px] font-medium"
                      style={{ borderColor: 'var(--color-border)', color: 'var(--color-accent)' }}
                    >
                      <PlusIcon />
                      Новая
                    </button>
                  </div>
                  {isCreating && (
                    <div className="mt-2.5 flex items-center gap-2 border-t pt-2.5" style={{ borderColor: 'var(--color-border)' }}>
                      <input
                        type="color"
                        value={newCategoryColor}
                        onChange={(e) => setNewCategoryColor(e.target.value)}
                        className="h-8 w-8 flex-shrink-0 cursor-pointer rounded-md border p-0.5"
                        style={{ borderColor: 'var(--color-border)' }}
                      />
                      <input
                        autoFocus
                        value={newCategoryName}
                        onChange={(e) => setNewCategoryName(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') void handleCreateCategory(merchant.id)
                          if (e.key === 'Escape') setCreatingFor(null)
                        }}
                        placeholder="Название категории"
                        className="min-w-0 flex-1 rounded-md border px-2.5 py-1.5 text-[12.5px] outline-none"
                        style={{ borderColor: 'var(--color-accent)', background: 'var(--color-sheet)', color: 'var(--color-ink)' }}
                      />
                      <button
                        type="button"
                        onClick={() => void handleCreateCategory(merchant.id)}
                        disabled={!newCategoryName.trim()}
                        className="flex-shrink-0 rounded-md px-3 py-1.5 text-[12.5px] font-semibold text-white"
                        style={{ background: 'var(--color-accent)', opacity: newCategoryName.trim() ? 1 : 0.5 }}
                      >
                        Добавить
                      </button>
                    </div>
                  )}
                </div>
              )
            })}
        </div>
      </div>
    </div>
  )
}
