import { createContext } from 'react'

import type { GraphLiveState } from '../lib/graphLive'
import type {
  AgentStepView,
  QueryEnvelope,
  QueryRow,
  RealtimeStatus,
} from '../lib/types'
import type { SubmitStatus } from '../hooks/useQuery'

export interface DemoContextValue {
  activeQueryId: string | null
  setActiveQueryId: (id: string | null) => void
  agentSteps: AgentStepView[]
  graphLive: GraphLiveState
  queries: QueryRow[]
  totalCostUsd: number
  queryCount: number
  realtimeStatus: RealtimeStatus
  streamError: string | null
  submitStatus: SubmitStatus
  submitError: string | null
  lastResult: QueryEnvelope | null
  submitQuery: (
    rawQuery: string,
    targetCompanyId?: string | null,
  ) => Promise<QueryEnvelope | null>
  activeQuery: QueryRow | null
}

export const DemoContext = createContext<DemoContextValue | null>(null)
