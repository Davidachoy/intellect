import type { ReactNode } from 'react'

interface PanelProps {
  title: string
  subtitle?: string
  badge?: ReactNode
  children: ReactNode
  className?: string
}

export function Panel({
  title,
  subtitle,
  badge,
  children,
  className = '',
}: PanelProps) {
  return (
    <section
      className={`flex flex-col rounded-xl border border-slate-800/80 bg-slate-900/70 shadow-lg shadow-black/25 backdrop-blur-sm ${className}`}
    >
      <header className="flex items-start justify-between gap-3 border-b border-slate-800/80 px-5 py-4">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-200">
            {title}
          </h2>
          {subtitle ? (
            <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>
          ) : null}
        </div>
        {badge}
      </header>
      <div className="flex flex-1 flex-col overflow-hidden p-5">{children}</div>
    </section>
  )
}
