import { useCallback, useRef, useState } from 'react'

import {
  QuerySubmitError,
  submitQueryStream,
  type StreamEvent,
} from '../lib/api'
import {
  applyGraphNodeEnd,
  applyGraphNodeStart,
  initialGraphState,
  resetGraphForQuery,
  type GraphLiveState,
} from '../lib/graphLive'
import { config } from '../lib/config'
import type { QueryEnvelope } from '../lib/types'

export type SubmitStatus = 'idle' | 'submitting' | 'success' | 'error'

export interface UseQuerySubmitResult {
  status: SubmitStatus
  error: string | null
  lastResult: QueryEnvelope | null
  graphLive: GraphLiveState
  submit: (
    rawQuery: string,
    targetCompanyId?: string | null,
  ) => Promise<QueryEnvelope | null>
}

export function useQuerySubmit(
  onSubmitted?: (queryId: string) => void,
): UseQuerySubmitResult {
  const [status, setStatus] = useState<SubmitStatus>('idle')
  const [error, setError] = useState<string | null>(null)
  const [lastResult, setLastResult] = useState<QueryEnvelope | null>(null)
  const [graphLive, setGraphLive] = useState<GraphLiveState>(initialGraphState)
  const activeQueryIdRef = useRef<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  const submit = useCallback(
    async (
      rawQuery: string,
      targetCompanyId?: string | null,
    ): Promise<QueryEnvelope | null> => {
      const trimmed = rawQuery.trim()
      if (!trimmed) return null

      abortRef.current?.abort()
      const controller = new AbortController()
      abortRef.current = controller
      activeQueryIdRef.current = null

      setStatus('submitting')
      setError(null)
      setGraphLive(resetGraphForQuery())

      const isActiveQuery = (queryId: string) =>
        activeQueryIdRef.current === queryId

      const handleEvent = (event: StreamEvent) => {
        const queryId =
          'query_id' in event ? event.query_id : undefined
        if (!queryId) return

        if (event.type === 'query_started') {
          activeQueryIdRef.current = queryId
        } else if (!isActiveQuery(queryId)) {
          return
        }

        if (event.type === 'node_start') {
          setGraphLive((prev) => applyGraphNodeStart(prev, event.node))
        } else if (event.type === 'node_end') {
          setGraphLive((prev) =>
            applyGraphNodeEnd(prev, event.node, event.update),
          )
        }
      }

      try {
        const envelope = await submitQueryStream(
          trimmed,
          config.demoApiKey,
          {
            targetCompanyId: targetCompanyId || undefined,
            onEvent: handleEvent,
            signal: controller.signal,
          },
        )
        if (controller.signal.aborted) return null
        setLastResult(envelope)
        setStatus('success')
        onSubmitted?.(envelope.meta.query_id)
        return envelope
      } catch (err) {
        if (controller.signal.aborted) return null
        const message =
          err instanceof QuerySubmitError
            ? err.message
            : err instanceof Error
              ? err.message
              : 'Query failed'
        setError(message)
        setStatus('error')
        setGraphLive(initialGraphState())
        return null
      }
    },
    [onSubmitted],
  )

  return { status, error, lastResult, graphLive, submit }
}
