import { useAppStore } from '../store/useAppStore'

interface TopbarProps {
  onOpenSettings: () => void
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

export function Topbar({ onOpenSettings }: TopbarProps) {
  const theme = useAppStore((s) => s.theme)
  const toggleTheme = useAppStore((s) => s.toggleTheme)
  const activeChatId = useAppStore((s) => s.activeChatId)
  const chats = useAppStore((s) => s.chats)

  const activeChat = chats.find((c) => c.id === activeChatId)
  const title = activeChat?.title ?? 'Новый чат'

  return (
    <header
      className="flex h-[54px] flex-shrink-0 items-center gap-3 border-b px-[18px]"
      style={{ borderColor: 'var(--color-border)' }}
    >
      <span className="text-sm font-semibold" style={{ color: 'var(--color-ink)' }}>
        {title}
      </span>
      <div className="ml-auto flex items-center gap-1">
        <button
          type="button"
          onClick={toggleTheme}
          className="flex h-[34px] w-[34px] items-center justify-center rounded-[9px] border"
          style={{ borderColor: 'var(--color-border)', color: 'var(--color-muted)' }}
        >
          <span className="text-[15px]">{theme === 'light' ? '☀️' : '🌙'}</span>
        </button>
        <button
          type="button"
          onClick={onOpenSettings}
          className="flex h-[34px] w-[34px] items-center justify-center rounded-[9px] border"
          style={{ borderColor: 'var(--color-border)', color: 'var(--color-muted)' }}
        >
          <SettingsIcon />
        </button>
      </div>
    </header>
  )
}
