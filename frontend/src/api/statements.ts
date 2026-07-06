import { del, get, patch, postForm } from './client'
import type { DocFolderOut, StatementOut, TransactionOut } from './types'

export function getDocumentsTree(path?: string): Promise<DocFolderOut[]> {
  const query = path ? `?path=${encodeURIComponent(path)}` : ''
  return get<DocFolderOut[]>(`/documents/tree${query}`)
}

export function uploadStatement(file: File, folder: string): Promise<StatementOut> {
  const form = new FormData()
  form.append('file', file)
  form.append('folder', folder)
  return postForm<StatementOut>('/statements', form)
}

export function getStatement(statementId: string): Promise<StatementOut> {
  return get<StatementOut>(`/statements/${statementId}`)
}

export function getStatementTransactions(
  statementId: string,
  limit = 100,
  offset = 0,
): Promise<TransactionOut[]> {
  return get<TransactionOut[]>(`/statements/${statementId}/transactions?limit=${limit}&offset=${offset}`)
}

export function deleteStatement(statementId: string): Promise<void> {
  return del<void>(`/statements/${statementId}`)
}

export function renameStatement(statementId: string, name: string): Promise<StatementOut> {
  return patch<StatementOut>(`/statements/${statementId}`, { name })
}
