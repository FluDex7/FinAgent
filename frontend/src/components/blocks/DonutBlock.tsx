import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { useLocale, useT } from '../../hooks/useT'
import { normalizeMagnitude } from './normalizeMagnitude'

const PALETTE = [
  'var(--color-chart-1)',
  'var(--color-chart-2)',
  'var(--color-chart-3)',
  'var(--color-chart-4)',
  'var(--color-chart-5)',
]

interface DonutPoint {
  label: string
  value: number
  percent?: number
}

function formatNumber(n: number, locale: string): string {
  return new Intl.NumberFormat(locale).format(Math.round(n))
}

function DonutTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: DonutPoint }> }) {
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

export function DonutBlock({ data, title }: { data: unknown; title?: string }) {
  const t = useT()
  const locale = useLocale()
  const points = normalizeMagnitude(Array.isArray(data) ? (data as DonutPoint[]) : [])
  if (points.length === 0) return null

  const total = points.reduce((sum, p) => sum + p.value, 0)

  return (
    <div className="rounded-2xl border px-[18px] py-4" style={{ background: 'var(--color-surface)', borderColor: 'var(--color-border)' }}>
      {title && (
        <div className="mb-3.5 text-[12.5px] font-semibold" style={{ color: 'var(--color-muted)' }}>
          {title}
        </div>
      )}
      <div className="flex items-center gap-[26px]">
        <div className="relative h-[132px] w-[132px] flex-shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={points}
                dataKey="value"
                nameKey="label"
                innerRadius={40}
                outerRadius={66}
                paddingAngle={points.length > 1 ? 2 : 0}
                stroke="none"
                isAnimationActive={false}
              >
                {points.map((_, i) => (
                  <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
                ))}
              </Pie>
              <Tooltip content={<DonutTooltip />} />
            </PieChart>
          </ResponsiveContainer>
          <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
            <span className="font-mono text-base font-semibold" style={{ color: 'var(--color-ink)' }}>
              {formatNumber(total, locale)}
            </span>
            <span className="text-[10px]" style={{ color: 'var(--color-faint)' }}>
              {t('donutTotal')}
            </span>
          </div>
        </div>

        <div className="flex min-w-0 flex-1 flex-col gap-2.5">
          {points.map((point, i) => {
            const percent = point.percent ?? (total > 0 ? (point.value / total) * 100 : 0)
            return (
              <div key={point.label} className="flex items-center gap-2.5 text-[13px]">
                <span
                  className="h-2.5 w-2.5 flex-shrink-0 rounded-[3px]"
                  style={{ background: PALETTE[i % PALETTE.length] }}
                />
                <span className="min-w-0 truncate" style={{ color: 'var(--color-ink)' }}>
                  {point.label}
                </span>
                <span className="ml-auto font-mono text-[12.5px]" style={{ color: 'var(--color-muted)' }}>
                  {formatNumber(point.value, locale)}
                </span>
                <span className="w-[34px] text-right font-mono text-[11.5px]" style={{ color: 'var(--color-faint)' }}>
                  {percent.toFixed(1)}%
                </span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
