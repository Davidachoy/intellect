import { useEffect, useRef, useState } from 'react'

import { useAnimatedNumber } from '../hooks/useAnimatedNumber'
import { useDemo } from '../hooks/useDemo'
import type { QueryRow } from '../lib/types'
import { Panel } from './Panel'
import { StatusBadge } from './StatusBadge'

const RECENT_LIMIT = 10

function truncate(text: string, max: number): string {
  if (text.length <= max) return text
  return `${text.slice(0, max - 1)}…`
}

function formatUsd(amount: number): string {
  return `$${amount.toFixed(2)}`
}

function CostCounter({
  totalCostUsd,
  chargePulse,
  lastDeltaUsd,
}: {
  totalCostUsd: number
  chargePulse: boolean
  lastDeltaUsd: number | null
}) {
  const animatedTotal = useAnimatedNumber(totalCostUsd)

  return (
    <div className="relative">
      <div
        className={`rounded-lg border bg-slate-950/60 px-4 py-3 transition-colors duration-300 ${
          chargePulse
            ? 'border-cyan-400/60 [animation:cost-flash_0.65s_ease-out]'
            : 'border-slate-800'
        }`}
      >
        <p className="text-xs uppercase tracking-wide text-slate-500">
          Total cost
        </p>
        <p className="mt-1 text-2xl font-semibold tabular-nums text-cyan-300">
          {formatUsd(animatedTotal)}
        </p>
      </div>
      {lastDeltaUsd !== null && lastDeltaUsd > 0 ? (
        <span
          key={lastDeltaUsd}
          className="pointer-events-none absolute -right-1 -top-2 rounded bg-emerald-500/20 px-2 py-0.5 text-xs font-semibold tabular-nums text-emerald-300 [animation:charge-float_0.75s_ease-out_forwards]"
        >
          +{formatUsd(lastDeltaUsd)}
        </span>
      ) : null}
    </div>
  )
}

function QueryListItem({
  query,
  isActive,
  isNew,
  onSelect,
}: {
  query: QueryRow
  isActive: boolean
  isNew: boolean
  onSelect: () => void
}) {
  const cost = Number(query.cost_usd ?? 0)

  return (
    <li className={isNew ? '[animation:row-enter_0.4s_ease-out]' : undefined}>
      <button
        type="button"
        onClick={onSelect}
        className={`w-full rounded-lg border px-3 py-3 text-left transition ${
          isActive
            ? 'border-cyan-500/50 bg-cyan-950/20'
            : 'border-slate-800 bg-slate-950/40 hover:border-slate-600'
        } ${isNew ? 'ring-1 ring-cyan-500/30' : ''}`}
      >
        <div className="flex items-start justify-between gap-2">
          <p className="text-sm text-slate-200">
            {truncate(query.raw_query, 72)}
          </p>
          <span
            className={`shrink-0 text-[10px] font-semibold uppercase ${
              query.blocked ? 'text-amber-400' : 'text-emerald-400'
            }`}
          >
            {query.blocked ? 'Blocked' : 'OK'}
          </span>
        </div>
        {query.blocked && query.block_reason ? (
          <p className="mt-1 text-xs text-amber-500/90">
            {truncate(query.block_reason, 96)}
          </p>
        ) : query.response ? (
          <p className="mt-1 text-xs text-slate-500">
            {truncate(query.response, 96)}
          </p>
        ) : null}
        <p className="mt-2 flex items-center justify-between text-xs text-slate-600">
          <span className="tabular-nums text-cyan-400/90">
            {formatUsd(cost)}
          </span>
          <span>{new Date(query.created_at).toLocaleTimeString()}</span>
        </p>
      </button>
    </li>
  )
}

