import { supabase, type TldString } from './supabase'
import type { TldEvaluationWithAnalysis } from '../types'
import { getApiBase } from './api-config'

// Types for API responses
export interface CreateEvaluationRequest {
  tld_string: string
  use_case?: string
  workflow_type?: 'binary_compliance_check' | 'technical_risk_assessment' | 'legal_risk_assessment' | 'geopolitical_risk_assessment' | 'quick_evaluation' | 'icann_compliance'
}

// Legacy types for compatibility (used by WorkflowProgressTracker)
export interface WorkflowProgress {
  type: string
  crew_name?: string
  agent_role?: string
  task_description?: string
  tool_name?: string
  progress?: number
  error?: string
  timestamp?: string
  message?: string
}

export interface CreateEvaluationResponse {
  workflow_id: string
  evaluation_id: string
  tld_string: string
  status: string
  message: string
}

// Application Management Types
export interface TldApplication {
  id: string
  tld_string: string
  tld_string_id: string
  applicant_id: string
  applicant_name: string
  internal_reference: string
  application_type: ApplicationType
  status: 'Draft' | 'Generating' | 'In_Progress' | 'Ready_For_Review' | 'Completed' | 'Failed'
  completion_percentage: number
  created_at: string
  updated_at: string
  risk_level?: string
  business_score?: number
  secondary_string_id?: string
  secondary_tld_string?: string
}

export type ApplicationType = 'standard' | 'community' | 'brand' | 'geographic' | 'idn_variant'

export interface CreateApplicationRequest {
  tld_string_id: string
  applicant_id: string
  tld_string: string
  application_type?: ApplicationType
  secondary_string_id?: string
  secondary_tld_string?: string
}

export interface ApplicationGenerationResponse {
  application_id: string
  status: string
  message: string
}


// Direct Supabase API Functions
export async function getTldEvaluations(
  status?: string,
  limit: number = 50
): Promise<TldEvaluationWithAnalysis[]> {
  let query = supabase
    .from('tld_strings')
    .select(`
      *,
      task_executions:task_executions(
        id,
        task_definition_id,
        status,
        confidence_score,
        completed_at,
        task_definitions(task_name, task_category)
      )
    `)
    .order('updated_at', { ascending: false })
    .limit(limit)

  if (status) {
    query = query.eq('overall_status', status)
  }

  const { data, error } = await query

  if (error) {
    throw new Error(`Failed to fetch TLD evaluations: ${error.message}`)
  }

  return data || []
}

export async function getTldEvaluation(evaluation_id: string): Promise<TldEvaluationWithAnalysis | null> {
  const { data, error } = await supabase
    .from('tld_strings')
    .select('*')
    .eq('id', evaluation_id)
    .single()

  if (error) {
    throw new Error(`Failed to fetch evaluation: ${error.message}`)
  }

  // Fetch task executions separately
  const { data: taskData, error: taskError } = await supabase
    .from('task_executions')
    .select('*')
    .eq('tld_string_id', evaluation_id)
    .order('updated_at', { ascending: false })

  if (taskError) {
    console.warn('Failed to fetch task executions:', taskError.message)
    return { ...data, task_executions: [] }
  }

  return { ...data, task_executions: taskData || [] }
}

export async function getTldEvaluationsByString(tld_string: string): Promise<TldEvaluationWithAnalysis[]> {
  const { data, error } = await supabase
    .from('tld_strings')
    .select('*')
    .eq('tld_string', tld_string.toLowerCase())
    .order('updated_at', { ascending: false })

  if (error) {
    throw new Error(`Failed to fetch evaluations for TLD: ${error.message}`)
  }

  // If we get the tld_strings successfully, now let's fetch task_executions separately
  if (data && data.length > 0) {
    const tldStringIds = data.map(tld => tld.id)
    
    const { data: taskData, error: taskError } = await supabase
      .from('task_executions')
      .select('*')
      .in('tld_string_id', tldStringIds)
      .order('updated_at', { ascending: false })

    if (taskError) {
      console.warn('Failed to fetch task executions:', taskError.message)
      // Return TLD strings without task executions if there's an error
      return data.map(tld => ({ ...tld, task_executions: [] }))
    }

    // Attach task executions to their respective TLD strings and fix status
    return data.map(tld => {
      const taskExecutions = taskData.filter(task => task.tld_string_id === tld.id)
      
      // Calculate actual status based on task executions
      let actualStatus = tld.overall_status || 'PENDING'
      
      if (taskExecutions.length > 0) {
        const allCompleted = taskExecutions.every(task => task.status === 'COMPLETED')
        const hasRunning = taskExecutions.some(task => task.status === 'RUNNING')
        const hasFailed = taskExecutions.some(task => task.status === 'FAILED')
        
        if (allCompleted) {
          actualStatus = 'COMPLETED'
        } else if (hasRunning) {
          actualStatus = 'RUNNING'
        } else if (hasFailed) {
          actualStatus = 'FAILED'
        }
      } else if (actualStatus === 'RUNNING') {
        // Keep as RUNNING - workflows might be starting up or in progress
        actualStatus = 'RUNNING'
      }
      
      return {
        ...tld,
        task_executions: taskExecutions,
        status: actualStatus,
        overall_status: actualStatus
      }
    })
  }

  return data || []
}

