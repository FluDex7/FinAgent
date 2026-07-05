import { useAppStore } from '../store/useAppStore'

const STARTERS = [
  'На что я трачу больше всего?',
  'Сравни март и февраль',
  'Найди подписки',
  'Крупные разовые траты',
]

interface EmptyStateProps {
  onOpenUpload: () => void
}

export function EmptyState({ onOpenUpload }: EmptyStateProps) {
  const sendMessage = useAppStore((s) => s.sendMessage)

  return (
    <div className="flex flex-col items-center pt-9 text-center">
      <div
        className="flex h-[52px] w-[52px] items-center justify-center rounded-2xl"
        style={{ background: 'var(--color-accent)', boxShadow: '0 8px 24px var(--color-accent-soft)' }}
      >
        <svg width="27" height="27" viewBox="0 0 24 24" fill="none">
          <path d="M4 19V9M9 19V5M14 19v-7M19 19v-11" stroke="#fff" strokeWidth="2.4" strokeLinecap="round" />
        </svg>
      </div>

      <h1 className="mb-1.5 mt-5 text-2xl font-bold tracking-tight" style={{ color: 'var(--color-ink)' }}>
        О чём спросить свои выписки?
      </h1>
      <p className="mb-6 max-w-[440px] text-sm leading-relaxed" style={{ color: 'var(--color-muted)' }}>
        Загрузите банковскую выписку — PDF или CSV — и задайте вопрос обычным языком. Всё считается на вашей машине.
      </p>

      <button
        type="button"
        onClick={onOpenUpload}
        className="flex w-full max-w-[460px] flex-col items-center gap-2.5 rounded-2xl border-[1.5px] border-dashed p-6"
        style={{ borderColor: 'var(--color-border)', background: 'var(--color-surface)' }}
      >
        <svg width="26" height="26" viewBox="0 0 24 24" fill="none" style={{ color: 'var(--color-accent)' }}>
          <path d="M12 16V4m0 0-4 4m4-4 4 4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          <path d="M4 16v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
        <span className="text-sm font-semibold" style={{ color: 'var(--color-ink)' }}>
          Перетащите выписку сюда
        </span>
        <span className="text-[12.5px]" style={{ color: 'var(--color-muted)' }}>
          или нажмите, чтобы выбрать файл · PDF, CSV
        </span>
        <span className="mt-0.5 inline-flex items-center gap-1.5 text-[11.5px]" style={{ color: 'var(--color-faint)' }}>
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none">
            <rect x="5" y="11" width="14" height="9" rx="2" stroke="currentColor" strokeWidth="2" />
            <path d="M8 11V8a4 4 0 0 1 8 0v3" stroke="currentColor" strokeWidth="2" />
          </svg>
          всё обрабатывается локально, ничего не уходит наружу
        </span>
      </button>

      <div className="mt-6 flex max-w-[520px] flex-wrap justify-center gap-2.5">
        {STARTERS.map((text) => (
          <button
            key={text}
            type="button"
            onClick={() => sendMessage(text)}
            className="rounded-full border px-3.5 py-2 text-[13px]"
            style={{ background: 'var(--color-surface)', borderColor: 'var(--color-border)', color: 'var(--color-ink)' }}
          >
            {text}
          </button>
        ))}
      </div>
    </div>
  )
}