export function AuditPanel() {
  const {
    queries,
    totalCostUsd,
    queryCount,
    realtimeStatus,
    streamError,
    setActiveQueryId,
    activeQueryId,
    lastResult,
  } = useDemo()

  const recentQueries = queries.slice(0, RECENT_LIMIT)
  const newestQueryId = recentQueries[0]?.id ?? null
  const animatedCount = useAnimatedNumber(queryCount, { durationMs: 350 })

  const prevTotalRef = useRef(totalCostUsd)
  const pulsedQueryIdsRef = useRef<Set<string>>(new Set())
  const [chargePulse, setChargePulse] = useState(false)
  const [lastDeltaUsd, setLastDeltaUsd] = useState<number | null>(null)
  const [highlightQueryId, setHighlightQueryId] = useState<string | null>(null)
  const pulseTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const highlightTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const triggerChargePulse = (delta: number, queryId?: string) => {
    if (delta <= 0) return
    if (queryId && pulsedQueryIdsRef.current.has(queryId)) return
    if (queryId) pulsedQueryIdsRef.current.add(queryId)
    setLastDeltaUsd(delta)
    setChargePulse(true)
    if (pulseTimerRef.current) clearTimeout(pulseTimerRef.current)
    pulseTimerRef.current = setTimeout(() => {
      setChargePulse(false)
      setLastDeltaUsd(null)
    }, 750)
  }

  useEffect(() => {
    const prev = prevTotalRef.current
    if (totalCostUsd > prev) {
      triggerChargePulse(
        totalCostUsd - prev,
        newestQueryId ?? lastResult?.meta.query_id,
      )
    }
    prevTotalRef.current = totalCostUsd
  }, [totalCostUsd, newestQueryId, lastResult])

  useEffect(() => {
    if (!lastResult || lastResult.meta.cost <= 0) return
    triggerChargePulse(lastResult.meta.cost, lastResult.meta.query_id)
  }, [lastResult])

  const skipInitialHighlightRef = useRef(true)

  useEffect(() => {
    if (!newestQueryId) return
    if (skipInitialHighlightRef.current) {
      skipInitialHighlightRef.current = false
      return
    }
    setHighlightQueryId(newestQueryId)
    if (highlightTimerRef.current) clearTimeout(highlightTimerRef.current)
    highlightTimerRef.current = setTimeout(
      () => setHighlightQueryId(null),
      1200,
    )
  }, [newestQueryId])

  useEffect(
    () => () => {
      if (pulseTimerRef.current) clearTimeout(pulseTimerRef.current)
      if (highlightTimerRef.current) clearTimeout(highlightTimerRef.current)
    },
    [],
  )

  return (
    <Panel
      title="Audit & billing"
      subtitle="Panel C — query log and running cost"
      badge={<StatusBadge status={realtimeStatus} />}
    >
      <div className="flex flex-1 flex-col gap-5 overflow-hidden">
        {streamError ? (
          <p className="text-sm text-amber-400" role="status">
            {streamError}
          </p>
        ) : null}

        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-lg border border-slate-800 bg-slate-950/60 px-4 py-3">
            <p className="text-xs uppercase tracking-wide text-slate-500">
              Queries
            </p>
            <p className="mt-1 text-2xl font-semibold tabular-nums text-slate-100">
              {Math.round(animatedCount)}
            </p>
            <p className="mt-0.5 text-[10px] text-slate-600">
              Last {RECENT_LIMIT} shown
            </p>
          </div>
          <CostCounter
            totalCostUsd={totalCostUsd}
            chargePulse={chargePulse}
            lastDeltaUsd={lastDeltaUsd}
          />
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto">
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">
            Recent queries
          </p>
          {recentQueries.length === 0 ? (
            <p className="text-sm text-slate-500">No queries yet.</p>
          ) : (
            <ul className="space-y-2">
              {recentQueries.map((q) => (
                <QueryListItem
                  key={q.id}
                  query={q}
                  isActive={q.id === activeQueryId}
                  isNew={q.id === highlightQueryId}
                  onSelect={() => setActiveQueryId(q.id)}
                />
              ))}
            </ul>
          )}
        </div>
      </div>
    </Panel>
  )
}