export async function searchTldEvaluations(
  query: string,
  limit: number = 20
): Promise<TldEvaluationWithAnalysis[]> {
  const { data, error } = await supabase
    .from('tld_strings')
    .select('*')
    .or(`tld_string.ilike.%${query}%,use_case.ilike.%${query}%`)
    .order('updated_at', { ascending: false })
    .limit(limit)

  if (error) {
    throw new Error(`Failed to search TLD evaluations: ${error.message}`)
  }

  // Fetch task executions separately for search results too
  if (data && data.length > 0) {
    const tldStringIds = data.map(tld => tld.id)
    
    const { data: taskData, error: taskError } = await supabase
      .from('task_executions')
      .select('*')
      .in('tld_string_id', tldStringIds)
      .order('updated_at', { ascending: false })

    if (taskError) {
      console.warn('Failed to fetch task executions for search:', taskError.message)
      return data.map(tld => ({ ...tld, task_executions: [] }))
    }

    return data.map(tld => ({
      ...tld,
      task_executions: taskData.filter(task => task.tld_string_id === tld.id)
    }))
  }

  return data || []
}

export async function checkRunningEvaluationStatus(tld_string: string): Promise<{
  tld_string: string
  has_running_evaluation: boolean
  running_evaluations: TldString[]
  count: number
}> {
  const { data, error } = await supabase
    .from('tld_strings')
    .select('*')
    .eq('tld_string', tld_string.toLowerCase())
    .eq('overall_status', 'RUNNING')

  if (error) {
    throw new Error(`Failed to check running evaluations: ${error.message}`)
  }

  return {
    tld_string,
    has_running_evaluation: (data?.length || 0) > 0,
    running_evaluations: data || [],
    count: data?.length || 0
  }
}

// Create and run evaluation using Supabase Edge Function or direct API
export async function createAndRunEvaluation(data: CreateEvaluationRequest): Promise<CreateEvaluationResponse> {
  // Check for duplicates first
  const { data: existing } = await supabase
    .from('tld_strings')
    .select('id, overall_status')
    .eq('tld_string', data.tld_string.toLowerCase())
    .single()

  if (existing) {
    throw new Error(`TLD string ".${data.tld_string}" already exists`)
  }

  // For local development, call CrewAI service directly
  const isDev = import.meta.env.VITE_DEV_MODE === 'true'
  const crewaiEndpoint = getApiBase()

  if (isDev) {
    // Create evaluation record in database first
    const evaluationRecord = {
      tld_string: data.tld_string.toLowerCase(),
      use_case: data.use_case || '',
      workflow_type: data.workflow_type || 'binary_compliance_check',
      overall_status: 'PENDING' as const,
    }

    const { data: created, error: insertError } = await supabase
      .from('tld_strings')
      .insert(evaluationRecord)
      .select()
      .single()

    if (insertError) {
      console.error('Database insert error:', insertError)
      throw new Error('Failed to create evaluation record')
    }

    // Update status to RUNNING
    await supabase
      .from('tld_strings')
      .update({ overall_status: 'RUNNING' })
      .eq('id', created.id)

    // Call CrewAI service directly in the background
    fetch(`${crewaiEndpoint}/evaluations/run`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        tld_string: created.tld_string,
        use_case: created.use_case,
        workflow_type: created.workflow_type
      })
    }).catch(error => {
      console.error('CrewAI workflow error:', error)
      // Update status to FAILED in background
      supabase
        .from('tld_strings')
        .update({
          overall_status: 'FAILED'
        })
        .eq('id', created.id)
    })

    return {
      workflow_id: created.workflow_id,
      evaluation_id: created.id,
      tld_string: created.tld_string,
      status: 'RUNNING',
      message: 'Evaluation started successfully'
    }
  } else {
    // Production: Use Edge Function
    const { data: result, error } = await supabase.functions.invoke('trigger-evaluation', {
      body: {
        tld_string: data.tld_string,
        use_case: data.use_case || '',
        workflow_type: data.workflow_type || 'binary_compliance_check'
      }
    })

    if (error) {
      throw new Error(error.message || 'Failed to create evaluation')
    }

    return result
  }
}

export async function createEvaluationRecord(data: CreateEvaluationRequest): Promise<TldString> {
  const evaluationRecord = {
    tld_string: data.tld_string.toLowerCase(),
    use_case: data.use_case || '',
    workflow_type: data.workflow_type || 'binary_compliance_check',
    overall_status: 'PENDING' as const,
  }

  const { data: created, error } = await supabase
    .from('tld_strings')
    .insert(evaluationRecord)
    .select()
    .single()

  if (error) {
    throw new Error(`Failed to create evaluation record: ${error.message}`)
  }

  return created
}

// Legacy function for compatibility (WorkflowProgressTracker)
export function createProgressStream(): EventSource {
  // For compatibility with existing WorkflowProgressTracker component
  // Create a mock EventSource that provides basic functionality
  const mockEventSource = new EventSource(`data:text/plain,`);
  
  // Close immediately since we're not using SSE in the Supabase architecture
  setTimeout(() => {
    mockEventSource.close();
  }, 100);
  
  return mockEventSource;
}

// Real-time subscriptions for live updates
export function subscribeToEvaluationUpdates(
  evaluation_id: string,
  callback: (payload: any) => void
) {
  return supabase
    .channel(`evaluation-${evaluation_id}`)
    .on(
      'postgres_changes',
      {
        event: '*',
        schema: 'public',
        table: 'tld_strings',
        filter: `id=eq.${evaluation_id}`
      },
      callback
    )
    .subscribe()
}

export function subscribeToTldStringUpdates(
  tld_string_id: string,
  callback: (payload: any) => void
) {
  return supabase
    .channel(`tld-string-${tld_string_id}`)
    .on(
      'postgres_changes',
      {
        event: '*',
        schema: 'public',
        table: 'tld_strings',
        filter: `id=eq.${tld_string_id}`
      },
      callback
    )
    .subscribe()
}

export function subscribeToTaskExecutionUpdates(
  tld_string_id: string,
  callback: (payload: any) => void
) {
  return supabase
    .channel(`task-executions-${tld_string_id}`)
    .on(
      'postgres_changes',
      {
        event: '*',
        schema: 'public',
        table: 'task_executions',
        filter: `tld_string_id=eq.${tld_string_id}`
      },
      callback
    )
    .subscribe()
}

