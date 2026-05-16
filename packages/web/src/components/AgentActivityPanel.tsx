import { useMemo } from 'react'

import { useDemo } from '../hooks/useDemo'
import { intelligenceSubSteps } from '../lib/auditSteps'
import { PipelineFlow } from './PipelineFlow'
import { Panel } from './Panel'
import { StatusBadge } from './StatusBadge'

export function AgentActivityPanel() {
  const {
    graphLive,
    activeQueryId,
    submitStatus,
    realtimeStatus,
    streamError,
    lastResult,
    activeQuery,
    agentSteps,
  } = useDemo()

  const isProcessing = submitStatus === 'submitting'
  const intelSubs = useMemo(
    () => intelligenceSubSteps(agentSteps),
    [agentSteps],
  )

  const showFinalResponse =
    lastResult &&
    activeQueryId === lastResult.meta.query_id &&
    (lastResult.meta.blocked || agentSteps.length > 0)

  return (
    <Panel
      title="Agent pipeline"
      subtitle="LangGraph — live node status"
      badge={<StatusBadge status={realtimeStatus} />}
      className="min-h-0 lg:min-h-[22rem]"
    >
      <div className="flex min-h-[16rem] flex-col gap-4">
        {streamError ? (
          <p className="text-sm text-amber-400" role="status">
            {streamError}
          </p>
        ) : null}

        {isProcessing ? (
          <p className="text-sm font-medium text-cyan-300/90">
            Running pipeline…
          </p>
        ) : !activeQueryId ? (
          <p className="text-sm text-slate-500">
            Submit a query to watch each agent light up in sequence.
          </p>
        ) : null}

        <div className="flex-1 rounded-xl border border-slate-800/80 bg-slate-950/40 p-4">
          <PipelineFlow graph={graphLive} />
        </div>

        {intelSubs.length > 1 ? (
          <div className="border-t border-slate-800/80 pt-3">
            <p className="mb-2 text-[10px] font-medium uppercase tracking-wide text-slate-500">
              Federated intelligence
            </p>
            <ul className="space-y-2">
              {intelSubs.map((step) => (
                <li
                  key={step.id}
                  className="rounded-lg border border-slate-800/60 bg-slate-900/50 px-3 py-2 text-xs text-slate-300"
                >
                  <span className="font-medium text-slate-200">
                    {step.label}
                  </span>
                  <span className="mt-0.5 block text-slate-500">
                    {step.decision}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {showFinalResponse ? (
          <div
            className={`rounded-lg border p-4 ${
              lastResult.meta.blocked
                ? 'border-red-500/40 bg-red-950/25'
                : 'border-emerald-500/40 bg-emerald-950/20'
            }`}
          >
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              {lastResult.meta.blocked ? 'Blocked' : 'Approved response'}
            </p>
            <p className="mt-2 text-sm leading-relaxed text-slate-200">
              {lastResult.meta.blocked
                ? activeQuery?.block_reason ??
                  lastResult.data.block_reason ??
                  'Response withheld'
                : lastResult.data.response}
            </p>
          </div>
        ) : null}
      </div>
    </Panel>
  )
}
