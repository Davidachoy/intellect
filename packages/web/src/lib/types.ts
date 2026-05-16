export interface AuditLogRow {
  id: string
  query_id: string
  agent: string
  event: string
  payload: Record<string, unknown>
  created_at: string
}

export interface QueryRow {
  id: string
  raw_query: string
  response: string | null
  blocked: boolean
  block_reason: string | null
  cost_usd: number | null
  created_at: string
}

export interface StructuredQueryPayload {
  intent?: string
  aggregation?: string
  filters?: Record<string, unknown>
  domain?: string
}

export interface CompanyQueryRow extends QueryRow {
  target_company_id: string
  querier_api_key_hash: string
  structured_query: StructuredQueryPayload | null
}

export interface CompanyMetrics {
  totalQueries: number
  totalRevenueUsd: number
  blockedCount: number
  blockedPercent: number
  uniqueQueriers: number
}

export type QueryTypeBucket = 'count' | 'average' | 'percentage' | 'benchmark'

export interface AnomalyAlertRow {
  id: string
  querier_id: string
  pattern: string
  query_ids: string[]
  severity: 'low' | 'medium' | 'high'
  acknowledged: boolean
  created_at: string
}

export interface QueryEnvelope {
  data: {
    query_id: string
    response: string
    blocked: boolean
    block_reason: string | null
    cost_usd: number
    sensitivity_tier: string
    explanation?: string | null
  }
  meta: {
    query_id: string
    cost: number
    blocked: boolean
  }
}

export type RealtimeStatus = 'connecting' | 'connected' | 'offline' | 'disabled'

export type AgentStepStatus =
  | 'pending'
  | 'running'
  | 'approved'
  | 'blocked'
  | 'neutral'
  | 'skipped'

export interface AgentStepView {
  id: string
  agent: string
  label: string
  event: string
  decision: string
  status: AgentStepStatus
  timingMs: number | null
  elapsedMs: number | null
  createdAt: string
}

export interface PipelineSlotView {
  agent: string
  label: string
  slotStatus: 'idle' | 'pending' | 'running' | 'completed' | 'skipped'
  step: AgentStepView | null
}