// Retry a failed evaluation
export async function retryTldEvaluation(evaluationId: string): Promise<void> {
  try {
    console.log(`🔄 Retrying TLD evaluation: ${evaluationId}`)
    
    // Get the evaluation details
    const { data: evaluation, error: fetchError } = await supabase
      .from('tld_strings')
      .select('*')
      .eq('id', evaluationId)
      .single()
    
    if (fetchError || !evaluation) {
      throw new Error(`Failed to fetch evaluation: ${fetchError?.message || 'Not found'}`)
    }
    
    // Clear existing task executions to start fresh
    const { error: deleteTasksError } = await supabase
      .from('task_executions')
      .delete()
      .eq('tld_string_id', evaluationId)
    
    if (deleteTasksError) {
      console.warn('Warning: Could not clear existing tasks:', deleteTasksError)
    }
    
    // Reset the evaluation status to PENDING
    const { error: updateError } = await supabase
      .from('tld_strings')
      .update({
        overall_status: 'PENDING',
        completed_at: null
      })
      .eq('id', evaluationId)
    
    if (updateError) {
      throw new Error(`Failed to reset evaluation status: ${updateError.message}`)
    }
    
    // Submit to CrewAI service for retry
    const crewaiEndpoint = getApiBase()
    
    const response = await fetch(`${crewaiEndpoint}/api/evaluations/auto-submit`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        tld_string: evaluation.tld_string,
        use_case: evaluation.use_case || 'Retry evaluation',
        enable_auto_execution: true
      })
    })
    
    if (!response.ok) {
      const errorText = await response.text()
      throw new Error(`CrewAI service error: ${errorText}`)
    }
    
    console.log(`✅ Successfully restarted evaluation: ${evaluationId}`)
    
  } catch (error: unknown) {
    console.error(`❌ Error retrying evaluation ${evaluationId}:`, error)
    throw error
  }
}

// Delete evaluation and all associated data
export async function deleteTldEvaluation(evaluationId: string): Promise<void> {
  try {
    console.log(`🗑️ Deleting TLD evaluation: ${evaluationId}`)
    
    // Delete the main TLD string record
    // All related records will be deleted automatically due to foreign key constraints
    const { error: deleteError } = await supabase
      .from('tld_strings')
      .delete()
      .eq('id', evaluationId)
    
    if (deleteError) {
      console.error('❌ Failed to delete TLD string record:', deleteError)
      throw new Error(`Failed to delete evaluation: ${deleteError.message}`)
    }
    
    console.log(`✅ Successfully deleted TLD evaluation: ${evaluationId}`)
  } catch (error: unknown) {
    console.error(`❌ Error deleting evaluation ${evaluationId}:`, error)
    throw error
  }
}

// =====================================================
// FILE UPLOAD API FUNCTIONS
// =====================================================

export interface FileUploadResult {
  id: string
  original_filename: string
  stored_filename: string
  file_path: string
  file_size_bytes: number
  validation_status: 'pending' | 'valid' | 'invalid' | 'needs_review'
  validation_errors: string[]
}

// Upload files for a specific application question
export async function uploadApplicationFiles(
  applicationId: string,
  questionId: string,
  files: File[],
  documentType?: string
): Promise<FileUploadResult[]> {
  const crewaiEndpoint = getApiBase()
  
  const formData = new FormData()
  formData.append('application_id', applicationId)
  formData.append('question_id', questionId)
  if (documentType) {
    formData.append('document_type', documentType)
  }
  
  files.forEach((file) => {
    formData.append(`files`, file)
  })
  
  const response = await fetch(`${crewaiEndpoint}/api/applications/${applicationId}/files/upload`, {
    method: 'POST',
    body: formData
  })
  
  if (!response.ok) {
    throw new Error(`Failed to upload files: ${response.statusText}`)
  }
  
  const data = await response.json()
  
  if (!data.success) {
    throw new Error(data.error || 'Failed to upload files')
  }
  
  return data.files
}

// Delete an uploaded file
export async function deleteApplicationFile(fileId: string): Promise<void> {
  const crewaiEndpoint = getApiBase()
  
  const response = await fetch(`${crewaiEndpoint}/api/files/${fileId}`, {
    method: 'DELETE'
  })
  
  if (!response.ok) {
    throw new Error(`Failed to delete file: ${response.statusText}`)
  }
  
  const data = await response.json()
  
  if (!data.success) {
    throw new Error(data.error || 'Failed to delete file')
  }
}

// Get uploaded files for an application
export async function getApplicationFiles(applicationId: string): Promise<FileUploadResult[]> {
  const crewaiEndpoint = getApiBase()
  
  const response = await fetch(`${crewaiEndpoint}/api/applications/${applicationId}/files`)
  
  if (!response.ok) {
    throw new Error(`Failed to fetch files: ${response.statusText}`)
  }
  
  const data = await response.json()
  
  if (!data.success) {
    throw new Error(data.error || 'Failed to fetch files')
  }
  
  return data.files
}


// =====================================================
// APPLICANT MANAGEMENT API FUNCTIONS
// =====================================================

// Types for Applicant Management
export interface KeyPersonnel {
  name: string
  title: string
  role: string
  email?: string
  phone?: string
  background?: string
  contact_type: string
}

