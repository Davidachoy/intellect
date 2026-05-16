import {
  usePCMAudioListener,
  usePCMAudioRecorderContext,
} from '@speechmatics/browser-audio-input-react'
import type { RealtimeServerMessage } from '@speechmatics/real-time-client'
import {
  useRealtimeEventListener,
  useRealtimeTranscription,
} from '@speechmatics/real-time-client-react'
import { useCallback, useEffect, useRef, useState } from 'react'

import { SpeechmaticsJwtError, fetchSpeechmaticsJwt } from '../lib/speechmatics'
import { END_OF_UTTERANCE_SILENCE_SEC } from '../lib/speechmaticsConstants'
import {
  ensureAudioContextRunning,
  safeStopRecording,
  safeStopTranscription,
} from '../lib/speechmaticsSession'
import { appendTranscript, liveTranscript } from '../lib/speechmaticsTranscript'

export type VoiceStatus = 'idle' | 'recording' | 'processing'

export interface UseSpeechmaticsVoiceOptions {
  disabled?: boolean
  onTranscript: (text: string) => void
  onComplete: (text: string) => Promise<void>
}

export interface UseSpeechmaticsVoiceResult {
  voiceStatus: VoiceStatus
  voiceError: string | null
  isVoiceActive: boolean
  toggleVoice: () => Promise<void>
}

export function useSpeechmaticsVoice({
  disabled = false,
  onTranscript,
  onComplete,
}: UseSpeechmaticsVoiceOptions): UseSpeechmaticsVoiceResult {
  const [voiceStatus, setVoiceStatus] = useState<VoiceStatus>('idle')
  const [voiceError, setVoiceError] = useState<string | null>(null)

  const finalsRef = useRef('')
  const finalizeInFlightRef = useRef(false)
  const sessionActiveRef = useRef(false)
  const voiceStatusRef = useRef<VoiceStatus>('idle')

  useEffect(() => {
    voiceStatusRef.current = voiceStatus
  }, [voiceStatus])

  const { startTranscription, stopTranscription, sendAudio } =
    useRealtimeTranscription()
  const { startRecording, stopRecording, audioContext } =
    usePCMAudioRecorderContext()

  usePCMAudioListener(sendAudio as (pcm: Float32Array) => void)

  const endRealtimeSession = useCallback(async () => {
    safeStopRecording(stopRecording)
    if (sessionActiveRef.current) {
      sessionActiveRef.current = false
      await safeStopTranscription(stopTranscription)
    }
  }, [stopRecording, stopTranscription])

  const finalizeSession = useCallback(async () => {
    if (finalizeInFlightRef.current) return
    finalizeInFlightRef.current = true
    setVoiceStatus('processing')

    await endRealtimeSession()

    const transcript = finalsRef.current.trim()
    finalsRef.current = ''

    try {
      if (transcript) {
        onTranscript(transcript)
        await onComplete(transcript)
      }
    } finally {
      finalizeInFlightRef.current = false
      setVoiceStatus('idle')
    }
  }, [endRealtimeSession, onComplete, onTranscript])

  useRealtimeEventListener(
    'receiveMessage',
    useCallback(
      ({ data }: { data: RealtimeServerMessage }) => {
        if (voiceStatusRef.current !== 'recording') return

        if (data.message === 'AddTranscript') {
          finalsRef.current = appendTranscript(finalsRef.current, data)
          onTranscript(finalsRef.current)
          return
        }

        if (data.message === 'AddPartialTranscript') {
          onTranscript(liveTranscript(finalsRef.current, data))
          return
        }

        if (data.message === 'EndOfUtterance') {
          void finalizeSession()
        }
      },
      [finalizeSession, onTranscript],
    ),
  )

  const startVoice = useCallback(async () => {
    if (disabled) return

    setVoiceError(null)
    finalsRef.current = ''
    finalizeInFlightRef.current = false

    try {
      if (!audioContext) {
        throw new Error('Microphone audio context is not ready')
      }
      await ensureAudioContextRunning(audioContext)

      const jwt = await fetchSpeechmaticsJwt()
      const sampleRate = audioContext.sampleRate

      await startTranscription(jwt, {
        transcription_config: {
          language: 'en',
          enable_partials: true,
          operating_point: 'enhanced',
          conversation_config: {
            end_of_utterance_silence_trigger: END_OF_UTTERANCE_SILENCE_SEC,
          },
        },
        audio_format: {
          type: 'raw',
          encoding: 'pcm_f32le',
          sample_rate: sampleRate,
        },
      })
      sessionActiveRef.current = true

      await startRecording({})
      setVoiceStatus('recording')
    } catch (err) {
      const message =
        err instanceof SpeechmaticsJwtError
          ? err.message
          : err instanceof Error
            ? err.message
            : 'Voice input failed'
      setVoiceError(message)
      setVoiceStatus('idle')
      await endRealtimeSession()
    }
  }, [
    audioContext,
    disabled,
    endRealtimeSession,
    startRecording,
    startTranscription,
  ])

  const stopVoice = useCallback(async () => {
    if (voiceStatusRef.current !== 'recording') return
    await finalizeSession()
  }, [finalizeSession])

  const toggleVoice = useCallback(async () => {
    if (voiceStatusRef.current === 'processing' || disabled) return
    if (voiceStatusRef.current === 'recording') {
      await stopVoice()
      return
    }
    await startVoice()
  }, [disabled, startVoice, stopVoice])

  useEffect(() => {
    return () => {
      if (!sessionActiveRef.current) return
      void endRealtimeSession()
    }
  }, [endRealtimeSession])

  return {
    voiceStatus,
    voiceError,
    isVoiceActive: voiceStatus === 'recording',
    toggleVoice,
  }
}
