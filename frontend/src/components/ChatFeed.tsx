import { useEffect, useRef, useState } from 'react'
import { useAppStore } from '../store/useAppStore'
import type { BlockOut, MessageOut, ToolCallOut } from '../api/types'
import { BlockRenderer } from './blocks/BlockRenderer'

interface AgentViewData {
  text: string
  scope: { files: string[]; auto: boolean } | null
  tools: ToolCallOut[] | null
  blocks: BlockOut[] | null
  suggestions: string[] | null
  isStreaming: boolean
}

function AgentIcon() {
  return (
    <div
      className="mt-0.5 flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-[9px] border"
      style={{ background: 'var(--color-surface)', borderColor: 'var(--color-border)' }}
    >
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
        <path d="M4 19V9M9 19V5M14 19v-7M19 19v-11" stroke="var(--color-accent)" strokeWidth="2.4" strokeLinecap="round" />
      </svg>
    </div>
  )
}

function ToolIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" style={{ color: 'var(--color-accent)' }}>
      <path
        d="M14.7 6.3a4 4 0 0 0-5.4 5.4l-6 6 2.9 2.9 6-6a4 4 0 0 0 5.4-5.4l-2.4 2.4-2.1-.8-.8-2.1 2.4-2.4Z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function ScopeBanner({ scope }: { scope: { files: string[]; auto: boolean } }) {
  return (
    <div
      className="mb-3 inline-flex items-center gap-2 rounded-[10px] border px-3 py-1.5 text-[12.5px]"
      style={{ background: 'var(--color-surface)', borderColor: 'var(--color-border)' }}
    >
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" style={{ color: 'var(--color-accent)', flexShrink: 0 }}>
        <path d="M4 6h16M4 12h16M4 18h10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      </svg>
      <span style={{ color: 'var(--color-muted)' }}>
        {scope.auto ? 'Агент сам определил область:' : 'Указанная область:'}
      </span>
      {scope.files.map((f) => (
        <span
          key={f}
          className="rounded-[5px] px-1.5 py-0.5 font-mono text-[11px]"
          style={{ color: 'var(--color-accent)', background: 'var(--color-accent-soft)' }}
        >
          {f}
        </span>
      ))}
    </div>
  )
}

function ToolTimeline({ tools }: { tools: ToolCallOut[] }) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})

  return (
    <div className="mb-3.5 flex flex-col gap-1.5">
      <div className="flex items-center gap-1.5 text-[11.5px]" style={{ color: 'var(--color-faint)' }}>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
          <path
            d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
          />
        </svg>
        Инструменты
      </div>
      <div className="flex flex-wrap gap-1.5">
        {tools.map((tool) => (
          <button
            key={tool.id}
            type="button"
            onClick={() => setExpanded((prev) => ({ ...prev, [tool.id]: !prev[tool.id] }))}
            className="flex items-center gap-1.5 rounded-md border px-2 py-1"
            style={{ borderColor: 'var(--color-border)' }}
          >
            <ToolIcon />
            <span className="font-mono text-[11.5px]" style={{ color: 'var(--color-ink)' }}>
              {tool.name}
              {tool.status === 'running' ? '…' : ''}
            </span>
            <svg
              width="11"
              height="11"
              viewBox="0 0 24 24"
              fill="none"
              style={{ color: 'var(--color-faint)', transform: expanded[tool.id] ? 'rotate(180deg)' : 'rotate(0deg)' }}
            >
              <path d="m6 9 6 6 6-6" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        ))}
      </div>
      {tools.map(
        (tool) =>
          expanded[tool.id] &&
          tool.detail && (
            <div
              key={`${tool.id}-detail`}
              className="overflow-hidden rounded-[10px] border"
              style={{ background: 'var(--color-surface-2)', borderColor: 'var(--color-border)' }}
            >
              <div
                className="flex items-center gap-1.5 border-b px-3 py-1.5 font-mono text-[10.5px]"
                style={{ borderColor: 'var(--color-border)', color: 'var(--color-faint)' }}
              >
                <span style={{ color: 'var(--color-accent)' }}>●</span> {tool.name} · read-only
              </div>
              <pre
                className="overflow-x-auto whitespace-pre p-3 font-mono text-xs leading-relaxed"
                style={{ color: 'var(--color-ink)' }}
              >
                {tool.detail}
              </pre>
            </div>
          ),
      )}
    </div>
  )
}