export interface ApplicantData {
  id?: string
  legal_name: string
  business_name?: string
  dba_name?: string
  entity_type: string
  jurisdiction: string
  incorporation_date?: string
  business_address: string
  mailing_address?: string
  phone?: string
  email: string
  website?: string
  tax_id?: string
  tax_id_issuing_authority?: string
  lei?: string
  is_existing_registry_operator?: boolean
  registry_relationship_explanation?: string
  is_rsp_or_provider?: boolean
  rsp_affiliate_explanation?: string
  stock_symbol?: string
  stock_exchange?: string
  address_line1?: string
  address_line2?: string
  city?: string
  state_province?: string
  postal_code?: string
  country_code?: string
  parent_company_name?: string
  parent_company_dba?: string
  parent_company_entity_type?: string
  parent_company_jurisdiction?: string
  parent_company_address?: Record<string, string>
  ultimate_parent_name?: string
  ultimate_parent_dba?: string
  ultimate_parent_entity_type?: string
  ultimate_parent_jurisdiction?: string
  ultimate_parent_address?: Record<string, string>
  has_unique_legal_issues?: boolean
  legal_issues_explanation?: string
  annual_revenue?: number
  total_assets?: number
  funding_sources?: string
  financial_statement_url?: string
  key_personnel?: KeyPersonnel[]
  registry_experience_description?: string
  current_tlds?: string[]
  affiliated_organizations?: string[]
  created_at?: string
  updated_at?: string
}

export interface ApplicantResponse {
  success: boolean
  applicant?: ApplicantData
  applicant_id?: string
  message: string
  error?: string
}

export interface ApplicantListResponse {
  success: boolean
  applicants: ApplicantData[]
  count: number
  message: string
}

// Get the default Example Registry applicant
export async function getDefaultApplicant(): Promise<ApplicantData> {
  const crewaiEndpoint = getApiBase()
  
  const response = await fetch(`${crewaiEndpoint}/api/applicants/default`)
  
  if (!response.ok) {
    throw new Error(`Failed to fetch default applicant: ${response.statusText}`)
  }
  
  const data: ApplicantResponse = await response.json()
  
  if (!data.success || !data.applicant) {
    throw new Error(data.error || 'Failed to fetch default applicant')
  }
  
  return data.applicant
}

// Get all applicants
export async function getAllApplicants(): Promise<ApplicantData[]> {
  const crewaiEndpoint = getApiBase()
  
  const response = await fetch(`${crewaiEndpoint}/api/applicants`)
  
  if (!response.ok) {
    throw new Error(`Failed to fetch applicants: ${response.statusText}`)
  }
  
  const data: ApplicantListResponse = await response.json()
  
  if (!data.success) {
    throw new Error(data.message || 'Failed to fetch applicants')
  }
  
  return data.applicants
}

// Get specific applicant by ID
export async function getApplicantById(applicantId: string): Promise<ApplicantData> {
  const crewaiEndpoint = getApiBase()
  
  const response = await fetch(`${crewaiEndpoint}/api/applicants/${applicantId}`)
  
  if (!response.ok) {
    throw new Error(`Failed to fetch applicant: ${response.statusText}`)
  }
  
  const data: ApplicantResponse = await response.json()
  
  if (!data.success || !data.applicant) {
    throw new Error(data.error || 'Failed to fetch applicant')
  }
  
  return data.applicant
}

// Create new applicant
export async function createApplicant(applicantData: Omit<ApplicantData, 'id' | 'created_at' | 'updated_at'>): Promise<string> {
  const crewaiEndpoint = getApiBase()
  
  const response = await fetch(`${crewaiEndpoint}/api/applicants`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(applicantData)
  })
  
  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(`Failed to create applicant: ${errorText}`)
  }
  
  const data: ApplicantResponse = await response.json()
  
  if (!data.success || !data.applicant_id) {
    throw new Error(data.error || 'Failed to create applicant')
  }
  
  return data.applicant_id
}

// Update existing applicant
export async function updateApplicant(
  applicantId: string, 
  updates: Partial<Omit<ApplicantData, 'id' | 'created_at' | 'updated_at'>>
): Promise<ApplicantData> {
  const crewaiEndpoint = getApiBase()
  
  const response = await fetch(`${crewaiEndpoint}/api/applicants/${applicantId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(updates)
  })
  
  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(`Failed to update applicant: ${errorText}`)
  }
  
  const data: ApplicantResponse = await response.json()
  
  if (!data.success || !data.applicant) {
    throw new Error(data.error || 'Failed to update applicant')
  }
  
  return data.applicant
}

// Partially update existing applicant
export async function patchApplicant(
  applicantId: string, 
  updates: Partial<Omit<ApplicantData, 'id' | 'created_at' | 'updated_at'>>
): Promise<ApplicantData> {
  const crewaiEndpoint = getApiBase()
  
  const response = await fetch(`${crewaiEndpoint}/api/applicants/${applicantId}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(updates)
  })
  
  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(`Failed to update applicant: ${errorText}`)
  }
  
  const data: ApplicantResponse = await response.json()
  
  if (!data.success || !data.applicant) {
    throw new Error(data.error || 'Failed to update applicant')
  }
  
  return data.applicant
}

// Delete applicant
export async function deleteApplicant(applicantId: string): Promise<void> {
  const crewaiEndpoint = getApiBase()
  
  const response = await fetch(`${crewaiEndpoint}/api/applicants/${applicantId}`, {
    method: 'DELETE'
  })
  
  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(`Failed to delete applicant: ${errorText}`)
  }
  
  const data: ApplicantResponse = await response.json()
  
  if (!data.success) {
    throw new Error(data.error || 'Failed to delete applicant')
  }
}

// =====================================================
// APPLICATION MANAGEMENT API FUNCTIONS
// =====================================================

// Map database status to frontend status
export function mapApplicationStatus(dbStatus: string): 'Draft' | 'Generating' | 'Completed' | 'Failed' {
  switch (dbStatus) {
    case 'Draft': return 'Draft'
    case 'In_Progress': return 'Generating'
    case 'Ready_For_Review': return 'Completed'
    case 'Submitted': return 'Completed'
    case 'Under_Evaluation': return 'Completed'
    default: return 'Draft'
  }
}

