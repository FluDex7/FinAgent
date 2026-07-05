import { BASE_URL, del, get, patch, post } from './client'
import type { ChatSseEvent, ChatSummary, MessageOut, Ref } from './types'

export function listChats(): Promise<ChatSummary[]> {
  return get<ChatSummary[]>('/chats')
}

export function createChat(): Promise<ChatSummary> {
  return post<ChatSummary>('/chats')
}

export function renameChat(chatId: string, title: string): Promise<ChatSummary> {
  return patch<ChatSummary>(`/chats/${chatId}`, { title })
}

export function deleteChat(chatId: string): Promise<void> {
  return del<void>(`/chats/${chatId}`)
}

export function getMessages(chatId: string): Promise<MessageOut[]> {
  return get<MessageOut[]>(`/chats/${chatId}/messages`)
}

function parseSseEvent(block: string): ChatSseEvent | null {
  let eventName = ''
  const dataLines: string[] = []
  for (const line of block.split('\n')) {
    if (line.startsWith('event:')) {
      eventName = line.slice('event:'.length).trim()
    } else if (line.startsWith('data:')) {
      dataLines.push(line.slice('data:'.length).trim())
    }
  }
  if (!eventName) return null
  const data = dataLines.length ? JSON.parse(dataLines.join('\n')) : {}
  return { event: eventName, data } as ChatSseEvent
}

export async function* streamChat(
  chatId: string | null,
  message: string,
  refs: Ref[] = [],
  signal?: AbortSignal,
): AsyncGenerator<ChatSseEvent> {
  const res = await fetch(`${BASE_URL}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ chatId, message, refs }),
    signal,
  })
  if (!res.ok || !res.body) {
    throw new Error(`chat stream failed: ${res.status}`)
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    let separatorIndex: number
    while ((separatorIndex = buffer.indexOf('\n\n')) !== -1) {
      const block = buffer.slice(0, separatorIndex)
      buffer = buffer.slice(separatorIndex + 2)
      const parsed = parseSseEvent(block)
      if (parsed) yield parsed
    }
  }
}
