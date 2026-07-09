import { useEscapeKey } from '../hooks/useEscapeKey'
import { useT } from '../hooks/useT'

interface ConfirmDialogProps {
  title: string
  message: string
  confirmLabel?: string
  onConfirm: () => void
  onCancel: () => void
}

export function ConfirmDialog({ title, message, confirmLabel, onConfirm, onCancel }: ConfirmDialogProps) {
  const t = useT()
  useEscapeKey(onCancel)

  return (
    <div
      onClick={onCancel}
      className="animate-fa-pop fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: 'rgba(15,23,42,.45)', backdropFilter: 'blur(2px)' }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-[380px] max-w-[90vw] rounded-2xl border p-[22px]"
        style={{ background: 'var(--color-sheet)', borderColor: 'var(--color-border)', boxShadow: '0 24px 60px rgba(15,23,42,.3)' }}
      >
        <div className="mb-2 text-[15px] font-semibold" style={{ color: 'var(--color-ink)' }}>
          {title}
        </div>
        <p className="mb-[18px] text-[13px] leading-relaxed" style={{ color: 'var(--color-muted)' }}>
          {message}
        </p>
        <div className="flex justify-end gap-2.5">
          <button
            type="button"
            onClick={onCancel}
            className="rounded-[9px] border px-4 py-2 text-[13px] font-medium"
            style={{ background: 'var(--color-surface)', borderColor: 'var(--color-border)', color: 'var(--color-ink)' }}
          >
            {t('cancel')}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className="rounded-[9px] px-4 py-2 text-[13px] font-semibold text-white"
            style={{ background: 'var(--color-neg)' }}
          >
            {confirmLabel ?? t('delete')}
          </button>
        </div>
      </div>
    </div>
  )
}