// Get all applications
export async function getTldApplications(): Promise<TldApplication[]> {
  try {
    const response = await fetch('/api/applications')
    if (!response.ok) {
      throw new Error(`Failed to fetch applications: ${response.statusText}`)
    }
    const result = await response.json()
    if (!result.success) {
      throw new Error(result.error || 'Failed to fetch applications')
    }
    
    return result.applications.map((app: any) => ({
      ...app,
      status: mapApplicationStatus(app.status),
      applicant_name: app.applicants?.legal_name || app.applicants?.business_name || 'Example Registry LLC',
      risk_level: undefined,
      business_score: undefined
    }))
  } catch (error) {
    console.error('Error fetching applications:', error)
    // Fallback to direct Supabase query if API fails
    const { data, error: supabaseError } = await supabase
      .from('tld_applications')
      .select(`*`)
      .order('updated_at', { ascending: false })
    if (supabaseError) {
      throw new Error(`Failed to fetch applications: ${supabaseError.message}`)
    }
    return data?.map(app => ({
      ...app,
      status: mapApplicationStatus(app.status),
      applicant_name: app.applicant_name || 'Unknown Applicant',
      risk_level: undefined,
      business_score: undefined
    })) || []
  }
}

// Create new applications for multiple TLD strings using new CrewAI endpoints
export async function createApplications(requests: CreateApplicationRequest[]): Promise<ApplicationGenerationResponse[]> {
  const crewaiEndpoint = getApiBase()
  
  const results: ApplicationGenerationResponse[] = []
  
  for (const request of requests) {
    try {
      console.log('🚀 Creating application via CrewAI API for:', request.tld_string)

      // Call the new generate-full endpoint that creates the app and generates answers
      const response = await fetch(`${crewaiEndpoint}/api/applications/generate-full`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          tld_string: request.tld_string,
          tld_string_id: request.tld_string_id,
          applicant_id: request.applicant_id,
          application_type: request.application_type || 'standard',
          secondary_string_id: request.secondary_string_id || undefined,
          secondary_tld_string: request.secondary_tld_string || undefined,
          generate_answers: true,
          store_in_database: true
        })
      })

      if (!response.ok) {
        const errorText = await response.text()
        console.error('CrewAI API Error:', errorText)
        throw new Error(`CrewAI service error (${response.status}): ${errorText}`)
      }

      const applicationResult = await response.json()
      console.log('✅ Application creation result:', applicationResult)
      
      results.push({
        application_id: applicationResult.application_id,
        status: applicationResult.status,
        message: applicationResult.message
      })

    } catch (error) {
      console.error(`❌ Failed to create application for ${request.tld_string}:`, error)
      results.push({
        application_id: '',
        status: 'Failed',
        message: `Failed to start application for .${request.tld_string}: ${error instanceof Error ? error.message : String(error)}`
      })
    }
  }

  return results
}

// Get available strings for new applications (completed evaluations not yet used)
export async function getAvailableStringsForApplications(): Promise<TldString[]> {
  const { data, error } = await supabase
    .from('tld_strings')
    .select(`
      *,
      tld_applications!left(id)
    `)
    .in('status', ['COMPLETED', 'Evaluated'])
    .is('tld_applications.id', null) // Only strings without existing applications

  if (error) {
    throw new Error(`Failed to fetch available strings: ${error.message}`)
  }

  return data || []
}

// Subscribe to application updates
export function subscribeToApplicationUpdates(
  application_id: string,
  callback: (payload: any) => void
) {
  return supabase
    .channel(`application-${application_id}`)
    .on(
      'postgres_changes',
      {
        event: '*',
        schema: 'public',
        table: 'tld_applications',
        filter: `id=eq.${application_id}`
      },
      callback
    )
    .subscribe()
}

// Subscribe to all application changes
export function subscribeToAllApplicationUpdates(callback: (payload: any) => void) {
  return supabase
    .channel('all-applications')
    .on(
      'postgres_changes',
      {
        event: '*',
        schema: 'public',
        table: 'tld_applications'
      },
      callback
    )
    .subscribe()
}

// =====================================================
// APPLICATION DETAIL API FUNCTIONS
// =====================================================

// Types for Application Questions and Answers
export type QuestionCategory = 'entity_field' | 'selection_field' | 'substantive_field' | 'file_upload'

export interface ApplicationQuestion {
  id: string
  question_number: string
  question_set?: string  // ICANN Question Set grouping (e.g., "1. Applicant Entity Information")
  section: string
  subsection?: string
  question_text: string
  input_type?: 'text' | 'textarea' | 'select' | 'checkbox' | 'file_upload'
  field_type?: string
  question_category?: QuestionCategory
  applicant_field_mapping?: string
  required: boolean
  options?: string[]
  character_limit?: number
  notes_instructions?: string
  input_field_requirements?: string
  public_posting?: boolean
  file_types?: string[]
  max_files?: number
  relevant_task_names?: string[]
  generation_hint?: string
  created_at?: string
  updated_at?: string
}

export interface ApplicationAnswer {
  id: string
  application_id: string
  question_id: string
  answer_text?: string
  answer_files?: string[]
  status: 'draft' | 'completed' | 'needs_review' | 'ai_generated'
  ai_generated?: boolean
  data_source?: string        // applicant_database, ai_generated, insufficient_data, etc.
  confidence_score?: number
  last_modified?: string
  created_at?: string
  updated_at?: string
  question?: ApplicationQuestion
}

