import type { QueryTypeBucket } from '../lib/types'

const LABELS: Record<QueryTypeBucket, string> = {
  count: 'Count queries',
  average: 'Average queries',
  percentage: 'Percentage queries',
  benchmark: 'Benchmark queries',
}

interface QueryTypeChartProps {
  distribution: Record<QueryTypeBucket, number>
}

export function QueryTypeChart({ distribution }: QueryTypeChartProps) {
  const total = Object.values(distribution).reduce((a, b) => a + b, 0)
  const max = Math.max(1, ...Object.values(distribution))

  return (
    <section className="company-panel border border-[#1a1a2e] bg-[#0d0d14]/80 p-5 company-panel-enter">
      <header className="mb-5">
        <h2 className="font-plex-sans text-sm font-semibold uppercase tracking-[0.14em] text-slate-200">
          Query type distribution
        </h2>
        <p className="mt-1 font-plex-sans text-xs text-slate-500">
          By structured_query.aggregation · updates on new query
        </p>
      </header>
      <ul className="space-y-4">
        {(Object.keys(LABELS) as QueryTypeBucket[]).map((key) => {
          const count = distribution[key]
          const pct = total === 0 ? 0 : (count / total) * 100
          const widthPct = total === 0 ? 0 : (count / max) * 100
          return (
            <li key={key}>
              <div className="mb-1.5 flex items-baseline justify-between gap-2">
                <span className="font-plex-sans text-xs text-slate-400">
                  {LABELS[key]}
                </span>
                <span className="font-plex-mono text-xs tabular-nums text-slate-500">
                  {count}
                  <span className="text-slate-600"> · </span>
                  {pct.toFixed(0)}%
                </span>
              </div>
              <div className="h-2 w-full bg-[#1a1a2e]">
                <div
                  className="query-type-bar h-full bg-[#00e5ff]/70 transition-[width] duration-500 ease-out"
                  style={{ width: `${widthPct}%` }}
                />
              </div>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
