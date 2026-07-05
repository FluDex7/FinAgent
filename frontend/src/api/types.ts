export type StatementFormat = 'csv' | 'pdf'
export type StatementStatus = 'new' | 'parsing' | 'parsed' | 'error'
export type MerchantSource = 'rule' | 'llm' | 'user'
export type MessageRole = 'user' | 'agent'

export interface StatementOut {
  id: string
  filename: string
  folderPath: string
  sourceFormat: StatementFormat
  status: StatementStatus
  bankName: string | null
  dateFrom: string | null
  dateTo: string | null
  transactionCount: number
  errorMessage: string | null
  createdAt: string
}

export interface DocFileOut {
  id: string
  name: string
  folder: string
  txCount: number
  dateFrom: string | null
  dateTo: string | null
  status: StatementStatus
}

export interface DocFolderOut {
  name: string
  files: DocFileOut[]
}

export interface TransactionOut {
  id: string
  date: string
  amount: number
  currency: string
  rawDescription: string
  merchantId: string | null
  categoryId: string | null
}

export interface CategoryOut {
  id: string
  name: string
  color: string
  isSystem: boolean
}

export interface MerchantOut {
  id: string
  normalizedKey: string
  displayName: string | null
  categoryId: string | null
  source: MerchantSource
}

export interface Ref {
  path: string
  kind: 'file' | 'folder'
}

export interface ChatSummary {
  id: string
  title: string
}

export type ToolCallStatus = 'running' | 'done' | 'error'

export interface ToolCallOut {
  id: string
  name: string
  status: ToolCallStatus
  detail: string | null
}

export type BlockKind = 'metrics' | 'donut' | 'bars' | 'line' | 'table'

export interface BlockOut {
  kind: BlockKind
  data: Record<string, unknown> | unknown[]
}

export interface MessageOut {
  id: string
  role: MessageRole
  text: string
  refs: Ref[] | null
  scope: { files: string[]; auto: boolean } | null
  tools: ToolCallOut[] | null
  blocks: BlockOut[] | null
  suggestions: string[] | null
  createdAt: string
}

export type ChatSseEvent =
  | { event: 'chat'; data: { chatId: string } }
  | { event: 'scope'; data: { files: string[]; auto: boolean } }
  | { event: 'tool_start'; data: { id: string; name: string } }
  | { event: 'tool_end'; data: { id: string; name: string; detail: string | null } }
  | { event: 'block'; data: BlockOut }
  | { event: 'token'; data: { text: string } }
  | { event: 'error'; data: { message: string } }
  | { event: 'done'; data: Record<string, never> }