// Get a single TLD application by ID
export async function getTldApplication(applicationId: string): Promise<TldApplication | null> {
  try {
    const response = await fetch(`/api/applications/${applicationId}`)
    if (!response.ok) {
      if (response.status === 404) return null
      throw new Error(`Failed to fetch application: ${response.statusText}`)
    }
    const result = await response.json()
    if (!result.success) return null

    const app = result.application
    return {
      ...app,
      status: mapApplicationStatus(app.status),
      applicant_name: app.applicants?.legal_name || app.applicants?.business_name || 'Unknown',
      risk_level: undefined,
      business_score: undefined
    }
  } catch (error) {
    console.error('Error fetching application:', error)
    return null
  }
}

// Mapping of question numbers to applicant data fields
const APPLICANT_QUESTION_MAPPING: Record<string, keyof ApplicantData> = {
  '1': 'legal_name',
  '2': 'dba_name',
  '3': 'entity_type',
  '4': 'jurisdiction',
  '5': 'tax_id',
  '6': 'tax_id_issuing_authority',
  '7': 'lei',
  '10': 'website',
  '12': 'registry_relationship_explanation',
  '14': 'rsp_affiliate_explanation',
  '15': 'stock_symbol',
  '16': 'stock_exchange',
  '17': 'phone',
  '18': 'phone',
  '19': 'email',
  '20': 'address_line1',
  '21': 'address_line2',
  '22': 'city',
  '23': 'state_province',
  '24': 'postal_code',
  '25': 'country_code',
  '26': 'parent_company_name',
  '27': 'parent_company_dba',
  '28': 'parent_company_entity_type',
  '29': 'parent_company_jurisdiction',
  '36': 'ultimate_parent_name',
  '37': 'ultimate_parent_dba',
  '38': 'ultimate_parent_entity_type',
  '39': 'ultimate_parent_jurisdiction',
}

// Mapping of question numbers to JSONB address sub-fields
const JSONB_ADDRESS_MAPPINGS: Record<string, { field: keyof ApplicantData; subfield: string }> = {
  '30': { field: 'parent_company_address', subfield: 'line1' },
  '31': { field: 'parent_company_address', subfield: 'line2' },
  '32': { field: 'parent_company_address', subfield: 'city' },
  '33': { field: 'parent_company_address', subfield: 'state' },
  '34': { field: 'parent_company_address', subfield: 'postal_code' },
  '35': { field: 'parent_company_address', subfield: 'country' },
  '40': { field: 'ultimate_parent_address', subfield: 'line1' },
  '41': { field: 'ultimate_parent_address', subfield: 'line2' },
  '42': { field: 'ultimate_parent_address', subfield: 'city' },
  '43': { field: 'ultimate_parent_address', subfield: 'state' },
  '44': { field: 'ultimate_parent_address', subfield: 'postal_code' },
  '45': { field: 'ultimate_parent_address', subfield: 'country' },
}

// Question numbers that should be auto-populated from the TLD string
const STRING_QUESTION_NUMBERS = ['116']  // "Provide the applied-for gTLD string"

// Mapping of string-related question numbers to application context fields
const STRING_FIELD_MAPPINGS: Record<string, string> = {
  '118': 'string_meaning',     // "Meaning/definition of the applied-for string"
}

