import { create } from 'zustand'
import { deleteChat, getMessages, listChats, renameChat, streamChat } from '../api/agent'
import {
  createCategory as createCategoryApi,
  listCategories,
  listMerchants,
  recategorizeMerchant as recategorizeMerchantApi,
} from '../api/categorization'
import { getHealth } from '../api/health'
import { getDocumentsTree } from '../api/statements'
import type {
  BlockOut,
  CategoryOut,
  ChatSummary,
  DocFolderOut,
  HealthResponse,
  MerchantOut,
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
  setTheme: (theme: Theme) => void

  documentsTree: DocFolderOut[]
  documentsLoading: boolean
  loadDocuments: () => Promise<void>

  health: HealthResponse | null
  loadHealth: () => Promise<void>

  categories: CategoryOut[]
  merchantsNeedingReview: MerchantOut[]
  reviewLoading: boolean
  loadCategories: () => Promise<void>
  loadMerchantsNeedingReview: () => Promise<void>
  createCategory: (name: string, color?: string) => Promise<CategoryOut>
  recategorizeMerchant: (merchantId: string, categoryId: string) => Promise<void>

  chats: ChatSummary[]
  chatsLoading: boolean
  activeChatId: string | null
  messages: MessageOut[]
  messagesLoading: boolean
  isStreaming: boolean
  streamingMessage: StreamingMessage | null
  error: string | null
  clearError: () => void

  loadChats: () => Promise<void>
  newChat: () => void
  selectChat: (chatId: string) => Promise<void>
  renameChat: (chatId: string, title: string) => Promise<void>
  deleteChat: (chatId: string) => Promise<void>
  sendMessage: (text: string, refs?: Ref[]) => Promise<void>
  stopStreaming: () => void
}

let activeAbortController: AbortController | null = null

function readStoredTheme(): Theme {
  return localStorage.getItem('fa-theme') === 'dark' ? 'dark' : 'light'
}

function materializeStreamingMessage(get: () => AppStore, set: (partial: Partial<AppStore>) => void): void {
  const streaming = get().streamingMessage
  if (!streaming || (!streaming.text && !streaming.tools.length && !streaming.blocks.length)) return

  const message: MessageOut = {
    id: `local-${Date.now()}`,
    role: 'agent',
    text: streaming.text,
    refs: null,
    scope: streaming.scope,
    tools: streaming.tools.length ? streaming.tools : null,
    blocks: streaming.blocks.length ? streaming.blocks : null,
    suggestions: null,
    createdAt: new Date().toISOString(),
  }
  set({ messages: [...get().messages, message] })
}

export const useAppStore = create<AppStore>((set, get) => ({
  theme: readStoredTheme(),
  toggleTheme: () => {
    const next: Theme = get().theme === 'light' ? 'dark' : 'light'
    localStorage.setItem('fa-theme', next)
    document.documentElement.setAttribute('data-theme', next)
    set({ theme: next })
  },
  setTheme: (next: Theme) => {
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

  categories: [],
  merchantsNeedingReview: [],
  reviewLoading: false,
  loadCategories: async () => {
    try {
      const categories = await listCategories()
      set({ categories })
    } catch (err) {
      set({ error: (err as Error).message })
    }
  },
  loadMerchantsNeedingReview: async () => {
    set({ reviewLoading: true })
    try {
      const merchants = await listMerchants(true)
      set({ merchantsNeedingReview: merchants })
    } catch (err) {
      set({ error: (err as Error).message })
    } finally {
      set({ reviewLoading: false })
    }
  },
  createCategory: async (name: string, color?: string) => {
    const category = await createCategoryApi(name, color)
    set({ categories: [...get().categories, category] })
    return category
  },
  recategorizeMerchant: async (merchantId: string, categoryId: string) => {
    await recategorizeMerchantApi(merchantId, categoryId)
    set({ merchantsNeedingReview: get().merchantsNeedingReview.filter((m) => m.id !== merchantId) })
  },

  chats: [],
  chatsLoading: false,
  activeChatId: null,
  messages: [],
  messagesLoading: false,
  isStreaming: false,
  streamingMessage: null,
  error: null,
  clearError: () => set({ error: null }),

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

    activeAbortController = new AbortController()

    try {
      for await (const evt of streamChat(get().activeChatId, text, refs, activeAbortController.signal)) {
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

      // Don't re-fetch messages from the server here: FastAPI's session-commit
      // dependency for a StreamingResponse only runs after the whole SSE body
      // has been sent, so a GET fired the instant the stream ends can race
      // ahead of that commit and come back without the turn that just
      // finished — silently wiping it from the screen. We already have the
      // full text/tools/blocks from the stream itself, so just use that.
      materializeStreamingMessage(get, set)
      if (wasNewChat) {
        await get().loadChats()
      }
    } catch (err) {
      if ((err as Error).name === 'AbortError') {
        materializeStreamingMessage(get, set)
      } else {
        set({ error: (err as Error).message })
      }
    } finally {
      activeAbortController = null
      set({ isStreaming: false, streamingMessage: null })
    }
  },

  stopStreaming: () => {
    activeAbortController?.abort()
  },
}))
