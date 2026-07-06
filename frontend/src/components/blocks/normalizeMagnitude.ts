/**
 * If every value in a chart's dataset is negative (a plain "spend by category"
 * breakdown, where the sign is just DB bookkeeping for debits), flip them all
 * positive so bars/slices grow upward/outward like a normal chart. Datasets with
 * a genuine mix of signs (e.g. period-over-period deltas) are left untouched,
 * since the sign itself is the information there.
 */
export function normalizeMagnitude<T extends { value: number }>(points: T[]): T[] {
  const hasNegative = points.some((p) => p.value < 0)
  const hasPositive = points.some((p) => p.value > 0)
  if (hasNegative && !hasPositive) {
    return points.map((p) => ({ ...p, value: -p.value }))
  }
  return points
}
