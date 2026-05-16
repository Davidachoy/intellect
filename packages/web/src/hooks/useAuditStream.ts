import { useEffect, useState } from 'react'

import { config } from '../lib/config'
import { getSupabaseClient } from '../lib/supabase'
import type { AuditLogRow, QueryRow, RealtimeStatus } from '../lib/types'

const RECENT_QUERIES_LIMIT = 10

function mergeAuditEntry(
  prev: AuditLogRow[],
  row: AuditLogRow,
): AuditLogRow[] {
  if (prev.some((e) => e.id === row.id)) return prev
  return [...prev, row].sort(
    (a, b) => a.created_at.localeCompare(b.created_at),
  )
}

function mergeQuery(prev: QueryRow[], row: QueryRow): QueryRow[] {
  const idx = prev.findIndex((q) => q.id === row.id)
  if (idx >= 0) {
    const next = [...prev]
    next[idx] = row
    return next
  }
  return [row, ...prev]
    .sort((a, b) => b.created_at.localeCompare(a.created_at))
    .slice(0, RECENT_QUERIES_LIMIT)
}

export interface AuditStreamState {
  auditEntries: AuditLogRow[]
  queries: QueryRow[]
  realtimeStatus: RealtimeStatus
  loadError: string | null
}

export function useAuditStream(): AuditStreamState {
  const [auditEntries, setAuditEntries] = useState<AuditLogRow[]>([])
  const [queries, setQueries] = useState<QueryRow[]>([])
  const [realtimeStatus, setRealtimeStatus] = useState<RealtimeStatus>(() =>
    config.supabaseConfigured ? 'connecting' : 'disabled',
  )
  const [loadError, setLoadError] = useState<string | null>(null)

  useEffect(() => {
    const supabase = getSupabaseClient()
    if (!supabase) return

    let cancelled = false

    async function loadInitial() {
      if (!supabase) return
      setLoadError(null)
      try {
        const [auditResult, queriesResult] = await Promise.all([
          supabase
            .from('audit_log')
            .select('*')
            .order('created_at', { ascending: false })
            .limit(50),
          supabase
            .from('queries')
            .select(
              'id, raw_query, response, blocked, block_reason, cost_usd, created_at',
            )
            .order('created_at', { ascending: false })
            .limit(RECENT_QUERIES_LIMIT),
        ])

        if (cancelled) return

        if (auditResult.error) throw auditResult.error
        if (queriesResult.error) throw queriesResult.error

        const auditRows = (auditResult.data ?? []) as AuditLogRow[]
        setAuditEntries(
          [...auditRows].sort((a, b) =>
            a.created_at.localeCompare(b.created_at),
          ),
        )
        setQueries((queriesResult.data ?? []) as QueryRow[])
      } catch (err) {
        if (!cancelled) {
          setLoadError(
            err instanceof Error ? err.message : 'Failed to load audit data',
          )
          setRealtimeStatus('offline')
        }
      }
    }

    void loadInitial()

    const channel = supabase
      .channel('intellect-demo')
      .on(
        'postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'audit_log' },
        (payload) => {
          const row = payload.new as AuditLogRow
          setAuditEntries((prev) => mergeAuditEntry(prev, row))
        },
      )
      .on(
        'postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'queries' },
        (payload) => {
          const row = payload.new as QueryRow
          setQueries((prev) => mergeQuery(prev, row))
        },
      )
      .on(
        'postgres_changes',
        { event: 'UPDATE', schema: 'public', table: 'queries' },
        (payload) => {
          const row = payload.new as QueryRow
          setQueries((prev) => mergeQuery(prev, row))
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
  }, [])

  return {
    auditEntries,
    queries,
    realtimeStatus,
    loadError,
  }
}
