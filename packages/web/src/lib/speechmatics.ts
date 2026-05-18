import { API_URL } from './config'

export class SpeechmaticsJwtError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'SpeechmaticsJwtError'
    this.status = status
  }
}

/** Fetch a short-lived JWT from the API (keeps SPEECHMATICS_API_KEY server-side). */
export async function fetchSpeechmaticsJwt(): Promise<string> {
  const response = await fetch(`${API_URL}/speechmatics/jwt`)

  if (!response.ok) {
    let detail = response.statusText
    try {
      const body = (await response.json()) as { detail?: string }
      if (body.detail) detail = body.detail
    } catch {
      /* ignore */
    }
    throw new SpeechmaticsJwtError(detail, response.status)
  }

  const body = (await response.json()) as { jwt?: string }
  if (!body.jwt) {
    throw new SpeechmaticsJwtError('Missing JWT in response', response.status)
  }
  return body.jwt
}