function UserBubble({ message }: { message: MessageOut }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[80%]">
        {message.refs && message.refs.length > 0 && (
          <div className="mb-1.5 flex flex-wrap justify-end gap-1.5">
            {message.refs.map((ref) => (
              <span
                key={ref.path}
                className="inline-flex items-center gap-1 rounded-md px-2 py-0.5 font-mono text-[11.5px]"
                style={{ color: 'var(--color-accent)', background: 'var(--color-accent-soft)' }}
              >
                @{ref.path}
              </span>
            ))}
          </div>
        )}
        <div
          className="rounded-[16px_16px_4px_16px] px-[15px] py-2.5 text-sm leading-relaxed text-white"
          style={{ background: 'var(--color-accent)' }}
        >
          {message.text}
        </div>
      </div>
    </div>
  )
}

function AgentBubble({ data }: { data: AgentViewData }) {
  const sendMessage = useAppStore((s) => s.sendMessage)
  const isThinking = data.isStreaming && !data.text && !(data.tools && data.tools.length)

  return (
    <div className="flex gap-3">
      <AgentIcon />
      <div className="min-w-0 flex-1">
        {isThinking && (
          <div className="flex h-7 items-center gap-2" style={{ color: 'var(--color-muted)' }}>
            <span className="text-[13.5px]">FinAgent анализирует</span>
            <span className="inline-flex gap-1">
              {[0, 0.2, 0.4].map((delay) => (
                <span
                  key={delay}
                  className="h-[5px] w-[5px] rounded-full"
                  style={{ background: 'var(--color-muted)', animation: `fa-dot 1.2s infinite ${delay}s` }}
                />
              ))}
            </span>
          </div>
        )}

        {data.scope && <ScopeBanner scope={data.scope} />}
        {data.tools && data.tools.length > 0 && <ToolTimeline tools={data.tools} />}

        {data.text && (
          <div className="whitespace-pre-wrap text-[14.5px] leading-relaxed" style={{ color: 'var(--color-ink)' }}>
            {data.text}
            {data.isStreaming && <span className="animate-fa-blink">▍</span>}
          </div>
        )}

        {data.blocks && data.blocks.length > 0 && <BlockRenderer blocks={data.blocks} />}

        {data.suggestions && data.suggestions.length > 0 && (
          <div className="mt-2.5 flex flex-wrap gap-2">
            {data.suggestions.map((sug) => (
              <button
                key={sug}
                type="button"
                onClick={() => sendMessage(sug)}
                className="inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-[12.5px]"
                style={{ borderColor: 'var(--color-border)', color: 'var(--color-muted)' }}
              >
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none">
                  <path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                </svg>
                {sug}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export function ChatFeed() {
  const messages = useAppStore((s) => s.messages)
  const streamingMessage = useAppStore((s) => s.streamingMessage)
  const isStreaming = useAppStore((s) => s.isStreaming)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingMessage])

  return (
    <div className="flex flex-col gap-[26px]">
      {messages.map((message) =>
        message.role === 'user' ? (
          <UserBubble key={message.id} message={message} />
        ) : (
          <AgentBubble
            key={message.id}
            data={{
              text: message.text,
              scope: message.scope,
              tools: message.tools,
              blocks: message.blocks,
              suggestions: message.suggestions,
              isStreaming: false,
            }}
          />
        ),
      )}
      {isStreaming && streamingMessage && (
        <AgentBubble
          data={{
            text: streamingMessage.text,
            scope: streamingMessage.scope,
            tools: streamingMessage.tools,
            blocks: streamingMessage.blocks,
            suggestions: null,
            isStreaming: true,
          }}
        />
      )}
      <div ref={bottomRef} />
    </div>
  )
}
