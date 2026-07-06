import { useEffect, useState } from 'react'
import { listCategories, listMerchants } from '../api/categorization'
import { getStatement, getStatementTransactions } from '../api/statements'
import { useEscapeKey } from '../hooks/useEscapeKey'
import type { CategoryOut, MerchantOut, StatementOut, TransactionOut } from '../api/types'

interface DocumentViewerProps {
  statementId: string
  onClose: () => void
}

const STATUS_LABEL: Record<string, string> = {
  parsed: 'Распарсено',
  parsing: 'Обрабатывается',
  new: 'Новая',
  error: 'Ошибка',
}

function formatDate(value: string): string {
  const d = new Date(value)
  return d.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

function formatAmount(value: number): string {
  return new Intl.NumberFormat('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(value)
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

export function DocumentViewer({ statementId, onClose }: DocumentViewerProps) {
  const [statement, setStatement] = useState<StatementOut | null>(null)
  const [transactions, setTransactions] = useState<TransactionOut[]>([])
  const [categories, setCategories] = useState<CategoryOut[]>([])
  const [merchants, setMerchants] = useState<MerchantOut[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  useEscapeKey(onClose)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    Promise.all([getStatement(statementId), listCategories(), listMerchants(false)])
      .then(async ([stmt, cats, merch]) => {
        if (cancelled) return
        setStatement(stmt)
        setCategories(cats)
        setMerchants(merch)
        const txs = await getStatementTransactions(statementId, stmt.transactionCount, 0)
        if (cancelled) return
        setTransactions(txs)
      })
      .catch((err) => {
        if (!cancelled) setError((err as Error).message)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [statementId])

  const categoryById = new Map(categories.map((c) => [c.id, c]))
  const merchantById = new Map(merchants.map((m) => [m.id, m]))

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
        <div className="flex min-w-0 flex-col">
          <span className="overflow-hidden text-ellipsis whitespace-nowrap text-sm font-semibold" style={{ color: 'var(--color-ink)' }}>
            {statement?.filename ?? '…'}
          </span>
          <span className="overflow-hidden text-ellipsis whitespace-nowrap text-[11.5px]" style={{ color: 'var(--color-muted)' }}>
            {statement?.bankName ?? statement?.folderPath ?? ''}
          </span>
        </div>
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
          {error && (
            <div className="rounded-[10px] border px-3 py-2 text-[12.5px]" style={{ borderColor: 'var(--color-neg)', color: 'var(--color-neg)' }}>
              {error}
            </div>
          )}
          {statement && !loading && (
            <>
              <div className="mb-5 flex gap-2.5">
                <span
                  className="inline-flex items-center gap-1.5 rounded-[10px] border px-3 py-1.5 text-[12.5px]"
                  style={{ background: 'var(--color-surface)', borderColor: 'var(--color-border)' }}
                >
                  <span
                    className="h-1.5 w-1.5 rounded-full"
                    style={{ background: statement.status === 'parsed' ? 'var(--color-pos)' : 'var(--color-neg)' }}
                  />
                  {STATUS_LABEL[statement.status] ?? statement.status}
                </span>
                {statement.dateFrom && statement.dateTo && (
                  <span
                    className="inline-flex items-center rounded-[10px] border px-3 py-1.5 text-[12.5px]"
                    style={{ background: 'var(--color-surface)', borderColor: 'var(--color-border)', color: 'var(--color-muted)' }}
                  >
                    Период: {formatDate(statement.dateFrom)} – {formatDate(statement.dateTo)}
                  </span>
                )}
              </div>

              <div className="overflow-hidden rounded-[14px] border" style={{ background: 'var(--color-surface)', borderColor: 'var(--color-border)' }}>
                <div
                  className="grid px-4 py-2.5 text-[11px] uppercase tracking-wide"
                  style={{ gridTemplateColumns: '1fr 1.6fr 1.2fr 0.9fr', color: 'var(--color-faint)' }}
                >
                  <span>Дата</span>
                  <span>Продавец</span>
                  <span>Категория</span>
                  <span className="text-right">Сумма</span>
                </div>
                {transactions.map((tx) => {
                  const merchant = tx.merchantId ? merchantById.get(tx.merchantId) : undefined
                  const category = tx.categoryId ? categoryById.get(tx.categoryId) : undefined
                  return (
                    <div
                      key={tx.id}
                      className="grid items-center border-t px-4 py-2.5 text-[13px]"
                      style={{ gridTemplateColumns: '1fr 1.6fr 1.2fr 0.9fr', borderColor: 'var(--color-border)' }}
                    >
                      <span className="font-mono text-xs" style={{ color: 'var(--color-muted)' }}>
                        {formatDate(tx.date)}
                      </span>
                      <span className="font-medium" style={{ color: 'var(--color-ink)' }}>
                        {merchant?.displayName ?? merchant?.normalizedKey ?? tx.rawDescription}
                      </span>
                      <span className="flex items-center" style={{ color: 'var(--color-muted)' }}>
                        {category && (
                          <span
                            className="mr-1.5 inline-block h-1.5 w-1.5 flex-shrink-0 rounded-sm"
                            style={{ background: category.color }}
                          />
                        )}
                        {category?.name ?? '—'}
                      </span>
                      <span
                        className="text-right font-mono"
                        style={{ color: tx.amount < 0 ? 'var(--color-neg)' : 'var(--color-pos)' }}
                      >
                        {formatAmount(tx.amount)}
                      </span>
                    </div>
                  )
                })}
              </div>
              <p className="mt-3.5 text-center text-xs" style={{ color: 'var(--color-faint)' }}>
                Всего транзакций: {transactions.length}
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
