import { useSyncExternalStore } from 'react'

import { RECORDING_SAMPLE_RATE } from '../lib/speechmaticsConstants'

function useHydrated(): boolean {
  return useSyncExternalStore(
    () => () => {},
    () => true,
    () => false,
  )
}

/** Shared across remounts; Speechmatics docs: leave AudioContext open for reuse. */
let sharedAudioContext: AudioContext | undefined

function getOrCreateSharedAudioContext(): AudioContext {
  if (!sharedAudioContext || sharedAudioContext.state === 'closed') {
    sharedAudioContext = new window.AudioContext(
      RECORDING_SAMPLE_RATE ? { sampleRate: RECORDING_SAMPLE_RATE } : undefined,
    )
  }
  return sharedAudioContext
}

export function useAudioContext(): AudioContext | undefined {
  const hydrated = useHydrated()
  if (!hydrated) return undefined
  return getOrCreateSharedAudioContext()
}
