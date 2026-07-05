import { useEffect } from 'react'
import { EmptyState } from './components/EmptyState'
import { Sidebar } from './components/Sidebar'
import { Topbar } from './components/Topbar'
import { useAppStore } from './store/useAppStore'

const CLOUDS = [
  { top: '6%', left: '-3%', width: 360, height: 130, blur: 6, anim: 'drift 24s ease-in-out infinite alternate', opacity: 0.9 },
  { top: '16%', right: '0%', width: 440, height: 160, blur: 9, anim: 'drift2 30s ease-in-out infinite alternate', opacity: 0.85 },
  { bottom: '8%', left: '6%', width: 520, height: 180, blur: 11, anim: 'drift 34s ease-in-out infinite alternate', opacity: 0.8 },
  { bottom: '20%', right: '-6%', width: 380, height: 140, blur: 8, anim: 'drift2 26s ease-in-out infinite alternate', opacity: 0.75 },
]

function App() {
  const theme = useAppStore((s) => s.theme)
  const loadDocuments = useAppStore((s) => s.loadDocuments)
  const loadChats = useAppStore((s) => s.loadChats)
  const loadHealth = useAppStore((s) => s.loadHealth)
  const messages = useAppStore((s) => s.messages)

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
  }, [theme])

  useEffect(() => {
    void loadDocuments()
    void loadChats()
    void loadHealth()
  }, [loadDocuments, loadChats, loadHealth])

  const isEmpty = messages.length === 0

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
        <Sidebar onOpenUpload={() => {}} onOpenSettings={() => {}} />

        <main className="relative flex h-full min-w-0 flex-1 flex-col" style={{ background: 'var(--color-sheet)' }}>
          <Topbar onOpenSettings={() => {}} />

          <div className="flex-1 overflow-y-auto">
            <div className="mx-auto max-w-[760px] px-6 pb-8 pt-6">
              {isEmpty && <EmptyState onOpenUpload={() => {}} />}
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}

export default App
