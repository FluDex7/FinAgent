import { useState } from 'react'
import type { KeyboardEvent } from 'react'
import { useAppStore } from '../store/useAppStore'

interface ComposerProps {
  onOpenAt: () => void
  onOpenUpload: () => void
}

function AtIcon() {
  return <span className="font-mono text-sm font-semibold">@</span>
}

function UploadIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

function StopIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
      <rect x="6" y="6" width="12" height="12" rx="2" />
    </svg>
  )
}

function SendIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <path d="M12 20V5m0 0-6 6m6-6 6 6" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

export function Composer({ onOpenAt, onOpenUpload }: ComposerProps) {
  const [input, setInput] = useState('')
  const isStreaming = useAppStore((s) => s.isStreaming)
  const sendMessage = useAppStore((s) => s.sendMessage)
  const stopStreaming = useAppStore((s) => s.stopStreaming)

  const canSend = input.trim().length > 0 && !isStreaming

  const handleSend = () => {
    if (!canSend) return
    const text = input.trim()
    setInput('')
    void sendMessage(text)
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex-shrink-0 px-6 pb-[18px]">
      <div className="relative mx-auto max-w-[760px]">
        <div
          className="rounded-2xl border p-2 pl-3.5"
          style={{ background: 'var(--color-surface)', borderColor: 'var(--color-border)', boxShadow: '0 2px 12px rgba(15,23,42,.04)' }}
        >
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
            placeholder="Спросите про свои траты…"
            className="max-h-[140px] w-full resize-none border-0 bg-transparent py-1.5 text-[14.5px] leading-relaxed outline-none"
            style={{ color: 'var(--color-ink)' }}
          />
          <div className="mt-0.5 flex items-center gap-1.5">
            <button
              type="button"
              onClick={onOpenAt}
              className="flex h-8 w-8 items-center justify-center rounded-[9px] border"
              style={{ borderColor: 'var(--color-border)', color: 'var(--color-muted)' }}
            >
              <AtIcon />
            </button>
            <button
              type="button"
              onClick={onOpenUpload}
              className="flex h-8 w-8 items-center justify-center rounded-[9px] border"
              style={{ borderColor: 'var(--color-border)', color: 'var(--color-muted)' }}
            >
              <UploadIcon />
            </button>
            <span className="ml-auto text-[11px]" style={{ color: 'var(--color-faint)' }}>
              Enter — отправить · Shift+Enter — перенос
            </span>
            {isStreaming ? (
              <button
                type="button"
                onClick={stopStreaming}
                className="flex h-[34px] w-[34px] items-center justify-center rounded-[10px] border"
                style={{ background: 'var(--color-surface-2)', borderColor: 'var(--color-border)', color: 'var(--color-ink)' }}
              >
                <StopIcon />
              </button>
            ) : (
              <button
                type="button"
                onClick={handleSend}
                disabled={!canSend}
                className="flex h-[34px] w-[34px] items-center justify-center rounded-[10px]"
                style={{
                  background: canSend ? 'var(--color-accent)' : 'var(--color-surface-2)',
                  color: canSend ? '#fff' : 'var(--color-faint)',
                }}
              >
                <SendIcon />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
