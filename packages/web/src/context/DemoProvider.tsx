import {
  useCallback,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

import { auditRowsToSteps } from '../lib/auditSteps'
import type { DemoContextValue } from './demoContext'
import { DemoContext } from './demoContext'
import { useAuditStream } from '../hooks/useAuditStream'
import { useQuerySubmit } from '../hooks/useQuery'
import { useSessionBilling } from '../hooks/useSessionBilling'

export function DemoProvider({ children }: { children: ReactNode }) {
  const [activeQueryId, setActiveQueryId] = useState<string | null>(null)

  const onSubmitted = useCallback((queryId: string) => {
    setActiveQueryId(queryId)
  }, [])

  const {
    status,
    error,
    lastResult,
    graphLive,
    submit: submitRaw,
  } = useQuerySubmit(onSubmitted)
  const { auditEntries, queries, realtimeStatus, loadError } =
    useAuditStream()
  const { sessionQueryCount, sessionTotalCostUsd } = useSessionBilling(
    queries,
    lastResult,
  )

  const agentSteps = useMemo(() => {
    if (!activeQueryId) return []
    const forQuery = auditEntries.filter((e) => e.query_id === activeQueryId)
    return auditRowsToSteps(forQuery)
  }, [auditEntries, activeQueryId])

  const activeQuery = useMemo(
    () => queries.find((q) => q.id === activeQueryId) ?? null,
    [queries, activeQueryId],
  )

  const submitQuery = useCallback(
    (rawQuery: string, targetCompanyId?: string | null) =>
      submitRaw(rawQuery, targetCompanyId),
    [submitRaw],
  )

  const value = useMemo<DemoContextValue>(
    () => ({
      activeQueryId,
      setActiveQueryId,
      agentSteps,
      graphLive,
      queries,
      totalCostUsd: sessionTotalCostUsd,
      queryCount: sessionQueryCount,
      realtimeStatus,
      streamError: loadError,
      submitStatus: status,
      submitError: error,
      lastResult,
      submitQuery,
      activeQuery,
    }),
    [
      activeQueryId,
      agentSteps,
      graphLive,
      queries,
      sessionTotalCostUsd,
      sessionQueryCount,
      realtimeStatus,
      loadError,
      status,
      error,
      lastResult,
      submitQuery,
      activeQuery,
    ],
  )

  return (
    <DemoContext.Provider value={value}>{children}</DemoContext.Provider>
  )
}
