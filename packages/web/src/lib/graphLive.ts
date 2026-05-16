import { GRAPH_NODES, PIPELINE_NODE_ORDER } from './graphTopology'

export type GraphNodeStatus =
  | 'idle'
  | 'pending'
  | 'running'
  | 'done'
  | 'blocked'
  | 'skipped'

export interface GraphNodeView {
  id: string
  label: string
  status: GraphNodeStatus
  detail?: string
}

export interface GraphLiveState {
  nodes: GraphNodeView[]
  activeEdge: string | null
}

const BASE_LABELS: Record<string, string> = Object.fromEntries(
  GRAPH_NODES.map((n) => [n.id, n.label]),
)

export function initialGraphState(): GraphLiveState {
  return {
    nodes: PIPELINE_NODE_ORDER.map((id) => ({
      id,
      label: BASE_LABELS[id] ?? id,
      status: 'idle' as const,
    })),
    activeEdge: null,
  }
}

export function resetGraphForQuery(): GraphLiveState {
  return {
    nodes: PIPELINE_NODE_ORDER.map((id) => ({
      id,
      label: BASE_LABELS[id] ?? id,
      status: 'pending',
    })),
    activeEdge: null,
  }
}

function setNodeStatus(
  nodes: GraphNodeView[],
  nodeId: string,
  status: GraphNodeStatus,
  detail?: string,
): GraphNodeView[] {
  const exists = nodes.some((n) => n.id === nodeId)
  const next = exists
    ? nodes.map((n) =>
        n.id === nodeId ? { ...n, status, detail: detail ?? n.detail } : n,
      )
    : [
        ...nodes,
        {
          id: nodeId,
          label: BASE_LABELS[nodeId] ?? nodeId,
          status,
          detail,
        },
      ]
  return next
}

function edgeId(source: string, target: string): string {
  return `${source}->${target}`
}

function completePriorRunningNodes(
  nodes: GraphNodeView[],
  targetNode: string,
): GraphNodeView[] {
  const idx = PIPELINE_NODE_ORDER.indexOf(
    targetNode as (typeof PIPELINE_NODE_ORDER)[number],
  )
  if (idx <= 0) return nodes
  let next = nodes
  for (let i = 0; i < idx; i += 1) {
    const id = PIPELINE_NODE_ORDER[i]
    const current = next.find((n) => n.id === id)
    if (current?.status === 'running') {
      next = setNodeStatus(next, id, 'done')
    }
  }
  return next
}

export function applyGraphNodeStart(
  state: GraphLiveState,
  node: string,
): GraphLiveState {
  let nodes = completePriorRunningNodes(state.nodes, node)
  nodes = setNodeStatus(nodes, node, 'running')
  if (node === 'synthesis') {
    nodes = setNodeStatus(nodes, 'synthesis', 'running')
  }
  const idx = PIPELINE_NODE_ORDER.indexOf(node as (typeof PIPELINE_NODE_ORDER)[number])
  const prev =
    idx > 0 ? PIPELINE_NODE_ORDER[idx - 1] : null
  return {
    nodes,
    activeEdge: prev ? edgeId(prev, node) : null,
  }
}

export function applyGraphNodeEnd(
  state: GraphLiveState,
  node: string,
  update: Record<string, unknown>,
): GraphLiveState {
  let nodes = [...state.nodes]

  if (node === 'intelligence') {
    const rawResults =
      (update.intelligence_results as Array<Record<string, unknown>>) ?? []
    const companies =
      rawResults.length > 0
        ? rawResults
        : ((update.companies as Array<Record<string, unknown>>) ?? [])
    if (companies.length > 1) {
      nodes = nodes.filter((n) => !n.id.startsWith('intelligence:'))
      const seenAgents = new Set<string>()
      for (const c of companies) {
        const agentKey = String(c.agent_id ?? c.company_name ?? '')
        if (seenAgents.has(agentKey)) continue
        seenAgents.add(agentKey)
        const name = String(c.company_name ?? 'Intelligence')
        const subId = `intelligence:${agentKey}`
        const err = c.error
        const counts = c.record_counts as number[] | undefined
        nodes.push({
          id: subId,
          label: `Intelligence · ${name}`,
          status: err ? 'blocked' : 'done',
          detail: err
            ? String(err)
            : counts?.length
              ? `n=${counts.join(',')}`
              : undefined,
        })
      }
      nodes = setNodeStatus(nodes, 'intelligence', 'done', `${companies.length} agents`)
    } else {
      nodes = setNodeStatus(nodes, 'intelligence', 'done')
    }
    if (companies.length > 1) {
      nodes = setNodeStatus(nodes, 'synthesis', 'done', 'Merged')
    } else {
      nodes = setNodeStatus(
        nodes,
        'synthesis',
        'skipped',
        companies.length === 0 ? 'No agents' : 'Single company',
      )
    }
  } else if (node === 'privacy_guard') {
    const passed = update.passed_privacy !== false
    nodes = setNodeStatus(
      nodes,
      'privacy_guard',
      passed ? 'done' : 'blocked',
      passed ? 'Approved' : String(update.block_reason ?? 'Blocked'),
    )
    if (!nodes.some((n) => n.id === 'end')) {
      nodes.push({
        id: 'end',
        label: 'END',
        status: passed ? 'done' : 'blocked',
      })
    } else {
      nodes = setNodeStatus(nodes, 'end', passed ? 'done' : 'blocked')
    }
  } else if (node === 'pricing') {
    const tier = update.sensitivity_tier
    const cost = update.cost_usd
    nodes = setNodeStatus(
      nodes,
      'pricing',
      'done',
      typeof cost === 'number'
        ? `$${cost.toFixed(2)} (${String(tier ?? 'tier')})`
        : undefined,
    )
  } else {
    nodes = setNodeStatus(nodes, node, 'done')
  }

  return { nodes, activeEdge: null }
}

export function markPricingSkipped(state: GraphLiveState): GraphLiveState {
  return {
    ...state,
    nodes: setNodeStatus(state.nodes, 'pricing', 'skipped', 'Privacy block'),
  }
}
