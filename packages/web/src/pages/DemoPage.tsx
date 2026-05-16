import { Link } from 'react-router-dom'

import { AgentActivityPanel } from '../components/AgentActivityPanel'
import { AuditPanel } from '../components/AuditPanel'
import { QueryPanel } from '../components/QueryPanel'
import { DemoProvider } from '../context/DemoProvider'
import { config } from '../lib/config'

export function DemoPage() {
  return (
    <DemoProvider>
      <div className="demo-page min-h-screen text-slate-100">
        <header className="border-b border-slate-800/60 bg-slate-950/80 backdrop-blur-md">
          <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-6 py-5">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.25em] text-cyan-400/90">
                Intellect
              </p>
              <h1 className="mt-1 text-xl font-semibold tracking-tight text-white sm:text-2xl">
                Intelligence marketplace
              </h1>
              <p className="mt-1 max-w-lg text-sm text-slate-400">
                Query Acme Retail, NordLogistics, or MedResearch. Aggregated
                insights only — raw data never leaves the vault.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <Link
                to="/company"
                className="rounded-lg border border-slate-700/80 bg-slate-900/60 px-4 py-2 text-sm text-slate-200 transition hover:border-cyan-500/40 hover:text-cyan-300"
              >
                Company dashboard
              </Link>
              {!config.supabaseConfigured ? (
                <p className="text-xs text-amber-400/90">
                  Realtime off — set Supabase env vars
                </p>
              ) : null}
            </div>
          </div>
        </header>

        <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
          <div className="grid gap-6 lg:grid-cols-12 lg:items-start">
            <aside className="lg:sticky lg:top-6 lg:col-span-4 xl:col-span-3">
              <QueryPanel />
            </aside>

            <div className="flex flex-col gap-6 lg:col-span-8 xl:col-span-9">
              <AgentActivityPanel />
              <AuditPanel />
            </div>
          </div>
        </main>
      </div>
    </DemoProvider>
  )
}