// Get application questions and answers for a specific application
export async function getApplicationQuestionsAndAnswers(applicationId: string): Promise<{questions: ApplicationQuestion[], answers: ApplicationAnswer[], applicant?: ApplicantData}> {
  try {
    const response = await fetch(`/api/applications/${applicationId}/questions`)
    if (!response.ok) {
      throw new Error(`Failed to fetch Q&A: ${response.statusText}`)
    }
    const result = await response.json()
    if (!result.success) {
      throw new Error(result.error || 'Failed to fetch Q&A')
    }

    // Extract applicant data if available
    const applicant: ApplicantData | undefined = result.applicant

    // Handle new API response format with separate questions and answers
    if (result.questions && result.answers) {
      // Database format - questions and answers are separate
      const questions: ApplicationQuestion[] = result.questions.map((q: any) => ({
        id: q.id,
        question_number: q.question_number,
        question_set: q.question_set,  // ICANN Question Set grouping
        section: q.section,
        subsection: q.subsection,
        question_text: q.question_text,
        field_type: q.field_type || 'textarea',
        input_type: q.input_type,
        question_category: q.question_category,
        applicant_field_mapping: q.applicant_field_mapping,
        character_limit: q.character_limit,
        input_field_requirements: q.input_field_requirements,
        required: q.required,
        public_posting: q.public_posting,
        notes_instructions: q.notes_instructions,
        relevant_task_names: q.relevant_task_names,
        generation_hint: q.generation_hint,
      }))

      // Start with existing answers from the database
      const answersMap = new Map<string, ApplicationAnswer>()
      result.answers.forEach((a: any) => {
        answersMap.set(a.question_id, {
          id: a.id,
          application_id: a.application_id,
          question_id: a.question_id,
          answer_text: a.answer_text || '',
          answer_files: a.answer_files || [],
          status: a.status || 'draft',
          ai_generated: a.ai_generated || false,
          data_source: a.data_source || a.source_data_summary || undefined,
          confidence_score: a.confidence_score,
          last_modified: a.last_modified || new Date().toISOString()
        })
      })

      // Pre-populate applicant-related questions if we have applicant data
      if (applicant) {
        questions.forEach(q => {
          const existingAnswer = answersMap.get(q.id)
          // Only pre-populate if no answer exists yet
          if (existingAnswer && existingAnswer.answer_text) return

          let value: string | undefined

          // Check direct field mapping first
          const fieldName = APPLICANT_QUESTION_MAPPING[q.question_number]
          if (fieldName && applicant[fieldName]) {
            const raw = applicant[fieldName]
            value = Array.isArray(raw) ? raw.join(', ') : String(raw || '')
          }

          // Check JSONB address mappings (parent_company_address, ultimate_parent_address)
          if (!value) {
            const jsonbMapping = JSONB_ADDRESS_MAPPINGS[q.question_number]
            if (jsonbMapping) {
              const addressObj = applicant[jsonbMapping.field] as Record<string, string> | undefined
              if (addressObj && typeof addressObj === 'object') {
                value = addressObj[jsonbMapping.subfield] || undefined
              }
            }
          }

          if (value) {
            answersMap.set(q.id, {
              id: existingAnswer?.id || `auto-${q.id}`,
              application_id: applicationId,
              question_id: q.id,
              answer_text: value,
              answer_files: [],
              status: 'draft',
              ai_generated: false,
              last_modified: new Date().toISOString()
            })
          }
        })
      }

      // Pre-populate TLD string questions (e.g., question 116)
      const tldString = result.tld_string
      if (tldString) {
        questions.forEach(q => {
          if (STRING_QUESTION_NUMBERS.includes(q.question_number)) {
            const existingAnswer = answersMap.get(q.id)
            if (!existingAnswer || !existingAnswer.answer_text || existingAnswer.answer_text.toLowerCase() === 'n/a') {
              answersMap.set(q.id, {
                id: existingAnswer?.id || `auto-string-${q.id}`,
                application_id: applicationId,
                question_id: q.id,
                answer_text: `.${tldString.toUpperCase()}`,
                answer_files: [],
                status: 'draft',
                ai_generated: false,
                last_modified: new Date().toISOString()
              })
            }
          }
        })
      }

      // Pre-populate string context fields (string_meaning, string_rationale, intended_use)
      questions.forEach(q => {
        const contextField = STRING_FIELD_MAPPINGS[q.question_number]
        if (contextField && result[contextField]) {
          const existingAnswer = answersMap.get(q.id)
          if (!existingAnswer || !existingAnswer.answer_text) {
            answersMap.set(q.id, {
              id: existingAnswer?.id || `auto-ctx-${q.id}`,
              application_id: applicationId,
              question_id: q.id,
              answer_text: String(result[contextField]),
              answer_files: [],
              status: 'draft',
              ai_generated: false,
              last_modified: new Date().toISOString()
            })
          }
        }
      })

      const answers = Array.from(answersMap.values())
      return { questions, answers, applicant }
    }
    else {
      // Legacy file format - questions have embedded answers
      const questions: ApplicationQuestion[] = result.questions.map((qa: any, index: number) => ({
        id: qa.id || `q-${index}`,
        question_number: qa.question_number || index + 1,
        section: qa.section || 'Unknown',
        subsection: qa.subsection || '',
        question_text: qa.question_text || '',
        field_type: 'textarea',
        character_limit: 5000,
        required: qa.required || true,
        notes_instructions: `Data source: ${qa.data_source || 'Generated'}`,
        public_posting: qa.public_posting || false
      }))

      const answers: ApplicationAnswer[] = result.questions.map((qa: any, index: number) => ({
        id: `answer-${qa.id || index}`,
        application_id: result.application_id,
        question_id: qa.id || `q-${index}`,
        answer_text: qa.answer || '',
        status: qa.validation_status || 'draft',
        ai_generated: qa.data_source === 'Generated',
        last_modified: new Date().toISOString()
      }))

      return { questions, answers, applicant: undefined }
    }
  } catch (error) {
    console.error('Error fetching application Q&A:', error)
    // Fallback to placeholder questions if API fails
    return getApplicationQuestions().then(questions => ({ questions, answers: [], applicant: undefined }))
  }
}

// Get all application questions (fallback/placeholder)
export async function getApplicationQuestions(): Promise<ApplicationQuestion[]> {
  const { data, error } = await supabase
    .from('application_questions_enhanced')
    .select('*')
    .order('question_number')

  if (error) {
    // If table doesn't exist, return placeholder ICANN questions
    if (error.code === 'PGRST204' || error.message.includes('does not exist')) {
      console.warn('application_questions table does not exist, returning sample ICANN questions')
      return [
        {
          id: 'sample-1',
          question_number: '1',
          section: 'Organization Information',
          subsection: 'Applicant Information',
          question_text: 'Provide the full legal name of the Applicant.',
          input_type: 'text',
          character_limit: 500,
          required: true,
          notes_instructions: 'Enter the complete legal name as it appears in official documents.',
          public_posting: false
        },
        {
          id: 'sample-2', 
          question_number: '2',
          section: 'Organization Information',
          subsection: 'Applicant Information',
          question_text: 'Provide the principal business address of the Applicant.',
          input_type: 'textarea',
          character_limit: 1000,
          required: true,
          notes_instructions: 'Include complete street address, city, state/province, postal code, and country.',
          public_posting: true
        },
        {
          id: 'sample-3',
          question_number: '18',
          section: 'Technical Services',
          subsection: 'Registry Services',
          question_text: 'Describe your technical plan for registry services including DNS resolution, database management, and zone file generation.',
          input_type: 'textarea',
          character_limit: 5000,
          required: true,
          notes_instructions: 'Provide detailed technical specifications and infrastructure plans.',
          public_posting: true
        },
        {
          id: 'sample-4',
          question_number: '20',
          section: 'Financial Information',
          subsection: 'Funding',
          question_text: 'Provide evidence of access to, or commitment for, the financial resources needed to operate a registry.',
          input_type: 'file_upload',
          required: true,
          notes_instructions: 'Upload financial statements, letters of credit, or other supporting documentation.',
          public_posting: false
        }
      ]
    }
    throw new Error(`Failed to fetch application questions: ${error.message}`)
  }

  return data || []
}

