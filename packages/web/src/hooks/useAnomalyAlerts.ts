import { useCallback, useEffect, useState } from 'react'

import { config } from '../lib/config'
import { getSupabaseClient } from '../lib/supabase'
import type { AnomalyAlertRow, RealtimeStatus } from '../lib/types'

export interface AnomalyAlertsState {
  activeAlert: AnomalyAlertRow | null
  dismissAlert: () => void
  realtimeStatus: RealtimeStatus
}

export function useAnomalyAlerts(): AnomalyAlertsState {
  const [activeAlert, setActiveAlert] = useState<AnomalyAlertRow | null>(null)
  const [dismissedId, setDismissedId] = useState<string | null>(null)
  const [realtimeStatus, setRealtimeStatus] = useState<RealtimeStatus>(() =>
    config.supabaseConfigured ? 'connecting' : 'disabled',
  )

  const dismissAlert = useCallback(() => {
    setActiveAlert((current) => {
      if (current) setDismissedId(current.id)
      return null
    })
  }, [])

  useEffect(() => {
    const supabase = getSupabaseClient()
    if (!supabase) return

    const channel = supabase
      .channel('intellect-alerts')
      .on(
        'postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'anomaly_alerts' },
        (payload) => {
          const row = payload.new as AnomalyAlertRow
          setDismissedId(null)
          setActiveAlert(row)
        },
      )
      .subscribe((status) => {
        if (status === 'SUBSCRIBED') {
          setRealtimeStatus('connected')
        } else if (status === 'CHANNEL_ERROR' || status === 'TIMED_OUT') {
          setRealtimeStatus('offline')
        }
      })

    return () => {
      void supabase.removeChannel(channel)
    }
  }, [])

  const visibleAlert =
    activeAlert && activeAlert.id !== dismissedId ? activeAlert : null

  return {
    activeAlert: visibleAlert,
    dismissAlert,
    realtimeStatus,
  }
}
