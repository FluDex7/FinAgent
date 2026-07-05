import { useEffect, useMemo, useRef, useState } from 'react'
import { useAppStore } from '../store/useAppStore'
import type { DocFolderOut, Ref } from '../api/types'

interface AtItem {
  path: string
  kind: 'file' | 'folder'
  hint: string
}

function flattenDocuments(tree: DocFolderOut[]): AtItem[] {
  const items: AtItem[] = []
  for (const folder of tree) {
    if (folder.name) {
      items.push({ path: folder.name, kind: 'folder', hint: `${folder.files.length} файлов` })
    }
    for (const file of folder.files) {
      const path = folder.name ? `${folder.name}/${file.name}` : file.name
      const hint = file.status === 'parsed' ? `${file.txCount} операций` : 'не распознано'
      items.push({ path, kind: 'file', hint })
    }
  }
  return items
}

function FileIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" style={{ flexShrink: 0 }}>
      <path d="M6 3h8l4 4v14H6V3Z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
      <path d="M14 3v4h4" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
    </svg>
  )
}

function FolderIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" style={{ flexShrink: 0 }}>
      <path
        d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Z"
        stroke="currentColor"
        strokeWidth="1.7"
      />
    </svg>
  )
}

interface AtPickerProps {
  onPick: (ref: Ref) => void
  onClose: () => void
}

export function AtPicker({ onPick, onClose }: AtPickerProps) {
  const documentsTree = useAppStore((s) => s.documentsTree)
  const [query, setQuery] = useState('')
  const containerRef = useRef<HTMLDivElement>(null)

  const items = useMemo(() => flattenDocuments(documentsTree), [documentsTree])
  const filtered = items.filter((item) => item.path.toLowerCase().includes(query.toLowerCase()))

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        onClose()
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [onClose])

  return (
    <div
      ref={containerRef}
      className="animate-fa-pop absolute bottom-[calc(100%+8px)] left-0 z-10 w-[340px] overflow-hidden rounded-xl border shadow-lg"
      style={{ background: 'var(--color-sheet)', borderColor: 'var(--color-border)' }}
    >
      <div className="flex items-center gap-2 border-b px-3 py-2.5" style={{ borderColor: 'var(--color-border)' }}>
        <span className="font-mono font-semibold" style={{ color: 'var(--color-accent)' }}>
          @
        </span>
        <input
          autoFocus
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="файл или папка…"
          className="flex-1 border-0 bg-transparent text-[13px] outline-none"
          style={{ color: 'var(--color-ink)' }}
        />
      </div>
      <div className="max-h-[230px] overflow-y-auto p-1.5">
        {filtered.length === 0 && (
          <div className="px-2.5 py-3 text-center text-[12.5px]" style={{ color: 'var(--color-faint)' }}>
            Ничего не найдено
          </div>
        )}
        {filtered.map((item) => (
          <button
            key={item.path}
            type="button"
            onClick={() => onPick({ path: item.path, kind: item.kind })}
            className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left"
            style={{ color: 'var(--color-ink)' }}
          >
            <span style={{ color: 'var(--color-muted)' }}>{item.kind === 'folder' ? <FolderIcon /> : <FileIcon />}</span>
            <span className="font-mono text-[12.5px]">{item.path}</span>
            <span className="ml-auto text-[11px]" style={{ color: 'var(--color-faint)' }}>
              {item.hint}
            </span>
          </button>
        ))}
      </div>
    </div>
  )
}
