interface MetricPoint {
  label: string
  value: string | number
}

export function MetricsBlock({ data }: { data: unknown }) {
  const points = Array.isArray(data) ? (data as MetricPoint[]) : []
  if (points.length === 0) return null

  return (
    <div className="grid grid-cols-3 gap-2.5">
      {points.map((point) => (
        <div
          key={point.label}
          className="rounded-xl border px-3.5 py-3"
          style={{ background: 'var(--color-surface)', borderColor: 'var(--color-border)' }}
        >
          <div className="mb-1 text-[11.5px]" style={{ color: 'var(--color-muted)' }}>
            {point.label}
          </div>
          <div className="font-mono text-[19px] font-semibold tracking-tight" style={{ color: 'var(--color-ink)' }}>
            {point.value}
          </div>
        </div>
      ))}
    </div>
  )
}
