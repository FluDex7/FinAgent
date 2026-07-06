import { useEffect, useRef, useState } from 'react'
import type { ChangeEvent, KeyboardEvent } from 'react'
import { useAppStore } from '../store/useAppStore'
import { AtPicker } from './AtPicker'
import type { Ref } from '../api/types'

interface ComposerProps {
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

function RemoveIcon() {
  return (
    <svg width="11" height="11" viewBox="0 0 24 24" fill="none">
      <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" />
    </svg>
  )
}

export function Composer({ onOpenUpload }: ComposerProps) {
  const [input, setInput] = useState('')
  const [atOpen, setAtOpen] = useState(false)
  const [pendingRefs, setPendingRefs] = useState<Ref[]>([])
  const isStreaming = useAppStore((s) => s.isStreaming)
  const sendMessage = useAppStore((s) => s.sendMessage)
  const stopStreaming = useAppStore((s) => s.stopStreaming)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const canSend = input.trim().length > 0 && !isStreaming

  // Grow the textarea to fit its content up to max-h, then let it scroll
  // internally beyond that — like Claude's composer — instead of clipping
  // to a single visible line.
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${el.scrollHeight}px`
  }, [input])

  const handleSend = () => {
    if (!canSend) return
    const text = input.trim()
    const refs = pendingRefs
    setInput('')
    setPendingRefs([])
    void sendMessage(text, refs)
  }

  const handleInputChange = (e: ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value
    // Typing "@" at the start or after whitespace opens the same picker the
    // button does, instead of leaving it as a dead character in the message —
    // it'll turn into a ref chip once something is picked.
    const justTypedAt = value.length === input.length + 1 && value.endsWith('@')
    const charBeforeAt = value.slice(-2, -1)
    if (justTypedAt && (charBeforeAt === '' || /\s/.test(charBeforeAt))) {
      setInput(value.slice(0, -1))
      setAtOpen(true)
      return
    }
    setInput(value)
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const addRef = (ref: Ref) => {
    setPendingRefs((prev) => (prev.some((r) => r.path === ref.path) ? prev : [...prev, ref]))
    setAtOpen(false)
  }

  const removeRef = (path: string) => {
    setPendingRefs((prev) => prev.filter((r) => r.path !== path))
  }

  return (
    <div className="flex-shrink-0 px-6 pb-[18px]">
      <div className="relative mx-auto max-w-[760px]">
        {atOpen && <AtPicker onPick={addRef} onClose={() => setAtOpen(false)} />}

        <div
          className="rounded-2xl border p-2 pl-3.5"
          style={{ background: 'var(--color-surface)', borderColor: 'var(--color-border)', boxShadow: '0 2px 12px rgba(15,23,42,.04)' }}
        >
          {pendingRefs.length > 0 && (
            <div className="flex flex-wrap gap-1.5 px-0 py-1">
              {pendingRefs.map((ref) => (
                <span
                  key={ref.path}
                  className="inline-flex items-center gap-1.5 rounded-md py-1 pl-2 pr-1 font-mono text-[11.5px]"
                  style={{ color: 'var(--color-accent)', background: 'var(--color-accent-soft)' }}
                >
                  @{ref.path}
                  <button type="button" onClick={() => removeRef(ref.path)} className="flex" style={{ color: 'var(--color-accent)' }}>
                    <RemoveIcon />
                  </button>
                </span>
              ))}
            </div>
          )}
          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            rows={1}
            placeholder="Спросите про свои траты…"
            className="max-h-[200px] w-full resize-none overflow-y-auto border-0 bg-transparent py-1.5 text-[14.5px] leading-relaxed outline-none"
            style={{ color: 'var(--color-ink)' }}
          />
          <div className="mt-0.5 flex items-center gap-1.5">
            <button
              type="button"
              onClick={() => setAtOpen((v) => !v)}
              className="flex h-8 w-8 items-center justify-center rounded-[9px] border"
              style={{
                borderColor: atOpen ? 'var(--color-accent)' : 'var(--color-border)',
                color: atOpen ? 'var(--color-accent)' : 'var(--color-muted)',
              }}
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
