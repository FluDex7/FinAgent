import { useEffect } from 'react'
import { useAppStore } from './store/useAppStore'

const CLOUDS = [
  { top: '6%', left: '-3%', width: 360, height: 130, blur: 6, anim: 'drift 24s ease-in-out infinite alternate', opacity: 0.9 },
  { top: '16%', right: '0%', width: 440, height: 160, blur: 9, anim: 'drift2 30s ease-in-out infinite alternate', opacity: 0.85 },
  { bottom: '8%', left: '6%', width: 520, height: 180, blur: 11, anim: 'drift 34s ease-in-out infinite alternate', opacity: 0.8 },
  { bottom: '20%', right: '-6%', width: 380, height: 140, blur: 8, anim: 'drift2 26s ease-in-out infinite alternate', opacity: 0.75 },
]

function App() {
  const theme = useAppStore((s) => s.theme)
  const toggleTheme = useAppStore((s) => s.toggleTheme)

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
  }, [theme])

  return (
    <div
      className="relative flex h-screen w-full items-center justify-center overflow-hidden p-6"
      style={{ background: 'var(--gradient-sky)' }}
    >
      {CLOUDS.map((cloud, i) => (
        <div
          key={i}
          className="pointer-events-none absolute"
          style={{
            top: cloud.top,
            left: cloud.left,
            right: cloud.right,
            bottom: cloud.bottom,
            width: cloud.width,
            height: cloud.height,
            background: `radial-gradient(closest-side, rgba(255,255,255,${cloud.opacity}), rgba(255,255,255,0))`,
            filter: `blur(${cloud.blur}px)`,
            animation: cloud.anim,
          }}
        />
      ))}

      <div
        className="relative z-10 flex overflow-hidden rounded-[22px] border border-[var(--color-border)]"
        style={{
          width: 'min(1180px, 100%)',
          height: 'min(770px, 100%)',
          background: 'var(--color-panel)',
          backdropFilter: 'blur(30px) saturate(140%)',
          WebkitBackdropFilter: 'blur(30px) saturate(140%)',
          boxShadow: '0 30px 80px rgba(20,60,120,.32), inset 0 1px 0 rgba(255,255,255,.5)',
        }}
      >
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
        </aside>

        <main className="relative flex h-full min-w-0 flex-1 flex-col" style={{ background: 'var(--color-sheet)' }}>
          <header
            className="flex h-[54px] flex-shrink-0 items-center gap-3 border-b px-[18px]"
            style={{ borderColor: 'var(--color-border)' }}
          >
            <span className="text-sm font-semibold" style={{ color: 'var(--color-ink)' }}>
              Новый чат
            </span>
            <div className="ml-auto flex items-center gap-1">
              <button
                onClick={toggleTheme}
                className="flex h-[34px] w-[34px] items-center justify-center rounded-[9px] border"
                style={{ borderColor: 'var(--color-border)', color: 'var(--color-muted)' }}
              >
                <span className="text-[15px]">{theme === 'light' ? '☀️' : '🌙'}</span>
              </button>
            </div>
          </header>
        </main>
      </div>
    </div>
  )
}

export default App
