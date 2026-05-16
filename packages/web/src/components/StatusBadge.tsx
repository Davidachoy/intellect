import type { RealtimeStatus } from '../lib/types'

const LABELS: Record<RealtimeStatus, string> = {
  connecting: 'Connecting…',
  connected: 'Live',
  offline: 'Offline',
  disabled: 'Realtime off',
}

const STYLES: Record<RealtimeStatus, string> = {
  connecting: 'bg-amber-500/15 text-amber-300 ring-amber-500/30',
  connected: 'bg-emerald-500/15 text-emerald-300 ring-emerald-500/30',
  offline: 'bg-red-500/15 text-red-300 ring-red-500/30',
  disabled: 'bg-slate-700/50 text-slate-400 ring-slate-600/40',
}

export function StatusBadge({ status }: { status: RealtimeStatus }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-wide ring-1 ring-inset ${STYLES[status]}`}
    >
      <span
        className={`h-1.5 w-1.5 rounded-full ${status === 'connected' ? 'animate-pulse bg-emerald-400' : 'bg-current opacity-70'}`}
        aria-hidden
      />
      {LABELS[status]}
    </span>
  )
}
