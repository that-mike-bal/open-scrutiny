import { createClient } from '@supabase/supabase-js'

// Credentials come only from the environment (see client/env.example).
// The service-role key must NEVER be referenced in frontend code — the browser
// bundle uses the anon key, and Row Level Security policies on the backend
// decide what that key can read/write.
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error(
    'Missing Supabase configuration: set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY ' +
    '(see client/env.example).'
  )
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    storageKey: 'app-auth',
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: true
  }
})

// Database types for TypeScript
export interface TldString {
  id: string
  tld_string: string
  use_case?: string
  workflow_id?: string
  workflow_type?: string
  overall_status?: string
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED'
  created_at: string
  updated_at: string
  completed_at?: string
  execution_time_minutes?: number
  has_evaluation: boolean
  has_application_draft: boolean
  use_case_count?: number
  confidence_score?: number
  risk_score?: number
  risk_classification?: string
  risk_level?: string
  risk_recommendation?: string
  confidence_level?: string
  gemini_report?: string
  generated_report?: {
    type?: string
    report_content?: string
    generated_at?: string
    model_used?: string
    status?: string
    content_length?: number
  }
}

export interface TaskExecution {
  id: string
  tld_string_id: string
  task_definition_id?: string  // Made optional since it can be null for dynamic tasks
  task_name: string  // Database-friendly name (e.g., 'iana_database_check')
  task_display_name?: string  // User-friendly name (e.g., 'IANA Database Verification')
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED'
  started_at?: string
  completed_at?: string
  execution_time_seconds?: number
  result_status?: 'PASS' | 'FAIL' | 'BLOCKED' | 'REVIEW_REQUIRED' | 'CLEAR' | 'LOW_RISK' | 'MEDIUM_RISK' | 'HIGH_RISK'
  result_data?: any
  confidence_score?: number
  agent_name?: string
  agent_version?: string
  tools_used?: string[]
  tool_call_count?: number
  crew_task_id?: string
  raw_output?: string
  user_friendly_summary?: string
  workflow_context?: any
  workflow_id?: string
  workflow_type?: string
  error_message?: string
  retry_count?: number
  created_at: string
  updated_at: string
  task_definition?: {
    id: string
    task_name: string
    task_category: string
    description: string
    is_binary_gate: boolean
    can_block_workflow: boolean
  }
}

export interface Database {
  public: {
    Tables: {
      tld_strings: {
        Row: TldString
        Insert: Omit<TldString, 'id' | 'created_at' | 'updated_at'>
        Update: Partial<Omit<TldString, 'id' | 'created_at'>>
      }
      task_executions: {
        Row: TaskExecution
        Insert: Omit<TaskExecution, 'id'>
        Update: Partial<Omit<TaskExecution, 'id'>>
      }
    }
  }
}
