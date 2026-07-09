import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useLocale } from '../../hooks/useT'
import { normalizeMagnitude } from './normalizeMagnitude'

interface LinePoint {
  label: string
  value: number
}

function formatNumber(n: number, locale: string): string {
  return new Intl.NumberFormat(locale).format(Math.round(n))
}

function formatCompact(n: number): string {
  const abs = Math.abs(n)
  if (abs >= 1_000_000) return `${(n / 1_000_000).toFixed(abs % 1_000_000 === 0 ? 0 : 1)}M`
  if (abs >= 1_000) return `${(n / 1_000).toFixed(abs % 1_000 === 0 ? 0 : 1)}k`
  return String(n)
}

function LineTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: LinePoint }> }) {
  const locale = useLocale()
  if (!active || !payload || payload.length === 0) return null
  const point = payload[0].payload
  return (
    <div
      className="rounded-lg border px-3 py-2 text-[12.5px] shadow-lg"
      style={{ background: 'var(--color-sheet)', borderColor: 'var(--color-border)' }}
    >
      <div style={{ color: 'var(--color-muted)' }}>{point.label}</div>
      <div className="font-mono font-semibold" style={{ color: 'var(--color-ink)' }}>
        {formatNumber(point.value, locale)}
      </div>
    </div>
  )
}

export function LineBlock({ data, title }: { data: unknown; title?: string }) {
  const points = normalizeMagnitude(Array.isArray(data) ? (data as LinePoint[]) : [])
  if (points.length === 0) return null

  return (
    <div className="rounded-2xl border px-[18px] py-4" style={{ background: 'var(--color-surface)', borderColor: 'var(--color-border)' }}>
      {title && (
        <div className="mb-3.5 text-[12.5px] font-semibold" style={{ color: 'var(--color-muted)' }}>
          {title}
        </div>
      )}
      <div style={{ width: '100%', height: 180 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={points} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
            <CartesianGrid vertical={false} stroke="var(--color-border)" />
            <XAxis
              dataKey="label"
              tickLine={false}
              axisLine={false}
              tick={{ fill: 'var(--color-faint)', fontSize: 11.5 }}
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              tick={{ fill: 'var(--color-faint)', fontSize: 11.5 }}
              width={38}
              tickFormatter={formatCompact}
            />
            <Tooltip content={<LineTooltip />} cursor={{ stroke: 'var(--color-border)' }} />
            <Line
              type="monotone"
              dataKey="value"
              stroke="var(--color-accent)"
              strokeWidth={2}
              dot={{ r: 4, fill: 'var(--color-accent)', strokeWidth: 2, stroke: 'var(--color-surface)' }}
              activeDot={{ r: 5 }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
