import type { BlockOut } from '../../api/types'
import { BarsBlock } from './BarsBlock'
import { DonutBlock } from './DonutBlock'
import { LineBlock } from './LineBlock'
import { MetricsBlock } from './MetricsBlock'
import { TableBlock } from './TableBlock'

export function BlockRenderer({ blocks }: { blocks: BlockOut[] }) {
  if (blocks.length === 0) return null

  return (
    <div className="mt-3.5 flex flex-col gap-2">
      {blocks.map((block, i) => {
        switch (block.kind) {
          case 'metrics':
            return <MetricsBlock key={i} data={block.data} />
          case 'donut':
            return <DonutBlock key={i} data={block.data} />
          case 'bars':
            return <BarsBlock key={i} data={block.data} />
          case 'line':
            return <LineBlock key={i} data={block.data} />
          case 'table':
            return <TableBlock key={i} data={block.data} />
          default:
            return null
        }
      })}
    </div>
  )
}
