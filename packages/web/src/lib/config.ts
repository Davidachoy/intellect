export const API_URL =
  import.meta.env.VITE_API_URL?.trim() || 'http://localhost:8000'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL?.trim() ?? ''
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY?.trim() ?? ''
const demoApiKey =
  import.meta.env.VITE_DEMO_API_KEY?.trim() || 'demo-key'

export const config = {
  apiUrl: API_URL,
  supabaseUrl,
  supabaseAnonKey,
  demoApiKey,
  supabaseConfigured: Boolean(supabaseUrl && supabaseAnonKey),
} as const
