import { useCallback, useState, type FormEvent } from 'react'

import { DEMO_COMPANIES } from '../lib/agents'
import { useDemo } from '../hooks/useDemo'
import { useSpeechmaticsVoice } from '../hooks/useSpeechmaticsVoice'
import { Panel } from './Panel'
import { SpeechProviders } from './SpeechProviders'

const DEMO_PLACEHOLDER =
  'Compare Acme Retail clients in Italy with NordLogistics shipments to Italy'

function VoiceSpinner() {
  return (
    <span
      className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-slate-400 border-t-cyan-400"
      aria-hidden
    />
  )
}

function QueryPanelForm() {
  const { submitQuery, submitStatus, submitError, lastResult } = useDemo()
  const [text, setText] = useState('')
  const [targetCompanyId, setTargetCompanyId] = useState('')

  const isSubmitting = submitStatus === 'submitting'

  const runSubmit = useCallback(
    async (query: string) => {
      if (isSubmitting) return
      const result = await submitQuery(
        query,
        targetCompanyId || null,
      )
      if (result && !result.meta.blocked) {
        setText('')
      }
    },
    [submitQuery, targetCompanyId, isSubmitting],
  )

  const handleVoiceComplete = useCallback(
    async (transcript: string) => {
      await runSubmit(transcript)
    },
    [runSubmit],
  )

  const { voiceStatus, voiceError, toggleVoice } = useSpeechmaticsVoice({
    disabled: isSubmitting,
    onTranscript: setText,
    onComplete: handleVoiceComplete,
  })

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    await runSubmit(text)
  }

  const voiceBusy = voiceStatus === 'recording' || voiceStatus === 'processing'
  const controlsDisabled = isSubmitting || voiceBusy

  return (
    <form onSubmit={(e) => void handleSubmit(e)} className="flex flex-1 flex-col gap-4">
      <div>
        <label
          htmlFor="target-company"
          className="text-xs font-medium uppercase tracking-wide text-slate-500"
        >
          Data source
        </label>
        <select
          id="target-company"
          value={targetCompanyId}
          onChange={(e) => setTargetCompanyId(e.target.value)}
          disabled={controlsDisabled}
          className="mt-1.5 w-full rounded-lg border border-slate-700/80 bg-slate-950/80 px-3 py-2 text-sm text-slate-100 focus:border-cyan-500/60 focus:outline-none focus:ring-2 focus:ring-cyan-500/20 disabled:opacity-60"
        >
          {DEMO_COMPANIES.map((c) => (
            <option key={c.id || 'auto'} value={c.id}>
              {c.label}
            </option>
          ))}
        </select>
      </div>

      <label className="sr-only" htmlFor="query-input">
        Natural language query
      </label>
      <textarea
        id="query-input"
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder={DEMO_PLACEHOLDER}
        rows={6}
        disabled={controlsDisabled}
        className="w-full flex-1 resize-none rounded-lg border border-slate-700/80 bg-slate-950/80 px-4 py-3 text-sm text-slate-100 placeholder:text-slate-600 focus:border-cyan-500/60 focus:outline-none focus:ring-2 focus:ring-cyan-500/20 disabled:opacity-60"
      />

      <div className="flex flex-wrap items-center gap-3">
        <button
          type="submit"
          disabled={controlsDisabled || !text.trim()}
          className="rounded-lg bg-cyan-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-cyan-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isSubmitting ? 'Running pipeline…' : 'Submit query'}
        </button>

        <button
          type="button"
          onClick={() => void toggleVoice()}
          disabled={isSubmitting || voiceStatus === 'processing'}
          aria-pressed={voiceStatus === 'recording'}
          aria-label={
            voiceStatus === 'recording'
              ? 'Stop voice input and submit'
              : voiceStatus === 'processing'
                ? 'Finalizing voice transcript'
                : 'Start voice input'
          }
          className={`inline-flex items-center gap-2 rounded-lg border px-4 py-2.5 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50 ${
            voiceStatus === 'recording'
              ? 'border-red-500/50 bg-red-950/40 text-red-200 hover:bg-red-950/60'
              : 'border-slate-700 bg-slate-800/80 text-slate-200 hover:border-slate-600 hover:bg-slate-800'
          }`}
        >
          {voiceStatus === 'processing' ? (
            <>
              <VoiceSpinner />
              Processing…
            </>
          ) : voiceStatus === 'recording' ? (
            <>
              <span
                className="h-2.5 w-2.5 animate-pulse rounded-full bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.8)]"
                aria-hidden
              />
              Stop & submit
            </>
          ) : (
            <>
              <span
                className="h-2 w-2 rounded-full bg-slate-500"
                aria-hidden
              />
              Voice query
            </>
          )}
        </button>
      </div>

      {voiceError ? (
        <p className="text-sm text-red-400" role="alert">
          {voiceError}
        </p>
      ) : null}

      {submitError ? (
        <p className="text-sm text-red-400" role="alert">
          {submitError}
        </p>
      ) : null}

      {lastResult ? (
        <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
            Latest response
          </p>
          {lastResult.meta.blocked ? (
            <p className="mt-2 text-sm text-amber-300">
              Blocked by Privacy Guard
              {lastResult.data.block_reason
                ? `: ${lastResult.data.block_reason}`
                : ''}
            </p>
          ) : (
            <>
              <p className="mt-2 text-sm leading-relaxed text-slate-200">
                {lastResult.data.response || 'No response text'}
              </p>
              {lastResult.data.explanation ? (
                <p className="mt-2 text-xs leading-relaxed text-slate-500">
                  {lastResult.data.explanation}
                </p>
              ) : null}
            </>
          )}
          <p className="mt-3 text-xs text-slate-500">
            Cost ${lastResult.meta.cost.toFixed(2)} · Query{' '}
            {lastResult.meta.query_id.slice(0, 8)}…
          </p>
        </div>
      ) : (
        <p className="text-xs text-slate-500">
          Marketplace mode: auto-route queries Acme Retail, NordLogistics, and
          MedResearch. Raw rows never appear — aggregated insights only.
        </p>
      )}
    </form>
  )
}

export function QueryPanel() {
  return (
    <Panel
      title="Analyst query"
      subtitle="Panel A — voice or text across the intelligence marketplace"
    >
      <SpeechProviders>
        <QueryPanelForm />
      </SpeechProviders>
    </Panel>
  )
}