// Get application answers for a specific application
export async function getApplicationAnswers(applicationId: string): Promise<ApplicationAnswer[]> {
  const { data, error } = await supabase
    .from('application_answers')
    .select(`
      *,
      application_questions_enhanced(*)
    `)
    .eq('application_id', applicationId)
    .order('updated_at')

  if (error) {
    // If table doesn't exist, return empty array for now
    if (error.code === 'PGRST204' || error.message.includes('does not exist') || error.message.includes('in the schema cache')) {
      console.warn('application_answers table does not exist or not in schema cache, returning empty array')
      return []
    }
    throw new Error(`Failed to fetch application answers: ${error.message}`)
  }

  return data?.map(answer => ({
    ...answer,
    question: answer.application_questions_enhanced
  })) || []
}

// Upsert (insert or update) an application answer
export async function upsertApplicationAnswer(answerData: {
  question_id: string
  application_id: string
  answer_text?: string
  answer_files?: string[]
  status: 'draft' | 'completed' | 'needs_review' | 'ai_generated'
  ai_generated?: boolean
}): Promise<ApplicationAnswer> {
  const upsertData = {
    ...answerData,
    last_modified: new Date().toISOString()
  }

  const { data, error } = await supabase
    .from('application_answers')
    .upsert(upsertData, {
      onConflict: 'application_id,question_id'
    })
    .select(`
      *,
      application_questions_enhanced(*)
    `)
    .single()

  if (error) {
    throw new Error(`Failed to save application answer: ${error.message}`)
  }

  return {
    ...data,
    question: data.application_questions_enhanced
  }
}

// Manually trigger RAG-based answer generation for all questions in an application
export async function generateApplicationAnswers(applicationId: string): Promise<{
  success: boolean
  message: string
  answers_generated?: number
  completion_percentage?: number
}> {
  // Validate input parameter
  if (!applicationId || typeof applicationId !== 'string' || applicationId === '[object Window]') {
    console.error('❌ Invalid applicationId provided to generateApplicationAnswers:', applicationId)
    return {
      success: false,
      message: 'Invalid application ID provided'
    }
  }

  const crewaiEndpoint = getApiBase()
  
  try {
    console.log(`🤖 Triggering RAG-based answer generation for application: ${applicationId}`)
    
    // Use the generate-multiple endpoint which calls ApplicationGenerationService
    const response = await fetch(`${crewaiEndpoint}/api/applications/generate-multiple`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        application_id: applicationId,
        question_ids: null,  // null means generate for ALL questions
        store_in_database: true
      })
    })

    if (!response.ok) {
      const errorText = await response.text()
      throw new Error(`RAG generation service error (${response.status}): ${errorText}`)
    }

    const result = await response.json()
    console.log('✅ Application answers generation result:', result)
    
    return {
      success: result.success,
      message: result.message || 'Application answers generated successfully',
      answers_generated: result.answers_generated?.length || 0,
      completion_percentage: result.completion_percentage
    }
  } catch (error) {
    console.error('❌ Error generating application answers:', error)
    return {
      success: false,
      message: error instanceof Error ? error.message : 'Failed to generate application answers'
    }
  }
}

// Trigger a full application generation workflow (including answers)
export async function triggerFullApplicationGeneration(
  tldString: string,
  applicantId: string
): Promise<{
  success: boolean
  message: string
  application_id?: string
}> {
  // Validate input parameter
  if (!tldString || typeof tldString !== 'string' || tldString === '[object Window]') {
    console.error('❌ Invalid tldString provided to triggerFullApplicationGeneration:', tldString)
    return {
      success: false,
      message: 'Invalid TLD string provided'
    }
  }

  const crewaiEndpoint = getApiBase()
  
  try {
    console.log(`🚀 Triggering full application generation for: ${tldString}`)
    
    const response = await fetch(`${crewaiEndpoint}/api/applications/generate-full`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        tld_string: tldString,
        applicant_id: applicantId,
        use_case: 'ICANN Application Generation',
        generate_answers: true,
        store_in_database: true
      })
    })

    if (!response.ok) {
      const errorText = await response.text()
      throw new Error(`CrewAI service error (${response.status}): ${errorText}`)
    }

    const result = await response.json()
    console.log('✅ Full application generation result:', result)
    
    return {
      success: true,
      message: result.message || 'Full application generation started successfully',
      application_id: result.application_id
    }
  } catch (error) {
    console.error('❌ Error triggering full application generation:', error)
    return {
      success: false,
      message: (error instanceof Error ? error.message : '') || 'Failed to trigger application generation'
    }
  }
}

// Get generation status for an application
export async function getApplicationGenerationStatus(applicationId: string): Promise<{
  status: string
  progress: number
  message: string
  answers_count?: number
  completed_answers?: number
}> {
  const crewaiEndpoint = getApiBase()
  
  try {
    const response = await fetch(`${crewaiEndpoint}/api/applications/${applicationId}/status`)
    
    if (!response.ok) {
      throw new Error(`Failed to get application status: ${response.statusText}`)
    }

    const result = await response.json()
    return {
      status: result.status || 'unknown',
      progress: result.progress || 0,
      message: result.message || 'No status message',
      answers_count: result.answers_count,
      completed_answers: result.completed_answers
    }
  } catch (error) {
    console.error('Error getting application status:', error)
    return {
      status: 'error',
      progress: 0,
      message: (error instanceof Error ? error.message : '') || 'Failed to get status'
    }
  }
}

// Delete application by ID or TLD string
export async function deleteApplication(applicationId?: string, tldString?: string): Promise<void> {
  let query = supabase.from('tld_applications').delete()
  
  if (applicationId) {
    query = query.eq('id', applicationId)
  } else if (tldString) {
    query = query.eq('tld_string', tldString.toLowerCase())
  } else {
    throw new Error('Must provide either applicationId or tldString')
  }
  
  const { error } = await query
  
  if (error) {
    throw new Error(`Failed to delete application: ${error.message}`)
  }
  
  console.log(`✅ Deleted application${applicationId ? ` ${applicationId}` : ''}${tldString ? ` for .${tldString}` : ''}`)
} 