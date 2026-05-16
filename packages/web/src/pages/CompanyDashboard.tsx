import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { ActivityFeed } from '../components/ActivityFeed'
import { AnomalyBanner } from '../components/AnomalyBanner'
import { MetricCard } from '../components/MetricCard'
import { QueryTypeChart } from '../components/QueryTypeChart'
import { StatusBadge } from '../components/StatusBadge'
import { useAnomalyAlerts } from '../hooks/useAnomalyAlerts'
import { useCompanyMetrics } from '../hooks/useCompanyMetrics'
import { useQuerierAliases } from '../hooks/useQuerierAliases'
import { ACME_RETAIL_NAME } from '../lib/constants'
import { formatUptime, formatUsd } from '../lib/format'
import { config } from '../lib/config'

export function CompanyDashboard() {
  const [uptimeSeconds, setUptimeSeconds] = useState(0)
  const {
    metrics,
    feedQueries,
    queryTypeDistribution,
    realtimeStatus,
    loadError,
    newFeedIds,
    clearNewFeedId,
  } = useCompanyMetrics()
  const { activeAlert, dismissAlert, realtimeStatus: alertsStatus } =
    useAnomalyAlerts()
  const getQuerierLabel = useQuerierAliases(feedQueries)

  useEffect(() => {
    const start = Date.now()
    const id = window.setInterval(() => {
      setUptimeSeconds(Math.floor((Date.now() - start) / 1000))
    }, 1000)
    return () => window.clearInterval(id)
  }, [])

  const streamStatus =
    realtimeStatus === 'connected' || alertsStatus === 'connected'
      ? 'connected'
      : realtimeStatus

  return (
    <div className="company-dashboard min-h-screen text-slate-100">
      {activeAlert ? (
        <div className="mx-auto max-w-[90rem] px-6 pt-6">
          <AnomalyBanner alert={activeAlert} onDismiss={dismissAlert} />
        </div>
      ) : null}

      <header className="border-b border-[#1a1a2e] px-6 py-5">
        <div className="mx-auto flex max-w-[90rem] flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-4">
            <div>
              <p className="font-plex-sans text-xs font-medium uppercase tracking-[0.2em] text-[#00e5ff]/80">
                Intellect · Data owner
              </p>
              <h1 className="mt-1 font-plex-sans text-2xl font-semibold tracking-tight text-white">
                {ACME_RETAIL_NAME}
              </h1>
            </div>
            <span className="inline-flex items-center gap-2 border border-emerald-500/40 bg-emerald-500/10 px-3 py-1 font-plex-mono text-xs font-semibold uppercase tracking-wider text-emerald-400">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
              Agent Active
            </span>
            <span className="font-plex-mono text-xs tabular-nums text-slate-500">
              Uptime {formatUptime(uptimeSeconds)}
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-4">
            <StatusBadge status={streamStatus} />
            <Link
              to="/"
              className="font-plex-sans border border-[#1a1a2e] px-4 py-2 text-sm text-slate-300 transition-colors hover:border-[#00e5ff]/40 hover:text-[#00e5ff]"
            >
              ← Main demo
            </Link>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[90rem] space-y-6 px-6 py-6">
        {!config.supabaseConfigured ? (
          <p className="font-plex-sans text-sm text-amber-400/90">
            Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY for live metrics
            and Realtime.
          </p>
        ) : null}
        {loadError ? (
          <p className="font-plex-sans text-sm text-[#ff3b3b]">{loadError}</p>
        ) : null}

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <MetricCard
            label="Total queries received"
            value={metrics.totalQueries}
            delayMs={0}
          />
          <MetricCard
            label="Total revenue"
            value={metrics.totalRevenueUsd}
            format={(n) => formatUsd(n)}
            accent="cyan"
            delayMs={100}
          />
          <MetricCard
            label="Queries blocked"
            value={metrics.blockedCount}
            accent="danger"
            delayMs={200}
            suffix={
              <span className="font-plex-mono text-sm tabular-nums text-slate-500">
                {metrics.blockedPercent.toFixed(1)}% of total
              </span>
            }
          />
          <MetricCard
            label="Unique queriers"
            value={metrics.uniqueQueriers}
            delayMs={300}
          />
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <ActivityFeed
              queries={feedQueries}
              getQuerierLabel={getQuerierLabel}
              newFeedIds={newFeedIds}
              onRowSeen={clearNewFeedId}
            />
          </div>
          <QueryTypeChart distribution={queryTypeDistribution} />
        </div>
      </main>
    </div>
  )
}
