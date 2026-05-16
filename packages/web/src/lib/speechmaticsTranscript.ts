import type { RealtimeServerMessage } from '@speechmatics/real-time-client'

export function messageToDisplayText(message: RealtimeServerMessage): string {
  if (
    message.message !== 'AddTranscript' &&
    message.message !== 'AddPartialTranscript'
  ) {
    return ''
  }

  return message.results
    .map((result) => result.alternatives?.[0]?.content ?? '')
    .join(' ')
    .trim()
}

export function appendTranscript(
  finals: string,
  message: RealtimeServerMessage,
): string {
  if (message.message === 'AddTranscript') {
    const chunk = messageToDisplayText(message)
    if (!chunk) return finals
    const spacer = finals && !finals.endsWith(' ') ? ' ' : ''
    return `${finals}${spacer}${chunk}`.trim()
  }
  return finals
}

export function liveTranscript(
  finals: string,
  message: RealtimeServerMessage,
): string {
  if (message.message === 'AddPartialTranscript') {
    const partial = messageToDisplayText(message)
    if (!partial) return finals
    const spacer = finals && !finals.endsWith(' ') ? ' ' : ''
    return `${finals}${spacer}${partial}`.trim()
  }
  if (message.message === 'AddTranscript') {
    return appendTranscript(finals, message)
  }
  return finals
}
