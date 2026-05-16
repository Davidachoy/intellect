import type { CompanyQueryRow, QueryTypeBucket } from './types'

const BENCHMARK_AGGREGATIONS = new Set([
  'group_by_region',
  'group_by',
  'compare',
  'trend',
  'benchmark',
])

export function aggregationToBucket(
  aggregation: string | undefined,
): QueryTypeBucket {
  const key = (aggregation ?? 'count').toLowerCase()
  if (key === 'count') return 'count'
  if (key === 'average' || key === 'sum') return 'average'
  if (key === 'percentage') return 'percentage'
  if (BENCHMARK_AGGREGATIONS.has(key)) return 'benchmark'
  return 'count'
}

export function countQueryTypeDistribution(
  queries: CompanyQueryRow[],
): Record<QueryTypeBucket, number> {
  const dist: Record<QueryTypeBucket, number> = {
    count: 0,
    average: 0,
    percentage: 0,
    benchmark: 0,
  }
  for (const q of queries) {
    const bucket = aggregationToBucket(q.structured_query?.aggregation)
    dist[bucket] += 1
  }
  return dist
}
