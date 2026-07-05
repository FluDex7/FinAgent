type TableRow = Record<string, string | number>

function formatHeader(key: string): string {
  return key.charAt(0).toUpperCase() + key.slice(1).replace(/([A-Z])/g, ' $1')
}

export function TableBlock({ data, title }: { data: unknown; title?: string }) {
  const rows = Array.isArray(data) ? (data as TableRow[]) : []
  if (rows.length === 0) return null
  const columns = Object.keys(rows[0])

  return (
    <div className="overflow-hidden rounded-[14px] border" style={{ background: 'var(--color-surface)', borderColor: 'var(--color-border)' }}>
      {title && (
        <div className="border-b px-4 py-2.5 text-[12.5px] font-semibold" style={{ borderColor: 'var(--color-border)', color: 'var(--color-muted)' }}>
          {title}
        </div>
      )}
      <div className="overflow-x-auto">
        <div
          className="grid px-4 py-2 text-[11px] uppercase tracking-wide"
          style={{ gridTemplateColumns: `repeat(${columns.length}, minmax(90px, 1fr))`, color: 'var(--color-faint)' }}
        >
          {columns.map((col, i) => (
            <span key={col} className={i > 0 ? 'text-right' : ''}>
              {formatHeader(col)}
            </span>
          ))}
        </div>
        {rows.map((row, rowIndex) => (
          <div
            key={rowIndex}
            className="grid items-center border-t px-4 py-2.5 text-[13px]"
            style={{ gridTemplateColumns: `repeat(${columns.length}, minmax(90px, 1fr))`, borderColor: 'var(--color-border)' }}
          >
            {columns.map((col, i) => {
              const value = row[col]
              const isNumeric = typeof value === 'number'
              return (
                <span
                  key={col}
                  className={i > 0 ? 'text-right font-mono' : 'font-medium'}
                  style={{
                    color: i === 0 ? 'var(--color-ink)' : 'var(--color-muted)',
                    fontVariantNumeric: isNumeric ? 'tabular-nums' : undefined,
                  }}
                >
                  {value}
                </span>
              )
            })}
          </div>
        ))}
      </div>
    </div>
  )
}
