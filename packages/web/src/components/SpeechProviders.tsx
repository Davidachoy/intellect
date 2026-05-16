import { PCMAudioRecorderProvider } from '@speechmatics/browser-audio-input-react'
import { RealtimeTranscriptionProvider } from '@speechmatics/real-time-client-react'
import type { ReactNode } from 'react'

import { useAudioContext } from '../hooks/useAudioContext'
import { SPEECHMATICS_WORKLET_URL } from '../lib/speechmaticsConstants'

export function SpeechProviders({ children }: { children: ReactNode }) {
  const audioContext = useAudioContext()

  return (
    <RealtimeTranscriptionProvider appId="intellect-demo">
      <PCMAudioRecorderProvider
        audioContext={audioContext}
        workletScriptURL={SPEECHMATICS_WORKLET_URL}
      >
        {children}
      </PCMAudioRecorderProvider>
    </RealtimeTranscriptionProvider>
  )
}
