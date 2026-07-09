import { useRef, useState } from 'react'
import type { DragEvent } from 'react'
import { uploadStatement } from '../../api/statements'
import { useEscapeKey } from '../../hooks/useEscapeKey'
import { useT } from '../../hooks/useT'
import { useAppStore } from '../../store/useAppStore'

interface UploadModalProps {
  onClose: () => void
}

type Phase = 'idle' | 'uploading' | 'done' | 'error'

function CloseIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

function UploadIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" style={{ color: 'var(--color-accent)' }}>
      <path d="M12 16V4m0 0-4 4m4-4 4 4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M4 16v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

function FileIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" style={{ color: 'var(--color-accent)' }}>
      <path d="M6 3h8l4 4v14H6V3Z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
      <path d="M14 3v4h4" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
    </svg>
  )
}

export function UploadModal({ onClose }: UploadModalProps) {
  const t = useT()
  const [phase, setPhase] = useState<Phase>('idle')
  const [file, setFile] = useState<File | null>(null)
  const [folder, setFolder] = useState('')
  const [errorMessage, setErrorMessage] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)
  const loadDocuments = useAppStore((s) => s.loadDocuments)
  useEscapeKey(onClose)

  const runUpload = async (selected: File) => {
    setFile(selected)
    setPhase('uploading')
    try {
      await uploadStatement(selected, folder.trim())
      await loadDocuments()
      setPhase('done')
    } catch (err) {
      setErrorMessage((err as Error).message)
      setPhase('error')
    }
  }

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    const dropped = e.dataTransfer.files[0]
    if (dropped) void runUpload(dropped)
  }

  return (
    <div
      onClick={onClose}
      className="animate-fa-pop fixed inset-0 z-40 flex items-center justify-center"
      style={{ background: 'rgba(15,23,42,.45)', backdropFilter: 'blur(2px)' }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-[480px] max-w-[92vw] overflow-hidden rounded-[18px] border"
        style={{ background: 'var(--color-sheet)', borderColor: 'var(--color-border)', boxShadow: '0 24px 60px rgba(15,23,42,.3)' }}
      >
        <div className="flex items-center border-b px-5 py-[14px]" style={{ borderColor: 'var(--color-border)' }}>
          <span className="text-[15px] font-semibold" style={{ color: 'var(--color-ink)' }}>
            {t('uploadTitle')}
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

        <div className="p-5">
          {phase === 'idle' && (
            <>
              <div className="mb-3 flex items-center gap-2.5 rounded-[10px] border px-3 py-2" style={{ borderColor: 'var(--color-border)' }}>
                <span className="text-[12.5px]" style={{ color: 'var(--color-muted)' }}>
                  {t('folder')}
                </span>
                <input
                  value={folder}
                  onChange={(e) => setFolder(e.target.value)}
                  placeholder={t('folderPlaceholder')}
                  className="flex-1 border-0 bg-transparent font-mono text-[12.5px] outline-none"
                  style={{ color: 'var(--color-ink)' }}
                />
              </div>
              <div
                onDragOver={(e) => e.preventDefault()}
                onDrop={handleDrop}
                onClick={() => inputRef.current?.click()}
                className="flex w-full flex-col items-center gap-2.5 rounded-[14px] border-[1.5px] border-dashed p-8"
                style={{ borderColor: 'var(--color-border)', background: 'var(--color-surface)' }}
              >
                <UploadIcon />
                <span className="text-sm font-semibold" style={{ color: 'var(--color-ink)' }}>
                  {t('dragOrChoose')}
                </span>
                <span className="text-[12.5px]" style={{ color: 'var(--color-muted)' }}>
                  {t('pdfOrCsv')}
                </span>
              </div>
              <input
                ref={inputRef}
                type="file"
                accept=".pdf,.csv"
                className="hidden"
                onChange={(e) => {
                  const selected = e.target.files?.[0]
                  if (selected) void runUpload(selected)
                }}
              />
              <p className="mt-3 text-center text-xs" style={{ color: 'var(--color-faint)' }}>
                {t('uploadNote')}
              </p>
            </>
          )}

          {phase !== 'idle' && file && (
            <>
              <div className="mb-4 flex items-center gap-2.5 rounded-[10px] border px-3 py-2.5" style={{ borderColor: 'var(--color-border)', background: 'var(--color-surface)' }}>
                <FileIcon />
                <span className="font-mono text-[12.5px]" style={{ color: 'var(--color-ink)' }}>
                  {file.name}
                </span>
                <span className="ml-auto text-[11.5px]" style={{ color: 'var(--color-faint)' }}>
                  {t('megabytes', { n: (file.size / 1024 / 1024).toFixed(1) })}
                </span>
              </div>

              {phase === 'uploading' && (
                <div className="flex items-center justify-center gap-2 py-4" style={{ color: 'var(--color-muted)' }}>
                  <span className="text-[13.5px]">{t('uploading')}</span>
                  <span className="inline-flex gap-1">
                    {[0, 0.2, 0.4].map((delay) => (
                      <span
                        key={delay}
                        className="h-1 w-1 rounded-full"
                        style={{ background: 'var(--color-accent)', animation: `fa-dot 1.2s infinite ${delay}s` }}
                      />
                    ))}
                  </span>
                </div>
              )}

              {phase === 'error' && (
                <div className="rounded-[10px] border px-3 py-2 text-[12.5px]" style={{ borderColor: 'var(--color-neg)', color: 'var(--color-neg)' }}>
                  {errorMessage}
                </div>
              )}

              {phase === 'done' && (
                <button
                  type="button"
                  onClick={onClose}
                  className="w-full rounded-[10px] py-[11px] text-[13.5px] font-semibold text-white"
                  style={{ background: 'var(--color-accent)' }}
                >
                  {t('doneOpenChat')}
                </button>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
