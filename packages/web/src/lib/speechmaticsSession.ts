/** Best-effort teardown helpers for Speechmatics realtime + PCM recorder. */

export function isSpeechmaticsSocketError(err: unknown): boolean {
  if (!(err instanceof Error)) return false
  return (
    err.name === 'SpeechmaticsRealtimeError' ||
    /socket not initialized/i.test(err.message)
  )
}

export async function safeStopTranscription(
  stop: () => Promise<unknown>,
): Promise<void> {
  try {
    await stop()
  } catch (err) {
    if (!isSpeechmaticsSocketError(err)) throw err
  }
}

export function safeStopRecording(stop: () => void): void {
  try {
    stop()
  } catch {
    /* recorder may already be stopped */
  }
}

export async function ensureAudioContextRunning(
  context: AudioContext,
): Promise<void> {
  if (context.state === 'closed') {
    throw new Error('Microphone audio context is not ready')
  }
  if (context.state === 'suspended') {
    await context.resume()
  }
}
