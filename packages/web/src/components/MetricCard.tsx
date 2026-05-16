import type { ReactNode } from 'react'

import { useAnimatedNumber } from '../hooks/useAnimatedNumber'

interface MetricCardProps {
  label: string
  value: number
  format?: (n: number) => string
  accent?: 'default' | 'cyan' | 'danger'
  suffix?: ReactNode
  delayMs?: number
}

const accentClasses = {
  default: 'text-slate-100',
  cyan: 'text-[#00e5ff]',
  danger: 'text-[#ff3b3b]',
} as const

export function MetricCard({
  label,
  value,
  format = (n) => Math.round(n).toLocaleString('en-US'),
  accent = 'default',
  suffix,
  delayMs = 0,
}: MetricCardProps) {
  const animated = useAnimatedNumber(value)

  return (
    <article
      className="company-metric-card border border-[#1a1a2e] bg-[#0d0d14]/80 p-5 transition-shadow hover:shadow-[0_0_24px_rgba(0,229,255,0.08)]"
      style={{ animationDelay: `${delayMs}ms` }}
    >
      <p className="font-plex-sans text-xs font-medium uppercase tracking-[0.14em] text-slate-500">
        {label}
      </p>
      <div className="mt-3 flex items-baseline gap-2">
        <p
          className={`font-plex-mono text-3xl font-semibold tabular-nums ${accentClasses[accent]}`}
        >
          {format(animated)}
        </p>
        {suffix}
      </div>
    </article>
  )
}
