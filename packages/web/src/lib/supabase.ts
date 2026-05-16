import { createClient, type SupabaseClient } from '@supabase/supabase-js'

import { config } from './config'
import type { AnomalyAlertRow, AuditLogRow, CompanyQueryRow } from './types'

export type IntellectDatabase = {
  public: {
    Tables: {
      audit_log: {
        Row: AuditLogRow
        Insert: AuditLogRow
        Update: Partial<AuditLogRow>
      }
      queries: {
        Row: CompanyQueryRow
        Insert: CompanyQueryRow
        Update: Partial<CompanyQueryRow>
      }
      anomaly_alerts: {
        Row: AnomalyAlertRow
        Insert: AnomalyAlertRow
        Update: Partial<AnomalyAlertRow>
      }
    }
  }
}

let client: SupabaseClient<IntellectDatabase> | null = null

export function getSupabaseClient(): SupabaseClient<IntellectDatabase> | null {
  if (!config.supabaseConfigured) {
    return null
  }
  if (!client) {
    client = createClient<IntellectDatabase>(
      config.supabaseUrl,
      config.supabaseAnonKey,
      {
        realtime: { params: { eventsPerSecond: 10 } },
      },
    )
  }
  return client
}
