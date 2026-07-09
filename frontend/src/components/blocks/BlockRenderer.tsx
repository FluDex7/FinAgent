import { lazy, Suspense } from 'react'
import { useT } from '../../hooks/useT'
import type { BlockOut } from '../../api/types'
import { MetricsBlock } from './MetricsBlock'
import { TableBlock } from './TableBlock'

const DonutBlock = lazy(() => import('./DonutBlock').then((m) => ({ default: m.DonutBlock })))
const BarsBlock = lazy(() => import('./BarsBlock').then((m) => ({ default: m.BarsBlock })))
const LineBlock = lazy(() => import('./LineBlock').then((m) => ({ default: m.LineBlock })))

function ChartFallback() {
  const t = useT()
  return (
    <div
      className="flex h-[180px] items-center justify-center rounded-2xl border text-[12.5px]"
      style={{ background: 'var(--color-surface)', borderColor: 'var(--color-border)', color: 'var(--color-muted)' }}
    >
      {t('chartLoading')}
    </div>
  )
}

export function BlockRenderer({ blocks }: { blocks: BlockOut[] }) {
  if (blocks.length === 0) return null

  return (
    <div className="mt-3.5 flex flex-col gap-2">
      {blocks.map((block, i) => {
        switch (block.kind) {
          case 'metrics':
            return <MetricsBlock key={i} data={block.data} />
          case 'donut':
            return (
              <Suspense key={i} fallback={<ChartFallback />}>
                <DonutBlock data={block.data} />
              </Suspense>
            )
          case 'bars':
            return (
              <Suspense key={i} fallback={<ChartFallback />}>
                <BarsBlock data={block.data} />
              </Suspense>
            )
          case 'line':
            return (
              <Suspense key={i} fallback={<ChartFallback />}>
                <LineBlock data={block.data} />
              </Suspense>
            )
          case 'table':
            return <TableBlock key={i} data={block.data} />
          default:
            return null
        }
      })}
    </div>
  )
}
