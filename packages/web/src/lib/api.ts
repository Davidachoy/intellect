import { API_URL } from './config'
import type { QueryEnvelope } from './types'

export class QuerySubmitError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'QuerySubmitError'
    this.status = status
  }
}

type ValidationIssue = { msg?: string; loc?: (string | number)[] }

function formatApiErrorDetail(
  detail: unknown,
  fallback: string,
): string {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const issues = detail as ValidationIssue[]
    const messages = issues
      .map((issue) => {
        const field = issue.loc?.slice(-1)[0]
        const msg = issue.msg ?? 'Invalid value'
        return field ? `${String(field)}: ${msg}` : msg
      })
      .filter(Boolean)
    if (messages.length > 0) return messages.join('; ')
  }
  return fallback
}

async function readApiErrorDetail(
  response: Response,
): Promise<string> {
  const fallback = response.statusText
  try {
    const errBody = (await response.json()) as { detail?: unknown }
    if (errBody.detail !== undefined) {
      return formatApiErrorDetail(errBody.detail, fallback)
    }
  } catch {
    /* ignore */
  }
  return fallback
}

export interface SubmitQueryOptions {
  targetCompanyId?: string | null
  signal?: AbortSignal
}

export type StreamEvent =
  | { type: 'query_started'; query_id: string; nodes: string[] }
  | { type: 'node_start'; query_id: string; node: string }
  | {
      type: 'node_end'
      query_id: string
      node: string
      update: Record<string, unknown>
    }
  | { type: 'complete'; query_id: string; envelope: QueryEnvelope }
  | { type: 'error'; query_id: string; message: string }

export async function submitQuery(
  rawQuery: string,
  querierApiKey: string,
  options: SubmitQueryOptions = {},
): Promise<QueryEnvelope> {
  const body: Record<string, string> = {
    raw_query: rawQuery,
    querier_api_key: querierApiKey,
  }
  if (options.targetCompanyId) {
    body.target_company_id = options.targetCompanyId
  }

  const response = await fetch(`${API_URL}/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    const detail = await readApiErrorDetail(response)
    throw new QuerySubmitError(detail, response.status)
  }

  return (await response.json()) as QueryEnvelope
}

export async function submitQueryStream(
  rawQuery: string,
  querierApiKey: string,
  options: SubmitQueryOptions & {
    onEvent: (event: StreamEvent) => void
  },
): Promise<QueryEnvelope> {
  const body: Record<string, string> = {
    raw_query: rawQuery,
    querier_api_key: querierApiKey,
  }
  if (options.targetCompanyId) {
    body.target_company_id = options.targetCompanyId
  }

  const response = await fetch(`${API_URL}/query/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal: options.signal,
  })

  if (!response.ok) {
    const detail = await readApiErrorDetail(response)
    throw new QuerySubmitError(detail, response.status)
  }

  const reader = response.body?.getReader()
  if (!reader) {
    throw new QuerySubmitError('No response body', 500)
  }

  const decoder = new TextDecoder()
  let buffer = ''
  let envelope: QueryEnvelope | null = null

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const parts = buffer.split('\n\n')
    buffer = parts.pop() ?? ''
    for (const part of parts) {
      const line = part.trim()
      if (!line.startsWith('data:')) continue
      const json = line.slice(5).trim()
      if (!json) continue
      const event = JSON.parse(json) as StreamEvent
      options.onEvent(event)
      if (event.type === 'complete') {
        envelope = event.envelope
      }
      if (event.type === 'error') {
        throw new QuerySubmitError(event.message, 500)
      }
    }
  }

  if (!envelope) {
    throw new QuerySubmitError('Stream ended without result', 500)
  }
  return envelope
}
