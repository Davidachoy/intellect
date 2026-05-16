import { useCallback, useEffect, useMemo, useState } from 'react'

import {
  ACME_RETAIL_COMPANY_ID,
  ACTIVITY_FEED_LIMIT,
} from '../lib/constants'
import { countQueryTypeDistribution } from '../lib/queryTypes'
import { config } from '../lib/config'
import { getSupabaseClient } from '../lib/supabase'
import type {
  CompanyMetrics,
  CompanyQueryRow,
  QueryTypeBucket,
  RealtimeStatus,
} from '../lib/types'

const COMPANY_QUERY_SELECT =
  'id, raw_query, response, blocked, block_reason, cost_usd, created_at, target_company_id, querier_api_key_hash, structured_query'

function computeMetrics(rows: CompanyQueryRow[]): CompanyMetrics {
  const totalQueries = rows.length
  const blockedCount = rows.filter((r) => r.blocked).length
  const totalRevenueUsd = rows.reduce(
    (sum, r) => sum + (r.cost_usd ?? 0),
    0,
  )
  const uniqueQueriers = new Set(
    rows.map((r) => r.querier_api_key_hash),
  ).size
  const blockedPercent =
    totalQueries === 0 ? 0 : (blockedCount / totalQueries) * 100

  return {
    totalQueries,
    totalRevenueUsd,
    blockedCount,
    blockedPercent,
    uniqueQueriers,
  }
}

function mergeCompanyQuery(
  prev: CompanyQueryRow[],
  row: CompanyQueryRow,
): CompanyQueryRow[] {
  const idx = prev.findIndex((q) => q.id === row.id)
  if (idx >= 0) {
    const next = [...prev]
    next[idx] = row
    return next
  }
  return [row, ...prev]
}

function isAcmeQuery(row: CompanyQueryRow): boolean {
  return row.target_company_id === ACME_RETAIL_COMPANY_ID
}

export interface CompanyMetricsState {
  metrics: CompanyMetrics
  feedQueries: CompanyQueryRow[]
  queryTypeDistribution: Record<QueryTypeBucket, number>
  realtimeStatus: RealtimeStatus
  loadError: string | null
  newFeedIds: Set<string>
  clearNewFeedId: (id: string) => void
}

export function useCompanyMetrics(): CompanyMetricsState {
  const [allQueries, setAllQueries] = useState<CompanyQueryRow[]>([])
  const [newFeedIds, setNewFeedIds] = useState<Set<string>>(() => new Set())
  const [realtimeStatus, setRealtimeStatus] = useState<RealtimeStatus>(() =>
    config.supabaseConfigured ? 'connecting' : 'disabled',
  )
  const [loadError, setLoadError] = useState<string | null>(null)

  const applyRow = useCallback((row: CompanyQueryRow, isInsert: boolean) => {
    if (!isAcmeQuery(row)) return
    setAllQueries((prev) => mergeCompanyQuery(prev, row))
    if (isInsert) {
      setNewFeedIds((prev) => new Set(prev).add(row.id))
    }
  }, [])

  useEffect(() => {
    const supabase = getSupabaseClient()
    if (!supabase) return

    let cancelled = false

    async function loadInitial(db: NonNullable<ReturnType<typeof getSupabaseClient>>) {
      setLoadError(null)
      try {
        const { data, error } = await db
          .from('queries')
          .select(COMPANY_QUERY_SELECT)
          .eq('target_company_id', ACME_RETAIL_COMPANY_ID)
          .order('created_at', { ascending: false })

        if (cancelled) return
        if (error) throw error

        const rows = (data ?? []) as CompanyQueryRow[]
        setAllQueries(rows)
      } catch (err) {
        if (!cancelled) {
          setLoadError(
            err instanceof Error ? err.message : 'Failed to load company data',
          )
          setRealtimeStatus('offline')
        }
      }
    }

    void loadInitial(supabase)

    const channel = supabase
      .channel('intellect-demo')
      .on(
        'postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'queries' },
        (payload) => {
          applyRow(payload.new as CompanyQueryRow, true)
        },
      )
      .on(
        'postgres_changes',
        { event: 'UPDATE', schema: 'public', table: 'queries' },
        (payload) => {
          applyRow(payload.new as CompanyQueryRow, false)
        },
      )
      .subscribe((status) => {
        if (status === 'SUBSCRIBED') {
          setRealtimeStatus('connected')
        } else if (status === 'CHANNEL_ERROR' || status === 'TIMED_OUT') {
          setRealtimeStatus('offline')
        }
      })

    return () => {
      cancelled = true
      void supabase.removeChannel(channel)
    }
  }, [applyRow])

  const metrics = useMemo(() => computeMetrics(allQueries), [allQueries])

  const feedQueries = useMemo(
    () =>
      [...allQueries]
        .sort((a, b) => b.created_at.localeCompare(a.created_at))
        .slice(0, ACTIVITY_FEED_LIMIT),
    [allQueries],
  )

  const queryTypeDistribution = useMemo(
    () => countQueryTypeDistribution(allQueries),
    [allQueries],
  )

  const clearNewFeedId = useCallback((id: string) => {
    setNewFeedIds((prev) => {
      if (!prev.has(id)) return prev
      const next = new Set(prev)
      next.delete(id)
      return next
    })
  }, [])

  return {
    metrics,
    feedQueries,
    queryTypeDistribution,
    realtimeStatus,
    loadError,
    newFeedIds,
    clearNewFeedId,
  }
}
