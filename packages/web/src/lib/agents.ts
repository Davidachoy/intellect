const AGENT_LABELS: Record<string, string> = {
  query_router: 'Query Router',
  benchmark: 'Benchmark',
  intelligence: 'Intelligence',
  explainer: 'Query Explainer',
  synthesis: 'Synthesis',
  privacy_guard: 'Privacy Guard',
  pricing: 'Pricing',
  data_quality: 'Data Quality',
}

/** Matches LangGraph execution order (packages/agents/graph.py). */
export const PIPELINE_ORDER = [
  'query_router',
  'benchmark',
  'intelligence',
  'explainer',
  'synthesis',
  'pricing',
  'privacy_guard',
] as const

export type PipelineAgent = (typeof PIPELINE_ORDER)[number]

export const DEMO_COMPANIES = [
  { id: '', label: 'Auto-route (marketplace)' },
  {
    id: 'a0000000-0000-4000-8000-000000000001',
    label: 'Acme Retail',
  },
  {
    id: 'a0000000-0000-4000-8000-000000000002',
    label: 'NordLogistics',
  },
  {
    id: 'a0000000-0000-4000-8000-000000000003',
    label: 'MedResearch',
  },
] as const

export function agentLabel(
  agent: string,
  payload?: Record<string, unknown>,
): string {
  if (agent === 'intelligence') {
    const company = payload?.company_name
    if (typeof company === 'string' && company.length > 0) {
      return `Intelligence · ${company}`
    }
  }
  return AGENT_LABELS[agent] ?? agent
}

export function pipelineIndex(agent: string): number {
  const base = agent.split(':')[0]
  const idx = PIPELINE_ORDER.indexOf(base as PipelineAgent)
  return idx === -1 ? 99 : idx
}

export function stepStatus(
  agent: string,
  event: string,
): 'approved' | 'blocked' | 'neutral' {
  if (agent === 'privacy_guard') {
    if (event === 'blocked') return 'blocked'
    if (event === 'approved') return 'approved'
  }
  if (event === 'charged') return 'approved'
  if (event === 'merged') return 'approved'
  if (event === 'skipped') return 'neutral'
  return 'neutral'
}
