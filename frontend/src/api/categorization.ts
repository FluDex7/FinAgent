import { get, patch, post } from './client'
import type { CategoryOut, MerchantOut } from './types'

export function listCategories(): Promise<CategoryOut[]> {
  return get<CategoryOut[]>('/categories')
}

export function createCategory(name: string, color?: string): Promise<CategoryOut> {
  return post<CategoryOut>('/categories', { name, color })
}

export function updateCategory(
  categoryId: string,
  fields: { name?: string; color?: string },
): Promise<CategoryOut> {
  return patch<CategoryOut>(`/categories/${categoryId}`, fields)
}

export function listMerchants(needsReview = false): Promise<MerchantOut[]> {
  return get<MerchantOut[]>(`/categories/merchants?needs_review=${needsReview}`)
}

export function recategorizeMerchant(merchantId: string, categoryId: string): Promise<MerchantOut> {
  return patch<MerchantOut>(`/categories/merchants/${merchantId}`, { categoryId })
}
