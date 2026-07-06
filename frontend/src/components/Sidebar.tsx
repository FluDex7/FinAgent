import { useState } from 'react'
import { useAppStore } from '../store/useAppStore'
import { ConfirmDialog } from './ConfirmDialog'

interface SidebarProps {
  onOpenUpload: () => void
  onOpenSettings: () => void
  onOpenDocument: (statementId: string) => void
  onCloseDocument: () => void
  onOpenReview: () => void
}

function PlusIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
      <path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

function ChevronIcon({ open }: { open: boolean }) {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      style={{ color: 'var(--color-faint)', transition: 'transform .15s', transform: `rotate(${open ? 90 : 0}deg)`, flexShrink: 0 }}
    >
      <path d="m9 6 6 6-6 6" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function FileIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" style={{ flexShrink: 0, opacity: 0.8 }}>
      <path d="M6 3h8l4 4v14H6V3Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
      <path d="M14 3v4h4" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
    </svg>
  )
}

function FolderIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" style={{ color: 'var(--color-muted)', flexShrink: 0 }}>
      <path
        d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Z"
        stroke="currentColor"
        strokeWidth="1.7"
      />
    </svg>
  )
}

function ChatIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" style={{ flexShrink: 0, opacity: 0.7 }}>
      <path d="M4 5h16v11H8l-4 4V5Z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
    </svg>
  )
}

function RenameIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
      <path d="M4 20h4L18 10l-4-4L4 16v4Z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
      <path d="M13 7l4 4" stroke="currentColor" strokeWidth="1.7" />
    </svg>
  )
}

function DeleteIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
      <path
        d="M5 7h14M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2m2 0v12a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V7"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
      />
    </svg>
  )
}

function TagIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" style={{ flexShrink: 0 }}>
      <path
        d="M12.5 3H5a2 2 0 0 0-2 2v7.5a2 2 0 0 0 .59 1.41l8.5 8.5a2 2 0 0 0 2.82 0l6-6a2 2 0 0 0 0-2.82l-8.5-8.5A2 2 0 0 0 12.5 3Z"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinejoin="round"
      />
      <circle cx="8" cy="8" r="1.4" fill="currentColor" />
    </svg>
  )
}

function SettingsIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.8" />
      <path
        d="M12 2v3M12 19v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M2 12h3M19 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  )
}

