/** Preferred sample rate for real-time STT (Speechmatics docs). */
export const RECORDING_SAMPLE_RATE =
  typeof navigator !== 'undefined' && navigator.userAgent.includes('Firefox')
    ? undefined
    : 16_000

/** Seconds of silence before EndOfUtterance (demo-friendly pause). */
export const END_OF_UTTERANCE_SILENCE_SEC = 1.5

export const SPEECHMATICS_WORKLET_URL = '/js/pcm-audio-worklet.min.js'
