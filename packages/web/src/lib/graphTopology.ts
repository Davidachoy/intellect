/** LangGraph topology (mirrors packages/shared/shared/graph_topology.py). */

export const GRAPH_NODES = [
  { id: 'query_router', label: 'Query Router' },
  { id: 'benchmark', label: 'Benchmark' },
  { id: 'intelligence', label: 'Intelligence' },
  { id: 'explainer', label: 'Explainer' },
  { id: 'synthesis', label: 'Synthesis' },
  { id: 'pricing', label: 'Pricing' },
  { id: 'privacy_guard', label: 'Privacy Guard' },
  { id: 'end', label: 'END' },
] as const

export const GRAPH_EDGES = [
  { id: 'e-router-bench', source: 'query_router', target: 'benchmark' },
  { id: 'e-router-intel', source: 'query_router', target: 'intelligence' },
  { id: 'e-bench-explainer', source: 'benchmark', target: 'explainer' },
  { id: 'e-intel-explainer', source: 'intelligence', target: 'explainer' },
  { id: 'e-explainer-pricing', source: 'explainer', target: 'pricing' },
  { id: 'e-pricing-privacy', source: 'pricing', target: 'privacy_guard' },
  { id: 'e-privacy-end', source: 'privacy_guard', target: 'end' },
] as const

export const PIPELINE_NODE_ORDER = [
  'query_router',
  'benchmark',
  'intelligence',
  'explainer',
  'pricing',
  'privacy_guard',
] as const

export type GraphNodeId = (typeof GRAPH_NODES)[number]['id']
