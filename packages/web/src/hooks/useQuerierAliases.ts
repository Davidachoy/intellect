import { useMemo, useRef } from 'react'

import type { CompanyQueryRow } from '../lib/types'

export function useQuerierAliases(queries: CompanyQueryRow[]) {
  const mapRef = useRef(new Map<string, number>())

  return useMemo(() => {
    const map = mapRef.current
    for (const q of queries) {
      if (!map.has(q.querier_api_key_hash)) {
        map.set(q.querier_api_key_hash, map.size + 1)
      }
    }
    return (hash: string) => {
      const n = map.get(hash)
      return n ? `Anonymous Querier #${n}` : 'Anonymous Querier'
    }
  }, [queries])
}
