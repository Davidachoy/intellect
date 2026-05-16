import { useMemo } from 'react'

import { PIPELINE_NODE_ORDER } from '../lib/graphTopology'
import type { GraphLiveState, GraphNodeView } from '../lib/graphLive'

const STATUS_STYLES: Record<
  GraphNodeView['status'],
  { ring: string; bg: string; dot: string; label: string }
> = {
  idle: {
    ring: 'border-slate-700',
    bg: 'bg-slate-900/80',
    dot: 'bg-slate-600',
    label: 'text-slate-500',
  },
  pending: {
    ring: 'border-dashed border-slate-600',
    bg: 'bg-slate-950/60',
    dot: 'bg-slate-500',
    label: 'text-slate-400',
  },
  running: {
    ring: 'border-cyan-400/70 shadow-[0_0_20px_rgba(34,211,238,0.15)]',
    bg: 'bg-cyan-950/30',
    dot: 'bg-cyan-400 animate-pulse',
    label: 'text-cyan-200',
  },
  done: {
    ring: 'border-emerald-500/50',
    bg: 'bg-emerald-950/25',
    dot: 'bg-emerald-400',
    label: 'text-emerald-100',
  },
  blocked: {
    ring: 'border-red-500/60',
    bg: 'bg-red-950/30',
    dot: 'bg-red-400',
    label: 'text-red-100',
  },
  skipped: {
    ring: 'border-slate-700/80',
    bg: 'bg-slate-950/40 opacity-60',
    dot: 'bg-slate-600',
    label: 'text-slate-500',
  },
}

function statusLabel(status: GraphNodeView['status']): string {
  switch (status) {
    case 'running':
      return 'Running'
    case 'done':
      return 'Done'
    case 'blocked':
      return 'Blocked'
    case 'skipped':
      return 'Skipped'
    case 'pending':
      return 'Pending'
    default:
      return 'Idle'
  }
}

function orderedNodes(graph: GraphLiveState): GraphNodeView[] {
  const byId = new Map(graph.nodes.map((n) => [n.id, n]))
  const main = PIPELINE_NODE_ORDER.map((id) => byId.get(id)).filter(
    (n): n is GraphNodeView => n !== undefined,
  )
  const branches = graph.nodes.filter((n) => n.id.startsWith('intelligence:'))
  const intelIndex = main.findIndex((n) => n.id === 'intelligence')
  if (intelIndex >= 0 && branches.length > 0) {
    return [
      ...main.slice(0, intelIndex + 1),
      ...branches,
      ...main.slice(intelIndex + 1),
    ]
  }
  const end = byId.get('end')
  if (end && !main.some((n) => n.id === 'end')) {
    main.push(end)
  }
  return main
}

function FlowNode({ node }: { node: GraphNodeView }) {
  const style = STATUS_STYLES[node.status]

  return (
    <div
      className={`flex items-center gap-3 rounded-lg border px-3 py-2.5 ${style.ring} ${style.bg}`}
    >
      <span
        className={`h-2.5 w-2.5 shrink-0 rounded-full ${style.dot}`}
        aria-hidden
      />
      <div className="min-w-0 flex-1">
        <p className={`truncate text-sm font-medium ${style.label}`}>
          {node.label}
        </p>
        {node.detail ? (
          <p className="mt-0.5 truncate text-xs text-slate-500">{node.detail}</p>
        ) : null}
      </div>
      <span
        className={`shrink-0 text-[10px] font-semibold uppercase tracking-wide ${style.label}`}
      >
        {statusLabel(node.status)}
      </span>
    </div>
  )
}

interface PipelineFlowProps {
  graph: GraphLiveState
}

export function PipelineFlow({ graph }: PipelineFlowProps) {
  const nodes = useMemo(() => orderedNodes(graph), [graph.nodes])

  if (nodes.length === 0) {
    return (
      <p className="rounded-lg border border-dashed border-slate-700 bg-slate-950/40 px-4 py-8 text-center text-sm text-slate-500">
        Pipeline will appear when you submit a query.
      </p>
    )
  }

  return (
    <ol className="space-y-0">
      {nodes.map((node, index) => (
        <li key={node.id} className="relative">
          {index > 0 ? (
            <span
              className="absolute -top-3 left-[1.125rem] h-3 w-px bg-slate-600"
              aria-hidden
            />
          ) : null}
          <FlowNode node={node} />
        </li>
      ))}
    </ol>
  )
}
