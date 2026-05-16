import { useEffect } from 'react'

import { formatTimeAgo, formatUsd, truncateQuery } from '../lib/format'
import type { CompanyQueryRow } from '../lib/types'

interface ActivityFeedProps {
  queries: CompanyQueryRow[]
  getQuerierLabel: (hash: string) => string
  newFeedIds: Set<string>
  onRowSeen: (id: string) => void
}

export function ActivityFeed({
  queries,
  getQuerierLabel,
  newFeedIds,
  onRowSeen,
}: ActivityFeedProps) {
  return (
    <section className="company-panel border border-[#1a1a2e] bg-[#0d0d14]/80">
      <header className="border-b border-[#1a1a2e] px-5 py-4">
        <h2 className="font-plex-sans text-sm font-semibold uppercase tracking-[0.14em] text-slate-200">
          Live activity feed
        </h2>
        <p className="mt-1 font-plex-sans text-xs text-slate-500">
          Incoming queries · newest first · querier identity hidden
        </p>
      </header>
      <ul className="max-h-[28rem] overflow-y-auto">
        {queries.length === 0 ? (
          <li className="px-5 py-8 text-center font-plex-sans text-sm text-slate-500">
            Waiting for queries…
          </li>
        ) : (
          queries.map((q) => (
            <FeedRow
              key={q.id}
              query={q}
              querierLabel={getQuerierLabel(q.querier_api_key_hash)}
              isNew={newFeedIds.has(q.id)}
              onSeen={() => onRowSeen(q.id)}
            />
          ))
        )}
      </ul>
    </section>
  )
}

function FeedRow({
  query,
  querierLabel,
  isNew,
  onSeen,
}: {
  query: CompanyQueryRow
  querierLabel: string
  isNew: boolean
  onSeen: () => void
}) {
  useEffect(() => {
    if (!isNew) return
    const t = window.setTimeout(onSeen, 800)
    return () => window.clearTimeout(t)
  }, [isNew, onSeen])

  const statusClass = query.blocked
    ? 'text-[#ff3b3b]'
    : 'text-[#00e5ff]'
  const statusLabel = query.blocked ? 'BLOCKED' : 'APPROVED'

  return (
    <li
      className={`border-b border-[#1a1a2e]/80 px-5 py-3 last:border-b-0 ${
        isNew ? 'activity-row-enter' : ''
      }`}
    >
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1 font-plex-mono text-xs text-slate-400">
        <span className="text-slate-500">{querierLabel}</span>
        <span className="text-slate-600">·</span>
        <span className="max-w-full text-slate-300">
          {truncateQuery(query.raw_query)}
        </span>
        <span className="text-slate-600">·</span>
        <span className="tabular-nums text-[#00e5ff]">
          {formatUsd(query.cost_usd ?? 0)}
        </span>
        <span className="text-slate-600">·</span>
        <span className={`font-semibold ${statusClass}`}>{statusLabel}</span>
        <span className="text-slate-600">·</span>
        <span className="text-slate-500">{formatTimeAgo(query.created_at)}</span>
      </div>
    </li>
  )
}
