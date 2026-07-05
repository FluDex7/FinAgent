import { create } from 'zustand'
import { deleteChat, getMessages, listChats, renameChat, streamChat } from '../api/agent'
import { getHealth } from '../api/health'
import { getDocumentsTree } from '../api/statements'
import type {
  BlockOut,
  ChatSummary,
  DocFolderOut,
  HealthResponse,
  MessageOut,
  Ref,
  ToolCallOut,
} from '../api/types'

type Theme = 'light' | 'dark'

export interface StreamingMessage {
  text: string
  tools: ToolCallOut[]
  blocks: BlockOut[]
  scope: { files: string[]; auto: boolean } | null
}

interface AppStore {
  theme: Theme
  toggleTheme: () => void

  documentsTree: DocFolderOut[]
  documentsLoading: boolean
  loadDocuments: () => Promise<void>

  health: HealthResponse | null
  loadHealth: () => Promise<void>

  chats: ChatSummary[]
  chatsLoading: boolean
  activeChatId: string | null
  messages: MessageOut[]
  messagesLoading: boolean
  isStreaming: boolean
  streamingMessage: StreamingMessage | null
  error: string | null

  loadChats: () => Promise<void>
  newChat: () => void
  selectChat: (chatId: string) => Promise<void>
  renameChat: (chatId: string, title: string) => Promise<void>
  deleteChat: (chatId: string) => Promise<void>
  sendMessage: (text: string, refs?: Ref[]) => Promise<void>
}

function readStoredTheme(): Theme {
  return localStorage.getItem('fa-theme') === 'dark' ? 'dark' : 'light'
}

export const useAppStore = create<AppStore>((set, get) => ({
  theme: readStoredTheme(),
  toggleTheme: () => {
    const next: Theme = get().theme === 'light' ? 'dark' : 'light'
    localStorage.setItem('fa-theme', next)
    document.documentElement.setAttribute('data-theme', next)
    set({ theme: next })
  },

  documentsTree: [],
  documentsLoading: false,
  loadDocuments: async () => {
    set({ documentsLoading: true })
    try {
      const tree = await getDocumentsTree()
      set({ documentsTree: tree })
    } catch (err) {
      set({ error: (err as Error).message })
    } finally {
      set({ documentsLoading: false })
    }
  },

  health: null,
  loadHealth: async () => {
    try {
      const health = await getHealth()
      set({ health })
    } catch (err) {
      set({ error: (err as Error).message })
    }
  },

  chats: [],
  chatsLoading: false,
  activeChatId: null,
  messages: [],
  messagesLoading: false,
  isStreaming: false,
  streamingMessage: null,
  error: null,

  loadChats: async () => {
    set({ chatsLoading: true })
    try {
      const chats = await listChats()
      set({ chats })
    } catch (err) {
      set({ error: (err as Error).message })
    } finally {
      set({ chatsLoading: false })
    }
  },

  newChat: () => {
    set({ activeChatId: null, messages: [], streamingMessage: null })
  },

  selectChat: async (chatId: string) => {
    set({ activeChatId: chatId, messagesLoading: true, streamingMessage: null })
    try {
      const messages = await getMessages(chatId)
      set({ messages })
    } catch (err) {
      set({ error: (err as Error).message })
    } finally {
      set({ messagesLoading: false })
    }
  },

  renameChat: async (chatId: string, title: string) => {
    const updated = await renameChat(chatId, title)
    set({ chats: get().chats.map((c) => (c.id === chatId ? updated : c)) })
  },

  deleteChat: async (chatId: string) => {
    await deleteChat(chatId)
    const remaining = get().chats.filter((c) => c.id !== chatId)
    const updates: Partial<AppStore> = { chats: remaining }
    if (get().activeChatId === chatId) {
      updates.activeChatId = null
      updates.messages = []
    }
    set(updates)
  },

  sendMessage: async (text: string, refs: Ref[] = []) => {
    const wasNewChat = get().activeChatId === null
    const optimisticUser: MessageOut = {
      id: `local-${Date.now()}`,
      role: 'user',
      text,
      refs: refs.length ? refs : null,
      scope: null,
      tools: null,
      blocks: null,
      suggestions: null,
      createdAt: new Date().toISOString(),
    }
    set({
      messages: [...get().messages, optimisticUser],
      isStreaming: true,
      streamingMessage: { text: '', tools: [], blocks: [], scope: null },
      error: null,
    })

    try {
      for await (const evt of streamChat(get().activeChatId, text, refs)) {
        const streaming = get().streamingMessage
        if (!streaming) continue

        switch (evt.event) {
          case 'chat':
            if (get().activeChatId !== evt.data.chatId) {
              set({ activeChatId: evt.data.chatId })
            }
            break
          case 'scope':
            set({ streamingMessage: { ...streaming, scope: evt.data } })
            break
          case 'tool_start':
            set({
              streamingMessage: {
                ...streaming,
                tools: [...streaming.tools, { id: evt.data.id, name: evt.data.name, status: 'running', detail: null }],
              },
            })
            break
          case 'tool_end':
            set({
              streamingMessage: {
                ...streaming,
                tools: streaming.tools.map((t) =>
                  t.id === evt.data.id ? { ...t, status: 'done', detail: evt.data.detail } : t,
                ),
              },
            })
            break
          case 'block':
            set({ streamingMessage: { ...streaming, blocks: [...streaming.blocks, evt.data] } })
            break
          case 'token':
            set({ streamingMessage: { ...streaming, text: streaming.text + evt.data.text } })
            break
          case 'error':
            set({ error: evt.data.message })
            break
          case 'done':
            break
        }
      }

      const chatId = get().activeChatId
      if (chatId) {
        const messages = await getMessages(chatId)
        set({ messages })
        if (wasNewChat) {
          await get().loadChats()
        }
      }
    } catch (err) {
      set({ error: (err as Error).message })
    } finally {
      set({ isStreaming: false, streamingMessage: null })
    }
  },
}))
