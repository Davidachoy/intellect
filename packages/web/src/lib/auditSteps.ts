import {
  agentLabel,
  pipelineIndex,
  PIPELINE_ORDER,
  stepStatus,
} from './agents'
import type {
  AgentStepView,
  AuditLogRow,
  PipelineSlotView,
} from './types'

export function decisionSummary(row: AuditLogRow): string {
  const payload = row.payload ?? {}

  switch (row.agent) {
    case 'query_router': {
      const targets = payload.target_agent_ids
      if (Array.isArray(targets) && targets.length > 0) {
        return `Routed to ${targets.length} intelligence agent(s)`
      }
      return 'Structured query ready for intelligence'
    }
    case 'benchmark': {
      const preview = payload.preview
      return typeof preview === 'string' && preview.length > 0
        ? preview
        : 'Sector benchmark aggregated across companies'
    }
    case 'explainer': {
      const explanation = payload.explanation
      return typeof explanation === 'string' && explanation.length > 0
        ? explanation
        : 'Plain-English derivation summary'
    }
    case 'intelligence': {
      const company = payload.company_name
      const insightCount = payload.insight_count
      const prefix =
        typeof company === 'string' && company.length > 0
          ? `${company}: `
          : ''
      if (typeof insightCount === 'number') {
        return `${prefix}${insightCount} aggregated insight(s) produced`
      }
      if (payload.error) {
        return `${prefix}unavailable`
      }
      return `${prefix}Aggregated insights from vector store`
    }
    case 'explainer': {
      const preview = payload.preview
      if (typeof preview === 'string' && preview.length > 0) {
        return preview
      }
      return 'Plain-English derivation recorded'
    }
    case 'synthesis': {
      const count = payload.company_count
      if (typeof count === 'number') {
        return `Merged insights from ${count} companies`
      }
      return 'Multi-company response synthesized'
    }
    case 'privacy_guard':
      if (row.event === 'blocked') {
        const reason = payload.block_reason
        return typeof reason === 'string' && reason.length > 0
          ? reason
          : 'Blocked by privacy policy'
      }
      return 'Passed k-anonymity and PII checks'
    case 'pricing': {
      const cost = payload.cost_usd
      const tier = payload.sensitivity_tier
      if (typeof cost === 'number') {
        const tierLabel =
          typeof tier === 'string' && tier.length > 0 ? tier : 'sensitive'
        return `Charged $${cost.toFixed(2)} (${tierLabel} tier)`
      }
      return 'Transaction logged to audit'
    }
    default:
      return row.event
  }
}

export function auditRowsToSteps(rows: AuditLogRow[]): AgentStepView[] {
  const sorted = [...rows].sort(
    (a, b) =>
      pipelineIndex(a.agent) - pipelineIndex(b.agent) ||
      a.created_at.localeCompare(b.created_at),
  )

  const t0 =
    sorted.length > 0 ? new Date(sorted[0].created_at).getTime() : null

  return sorted.map((row, index) => {
    const prev = index > 0 ? sorted[index - 1] : null
    const timingMs = prev
      ? new Date(row.created_at).getTime() -
        new Date(prev.created_at).getTime()
      : null
    const elapsedMs =
      t0 !== null
        ? new Date(row.created_at).getTime() - t0
        : null

    return {
      id: row.id,
      agent: row.agent,
      label: agentLabel(row.agent, row.payload),
      event: row.event,
      decision: decisionSummary(row),
      status: stepStatus(row.agent, row.event),
      timingMs,
      elapsedMs,
      createdAt: row.created_at,
    }
  })
}

function privacyBlocked(steps: AgentStepView[]): boolean {
  return steps.some(
    (s) => s.agent === 'privacy_guard' && s.status === 'blocked',
  )
}

/** Build slots for fixed pipeline agents; intelligence sub-steps render separately. */
export function buildPipelineSlots(
  steps: AgentStepView[],
  options: {
    trackActive: boolean
    isProcessing: boolean
  },
): PipelineSlotView[] {
  const { trackActive, isProcessing } = options
  const blocked = privacyBlocked(steps)
  const multiIntel = steps.filter((s) => s.agent === 'intelligence').length > 1
  let completedBefore = 0

  return PIPELINE_ORDER.map((agent) => {
    const label = agentLabel(agent)
    const step = steps.find((s) => s.agent === agent) ?? null

    if (agent === 'benchmark') {
      const hasBenchmark = steps.some((s) => s.agent === 'benchmark')
      if (!hasBenchmark) {
        return { agent, label, slotStatus: 'skipped' as const, step: null }
      }
    }

    if (agent === 'synthesis' && !multiIntel) {
      return { agent, label, slotStatus: 'skipped' as const, step: null }
    }

    if (step) {
      completedBefore += 1
      return { agent, label, slotStatus: 'completed' as const, step }
    }

    if (!trackActive) {
      return { agent, label, slotStatus: 'idle' as const, step: null }
    }

    if (agent === 'pricing' && blocked) {
      return { agent, label, slotStatus: 'skipped' as const, step: null }
    }

    const isCurrentStage =
      trackActive && isProcessing && completedBefore === steps.length

    if (isCurrentStage) {
      return { agent, label, slotStatus: 'running' as const, step: null }
    }

    return { agent, label, slotStatus: 'pending' as const, step: null }
  })
}

export function intelligenceSubSteps(steps: AgentStepView[]): AgentStepView[] {
  return steps.filter((s) => s.agent === 'intelligence')
}
