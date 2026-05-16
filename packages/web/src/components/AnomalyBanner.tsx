import type { AnomalyAlertRow } from '../lib/types'

interface AnomalyBannerProps {
  alert: AnomalyAlertRow
  onDismiss: () => void
}

function severityStyles(severity: string): string {
  const s = severity.toLowerCase()
  if (s === 'critical' || s === 'high') {
    return 'border-[#ff3b3b] bg-[#ff3b3b]/15 text-[#ff8a8a]'
  }
  if (s === 'medium') {
    return 'border-amber-500/60 bg-amber-500/10 text-amber-300'
  }
  return 'border-slate-500/60 bg-slate-500/10 text-slate-300'
}

export function AnomalyBanner({ alert, onDismiss }: AnomalyBannerProps) {
  return (
    <div
      role="alert"
      className="anomaly-banner-pulse mb-6 flex flex-wrap items-center justify-between gap-4 border border-[#ff3b3b] bg-[#1a0808]/90 px-5 py-4"
    >
      <div className="min-w-0 flex-1">
        <p className="font-plex-sans text-xs font-semibold uppercase tracking-[0.16em] text-[#ff3b3b]">
          Anomaly detected
        </p>
        <p className="mt-1 font-plex-mono text-sm text-slate-200">
          <span className="text-[#ff8a8a]">{alert.pattern}</span>
          <span className="text-slate-500"> · </span>
          <span className="tabular-nums">
            {alert.query_ids.length} suspicious{' '}
            {alert.query_ids.length === 1 ? 'query' : 'queries'}
          </span>
        </p>
      </div>
      <div className="flex items-center gap-3">
        <span
          className={`font-plex-mono border px-2 py-0.5 text-xs font-semibold uppercase tracking-wider ${severityStyles(alert.severity)}`}
        >
          {alert.severity}
        </span>
        <button
          type="button"
          onClick={onDismiss}
          className="font-plex-sans border border-[#1a1a2e] bg-[#0a0a0f] px-3 py-1.5 text-xs text-slate-300 transition-colors hover:border-slate-600 hover:text-white"
        >
          Dismiss
        </button>
      </div>
    </div>
  )
}
