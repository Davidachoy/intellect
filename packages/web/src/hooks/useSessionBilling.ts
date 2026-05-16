import { useEffect, useRef, useState } from 'react'

import type { QueryEnvelope, QueryRow } from '../lib/types'

/**
 * Running session totals (TASK-015). Separate from the last-N query list:
 * when the UI list rolls off older rows, counts and cost still accumulate.
 */
export function useSessionBilling(
  queries: QueryRow[],
  lastResult: QueryEnvelope | null,
): { sessionQueryCount: number; sessionTotalCostUsd: number } {
  const costByQueryIdRef = useRef<Map<string, number>>(new Map())
  const [totals, setTotals] = useState({
    sessionQueryCount: 0,
    sessionTotalCostUsd: 0,
  })

  useEffect(() => {
    for (const q of queries) {
      costByQueryIdRef.current.set(q.id, Number(q.cost_usd ?? 0))
    }
    if (lastResult) {
      costByQueryIdRef.current.set(
        lastResult.meta.query_id,
        lastResult.meta.cost,
      )
    }

    let sessionTotalCostUsd = 0
    for (const cost of costByQueryIdRef.current.values()) {
      sessionTotalCostUsd += cost
    }

    setTotals({
      sessionQueryCount: costByQueryIdRef.current.size,
      sessionTotalCostUsd,
    })
  }, [queries, lastResult])

  return totals
}