export function Sidebar({
  onOpenUpload,
  onOpenSettings,
  onOpenDocument,
  onCloseDocument,
  onOpenReview,
}: SidebarProps) {
  const documentsTree = useAppStore((s) => s.documentsTree)
  const chats = useAppStore((s) => s.chats)
  const activeChatId = useAppStore((s) => s.activeChatId)
  const health = useAppStore((s) => s.health)
  const newChat = useAppStore((s) => s.newChat)
  const selectChat = useAppStore((s) => s.selectChat)
  const renameChatAction = useAppStore((s) => s.renameChat)
  const deleteChatAction = useAppStore((s) => s.deleteChat)
  const reviewCount = useAppStore((s) => s.merchantsNeedingReview.length)
  const renameDocument = useAppStore((s) => s.renameDocument)
  const deleteDocument = useAppStore((s) => s.deleteDocument)

  const [openFolders, setOpenFolders] = useState<Record<string, boolean>>({})
  const [editingChatId, setEditingChatId] = useState<string | null>(null)
  const [editValue, setEditValue] = useState('')
  const [pendingDelete, setPendingDelete] = useState<{ id: string; title: string } | null>(null)

  const [fileMenu, setFileMenu] = useState<{ id: string; name: string; x: number; y: number } | null>(null)
  const [editingFileId, setEditingFileId] = useState<string | null>(null)
  const [editFileValue, setEditFileValue] = useState('')
  const [pendingFileDelete, setPendingFileDelete] = useState<{ id: string; name: string } | null>(null)

  const toggleFolder = (name: string) => {
    setOpenFolders((prev) => ({ ...prev, [name]: !prev[name] }))
  }

  const startFileRename = (fileId: string, currentName: string) => {
    setEditingFileId(fileId)
    setEditFileValue(currentName)
    setFileMenu(null)
  }

  const commitFileRename = async () => {
    if (editingFileId && editFileValue.trim()) {
      await renameDocument(editingFileId, editFileValue.trim())
    }
    setEditingFileId(null)
  }

  const startRename = (chatId: string, currentTitle: string) => {
    setEditingChatId(chatId)
    setEditValue(currentTitle)
  }

  const commitRename = async () => {
    if (editingChatId && editValue.trim()) {
      await renameChatAction(editingChatId, editValue.trim())
    }
    setEditingChatId(null)
  }

  const providerLabel = health
    ? health.llm.ok
      ? health.llm.provider === 'openai'
        ? 'OpenAI подключён'
        : 'Ollama (локально)'
      : health.llm.detail
    : 'Проверка...'

  return (
    <aside
      className="flex h-full w-[284px] flex-shrink-0 flex-col border-r"
      style={{ background: 'var(--color-panel)', borderColor: 'var(--color-border)' }}
    >
      <div className="flex items-center gap-2.5 px-4 pb-3 pt-4">
        <div
          className="flex h-[26px] w-[26px] flex-shrink-0 items-center justify-center rounded-lg"
          style={{ background: 'var(--color-accent)' }}
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
            <path d="M4 19V9M9 19V5M14 19v-7M19 19v-11" stroke="#fff" strokeWidth="2.4" strokeLinecap="round" />
          </svg>
        </div>
        <span className="text-[15px] font-bold tracking-tight" style={{ color: 'var(--color-ink)' }}>
          FinAgent
        </span>
        <span
          className="ml-auto rounded-full border px-1.5 py-0.5 text-[10px] font-semibold"
          style={{ color: 'var(--color-faint)', borderColor: 'var(--color-border)' }}
        >
          локально
        </span>
      </div>

      <div className="px-3 pb-3">
        <button
          type="button"
          onClick={() => {
            onCloseDocument()
            newChat()
          }}
          className="flex w-full items-center gap-2 rounded-[10px] border px-3 py-[9px] text-[13.5px] font-medium"
          style={{ background: 'var(--color-surface)', borderColor: 'var(--color-border)', color: 'var(--color-ink)' }}
        >
          <PlusIcon />
          Новый чат
        </button>
      </div>

      {reviewCount > 0 && (
        <div className="px-3 pb-3">
          <button
            type="button"
            onClick={() => {
              onCloseDocument()
              onOpenReview()
            }}
            className="flex w-full items-center gap-2 rounded-[10px] border px-3 py-[9px] text-[13.5px] font-medium"
            style={{ borderColor: 'var(--color-border)', color: 'var(--color-ink)' }}
          >
            <TagIcon />
            Требуют категории
            <span
              className="ml-auto rounded-full px-1.5 py-0.5 text-[11px] font-semibold text-white"
              style={{ background: 'var(--color-accent)' }}
            >
              {reviewCount}
            </span>
          </button>
        </div>
      )}

      <div className="flex-1 overflow-y-auto px-2 pb-2 pt-1">
        <div className="flex items-center justify-between px-2 py-1.5">
          <span
            className="text-[11px] font-semibold uppercase tracking-wider"
            style={{ color: 'var(--color-faint)' }}
          >
            Документы
          </span>
        </div>

        {documentsTree.map((folder) => {
          const isOpen = !!openFolders[folder.name]
          return (
            <div key={folder.name}>
              <button
                type="button"
                onClick={() => toggleFolder(folder.name)}
                className="flex w-full items-center gap-[7px] rounded-[7px] px-2 py-1.5 text-left text-[13px] font-medium"
                style={{ color: 'var(--color-ink)' }}
              >
                <ChevronIcon open={isOpen} />
                <FolderIcon />
                {folder.name}
                <span className="ml-auto text-[11px]" style={{ color: 'var(--color-faint)' }}>
                  {folder.files.length}
                </span>
              </button>
              {isOpen && (
                <div className="pl-2.5">
                  {folder.files.map((file) => {
                    const isParsed = file.status === 'parsed'
                    const hasStatement = file.status !== 'new'
                    const isEditing = editingFileId === file.id

                    if (isEditing) {
                      return (
                        <input
                          key={file.id}
                          value={editFileValue}
                          onChange={(e) => setEditFileValue(e.target.value)}
                          onBlur={commitFileRename}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') {
                              e.preventDefault()
                              void commitFileRename()
                            } else if (e.key === 'Escape') {
                              setEditingFileId(null)
                            }
                          }}
                          autoFocus
                          className="mb-0.5 w-full rounded-md border px-[7px] py-[5px] text-[12.5px] outline-none"
                          style={{ borderColor: 'var(--color-accent)', background: 'var(--color-surface)', color: 'var(--color-ink)' }}
                        />
                      )
                    }

                    return (
                      <button
                        key={file.id}
                        type="button"
                        disabled={!isParsed}
                        title={isParsed ? undefined : 'Файл ещё не распознан'}
                        onClick={() => onOpenDocument(file.id)}
                        onContextMenu={(e) => {
                          if (!hasStatement) return
                          e.preventDefault()
                          setFileMenu({ id: file.id, name: file.name, x: e.clientX, y: e.clientY })
                        }}
                        className="flex w-full items-center gap-[7px] rounded-[7px] px-2 py-1.5 text-left text-[12.5px]"
                        style={{ color: isParsed ? 'var(--color-muted)' : 'var(--color-faint)' }}
                      >
                        <FileIcon />
                        <span className="overflow-hidden text-ellipsis whitespace-nowrap">{file.name}</span>
                      </button>
                    )
                  })}
                </div>
              )}
            </div>
          )
        })}

        <button
          type="button"
          onClick={onOpenUpload}
          className="mt-1 flex w-full items-center gap-[7px] rounded-[7px] p-2 text-[12.5px] font-medium"
          style={{ color: 'var(--color-accent)' }}
        >
          <PlusIcon />
          Загрузить выписку
        </button>

        <div className="px-2 pb-1.5 pt-4">
          <span
            className="text-[11px] font-semibold uppercase tracking-wider"
            style={{ color: 'var(--color-faint)' }}
          >
            Чаты
          </span>
        </div>
        {chats.map((chat) => {
          const isActive = chat.id === activeChatId
          const isEditing = editingChatId === chat.id
          return (
            <div key={chat.id} className="flex items-center gap-0.5">
              {isEditing ? (
                <input
                  value={editValue}
                  onChange={(e) => setEditValue(e.target.value)}
                  onBlur={commitRename}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault()
                      void commitRename()
                    } else if (e.key === 'Escape') {
                      setEditingChatId(null)
                    }
                  }}
                  autoFocus
                  className="min-w-0 flex-1 rounded-md border px-[7px] py-[5px] text-[13px] outline-none"
                  style={{ borderColor: 'var(--color-accent)', background: 'var(--color-surface)', color: 'var(--color-ink)' }}
                />
              ) : (
                <>
                  <button
                    type="button"
                    onClick={() => {
                      onCloseDocument()
                      selectChat(chat.id)
                    }}
                    className="flex min-w-0 flex-1 items-center gap-2 rounded-[7px] px-2 py-[7px] text-left text-[13px]"
                    style={{
                      background: isActive ? 'var(--color-surface-2)' : 'transparent',
                      color: isActive ? 'var(--color-ink)' : 'var(--color-muted)',
                      fontWeight: isActive ? 500 : 400,
                    }}
                  >
                    <ChatIcon />
                    <span className="overflow-hidden text-ellipsis whitespace-nowrap">{chat.title}</span>
                  </button>
                  <button
                    type="button"
                    title="Переименовать"
                    onClick={() => startRename(chat.id, chat.title)}
                    className="flex h-[26px] w-[26px] flex-shrink-0 items-center justify-center rounded-md"
                    style={{ color: 'var(--color-faint)' }}
                  >
                    <RenameIcon />
                  </button>
                  <button
                    type="button"
                    title="Удалить"
                    onClick={() => setPendingDelete({ id: chat.id, title: chat.title })}
                    className="flex h-[26px] w-[26px] flex-shrink-0 items-center justify-center rounded-md"
                    style={{ color: 'var(--color-faint)' }}
                  >
                    <DeleteIcon />
                  </button>
                </>
              )}
            </div>
          )
        })}
      </div>

      <div className="flex items-center gap-2.5 border-t px-3 py-2.5" style={{ borderColor: 'var(--color-border)' }}>
        <span
          className="h-[7px] w-[7px] flex-shrink-0 rounded-full"
          style={{
            background: health?.llm.ok ? 'var(--color-pos)' : 'var(--color-neg)',
            boxShadow: '0 0 0 3px var(--color-accent-soft)',
          }}
        />
        <span className="text-xs" style={{ color: 'var(--color-muted)' }}>
          {providerLabel}
        </span>
        <button
          type="button"
          onClick={onOpenSettings}
          className="ml-auto flex h-[30px] w-[30px] flex-shrink-0 items-center justify-center rounded-lg"
          style={{ color: 'var(--color-muted)' }}
        >
          <SettingsIcon />
        </button>
      </div>

      {pendingDelete && (
        <ConfirmDialog
          title="Удалить чат?"
          message={`Чат «${pendingDelete.title}» и его история будут удалены без возможности восстановления.`}
          onCancel={() => setPendingDelete(null)}
          onConfirm={() => {
            deleteChatAction(pendingDelete.id)
            setPendingDelete(null)
          }}
        />
      )}

      {fileMenu && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setFileMenu(null)} onContextMenu={(e) => e.preventDefault()} />
          <div
            className="fixed z-50 min-w-[160px] overflow-hidden rounded-[10px] border py-1 text-[13px]"
            style={{
              left: fileMenu.x,
              top: fileMenu.y,
              background: 'var(--color-sheet)',
              borderColor: 'var(--color-border)',
              boxShadow: '0 12px 30px rgba(15,23,42,.25)',
            }}
          >
            <button
              type="button"
              onClick={() => startFileRename(fileMenu.id, fileMenu.name)}
              className="flex w-full items-center gap-2 px-3 py-2 text-left"
              style={{ color: 'var(--color-ink)' }}
            >
              <RenameIcon />
              Переименовать
            </button>
            <button
              type="button"
              onClick={() => {
                setPendingFileDelete({ id: fileMenu.id, name: fileMenu.name })
                setFileMenu(null)
              }}
              className="flex w-full items-center gap-2 px-3 py-2 text-left"
              style={{ color: 'var(--color-neg)' }}
            >
              <DeleteIcon />
              Удалить
            </button>
          </div>
        </>
      )}

      {pendingFileDelete && (
        <ConfirmDialog
          title="Удалить файл?"
          message={`Файл «${pendingFileDelete.name}» и все его транзакции будут удалены без возможности восстановления.`}
          onCancel={() => setPendingFileDelete(null)}
          onConfirm={() => {
            deleteDocument(pendingFileDelete.id)
            setPendingFileDelete(null)
          }}
        />
      )}
    </aside>
  )
}
