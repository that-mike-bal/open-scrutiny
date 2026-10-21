import React, { useState, useEffect, useMemo } from 'react'
import { getApiBase } from '@/lib/api-config'
import { formatDistanceToNow } from 'date-fns'
import NewEvaluationModal from '@/components/NewEvaluationModal'
import CreateApplicationModal from '@/components/CreateApplicationModal'
import Navigation from '@/components/Navigation'
import { useNavigate } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { Plus, Clock, AlertCircle, CheckCircle, Grid3X3, List, ArrowUpDown, Filter, Trash2, Loader2, FileText, RotateCcw, MoreVertical, Search } from 'lucide-react'
import { deleteTldEvaluation, retryTldEvaluation } from '../lib/supabase-api'
import { useTldEvaluations } from '@/hooks/useTldEvaluations'
import { useSearchEvaluations } from '@/hooks/useSearchEvaluations'
import { useDebounce } from '@/hooks/useDebounce'
import { QueuedStrings, type QueuedString } from './QueuedStrings'

// Types for filtering and sorting
type ViewMode = 'grid' | 'list'
type SortOption = 'name-asc' | 'name-desc' | 'date-asc' | 'date-desc' | 'status' | 'risk-asc' | 'risk-desc'
type StatusFilter = 'all' | 'completed' | 'running' | 'failed' | 'pending'
type ComplianceFilter = 'all' | 'pass' | 'blocked' | 'requires-exception'
type RiskFilter = 'all' | 'low' | 'medium' | 'high' | 'critical'

// Custom error for server-busy 409 responses — callers can catch this specifically
class ServerBusyError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'ServerBusyError'
  }
}

// Workflow status for specific TLD
interface TldWorkflowStatus {
  tld_string_id: string
  workflows: Array<{
    workflow_type: string
    status: string
    auto_triggered: boolean
    started_at?: string
    completed_at?: string
    error_message?: string
  }>
  all_complete: boolean
}

// Toast notification component
interface ToastProps {
  message: string
  type: 'success' | 'info' | 'warning' | 'error'
  onClose: () => void
}

function Toast({ message, type, onClose }: ToastProps) {
  const bgColor = {
    success: 'bg-green-100 border-green-400 text-green-700',
    info: 'bg-blue-100 border-blue-400 text-blue-700',
    warning: 'bg-yellow-100 border-yellow-400 text-yellow-700',
    error: 'bg-red-100 border-red-400 text-red-700'
  }[type]

  const icon = {
    success: <CheckCircle className="w-4 h-4" />,
    info: <Clock className="w-4 h-4" />,
    warning: <AlertCircle className="w-4 h-4" />,
    error: <AlertCircle className="w-4 h-4" />
  }[type]

  return (
    <div className={`fixed top-4 right-4 z-50 border px-4 py-3 rounded-md shadow-lg animate-in slide-in-from-top-2 ${bgColor}`}>
      <div className="flex items-center space-x-2">
        {icon}
        <span className="text-sm font-medium">{message}</span>
        <button onClick={onClose} className="ml-2 text-lg leading-none hover:opacity-70">
          ×
        </button>
      </div>
    </div>
  )
}

// Helper function to get display status text
const getDisplayStatus = (status: string | undefined, overallStatus: string | undefined, hasData: boolean): string => {
  // Prioritize overall_status if it exists
  const actualStatus = overallStatus || status
  
  switch (actualStatus?.toUpperCase()) {
    case 'COMPLETED':
      return 'Completed'
    case 'RUNNING':
      return 'Evaluating'
    case 'FAILED':
      return 'Failed'
    case 'PENDING':
      return 'Pending'
    default:
      // Only show "No Data" for unknown statuses when there's no data
      return hasData ? (actualStatus || 'Unknown') : 'No Data'
  }
}

// Helper function to get risk badge variant and text
const getRiskBadgeInfo = (riskScore?: number, riskLevel?: string): { variant: "default" | "secondary" | "destructive" | "outline" | "success" | "warning", text: string, color?: string } => {
  if (riskScore !== undefined) {
    if (riskScore <= 20) return { variant: 'success', text: `${riskScore}/100`, color: 'bg-green-100 text-green-800' }
    if (riskScore <= 40) return { variant: 'outline', text: `${riskScore}/100`, color: 'bg-yellow-100 text-yellow-800' }
    if (riskScore <= 60) return { variant: 'warning', text: `${riskScore}/100`, color: 'bg-orange-100 text-orange-800' }
    if (riskScore <= 80) return { variant: 'destructive', text: `${riskScore}/100`, color: 'bg-red-100 text-red-800' }
    return { variant: 'destructive', text: `${riskScore}/100`, color: 'bg-red-200 text-red-900' }
  }
  
  if (riskLevel) {
    const level = riskLevel.toLowerCase()
    if (level.includes('low')) return { variant: 'success', text: 'Low Risk' }
    if (level.includes('medium') || level.includes('moderate')) return { variant: 'warning', text: 'Medium Risk' }
    if (level.includes('high')) return { variant: 'destructive', text: 'High Risk' }
    if (level.includes('critical')) return { variant: 'destructive', text: 'Critical Risk' }
  }
  
  return { variant: 'secondary', text: 'No Risk Data' }
}

export default function SimpleDashboard() {
  const QUEUE_STORAGE_KEY = 'tld_evaluation_queue_v1'
  const DASHBOARD_SETTINGS_KEY = 'tld_dashboard_settings_v1'
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'info' | 'warning' | 'error' } | null>(null)
  const [queuedStrings, setQueuedStrings] = useState<QueuedString[]>([])
  const [autoSubmit, setAutoSubmit] = useState(true)
  const navigate = useNavigate()
  
  // Load saved dashboard settings from localStorage
  const loadDashboardSettings = () => {
    try {
      const saved = localStorage.getItem(DASHBOARD_SETTINGS_KEY)
      if (saved) {
        return JSON.parse(saved)
      }
    } catch (error) {
      console.warn('Failed to load dashboard settings:', error)
    }
    return {
      viewMode: 'grid',
      sortBy: 'date-desc',
      statusFilter: 'all',
      complianceFilter: 'all',
      riskFilter: 'all'
    }
  }
  
  // View and filter state with persistence
  const [viewMode, setViewMode] = useState<ViewMode>(loadDashboardSettings().viewMode)
  const [sortBy, setSortBy] = useState<SortOption>(loadDashboardSettings().sortBy)
  const [statusFilter, setStatusFilter] = useState<StatusFilter>(loadDashboardSettings().statusFilter)
  const [complianceFilter, setComplianceFilter] = useState<ComplianceFilter>(loadDashboardSettings().complianceFilter)
  const [riskFilter, setRiskFilter] = useState<RiskFilter>(loadDashboardSettings().riskFilter)
  const [searchTerm, setSearchTerm] = useState<string>('')
  
  // Cleanup mode state
  const [cleanupMode, setCleanupMode] = useState(false)
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set())
  const [isDeleting, setIsDeleting] = useState(false)
  
  // Retry state
  const [retryingItems, setRetryingItems] = useState<Set<string>>(new Set())
  
  // Application creation modal state
  const [createAppModalOpen, setCreateAppModalOpen] = useState(false)
  const [selectedTldForApp, setSelectedTldForApp] = useState<{ tldString: string; evaluationId: string } | null>(null)
  
  // Queue system removed - workflows run directly
  const [workflowStatuses] = useState<Map<string, TldWorkflowStatus>>(new Map())
  
  // Use the real API hook instead of mock data
  const { evaluations, loading, loadingMore, error, refetch, loadMore, hasMore } = useTldEvaluations()
  const { searchResults, isSearching, searchError, searchEvaluations } = useSearchEvaluations()

  // Debounce search term to avoid excessive API calls
  const debouncedSearchTerm = useDebounce(searchTerm, 300)

  // Trigger search when debounced term changes
  useEffect(() => {
    if (debouncedSearchTerm.trim()) {
      searchEvaluations(debouncedSearchTerm)
    }
  }, [debouncedSearchTerm, searchEvaluations])

  // Client-side queue system - no server-side queue needed

  // Client-side queue management functions
  const addToQueue = (tldString: string, useCase: string) => {
    const queuedString: QueuedString = {
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      tldString,
      useCase,
      queuedAt: new Date().toISOString()
    }
    
    console.log('📋 Adding to queue:', tldString, queuedString)
    setQueuedStrings(prev => {
      const newQueue = [...prev, queuedString]
      console.log('📋 Queue updated, new length:', newQueue.length)
      return newQueue
    })
    showToast(`📋 .${tldString} added to queue`, 'info')
  }

  // Persist queue to localStorage so it survives navigation and reloads
  useEffect(() => {
    console.log('🔍 QUEUE INIT: Starting localStorage load...')
    try {
      const saved = localStorage.getItem(QUEUE_STORAGE_KEY)
      console.log('🔍 Raw localStorage value:', saved)
      console.log('🔍 localStorage key exists:', saved !== null)
      
      if (saved && saved !== 'null' && saved !== '[]') {
        const parsed: QueuedString[] = JSON.parse(saved)
        console.log('🔍 Successfully parsed:', parsed.length, 'items')
        console.log('🔍 Parsed data:', parsed)
        
        if (Array.isArray(parsed) && parsed.length > 0) {
          setQueuedStrings(parsed)
          console.log('🔍 ✅ Queue restored from localStorage:', parsed.length, 'items')
        } else {
          console.log('🔍 ❌ Parsed array is empty or invalid')
        }
      } else {
        console.log('🔍 No valid saved queue found (empty/null)')
      }
    } catch (error) {
      console.error('🔍 ❌ Error loading queue from localStorage:', error)
      console.error('🔍 localStorage content that failed to parse:', localStorage.getItem(QUEUE_STORAGE_KEY))
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    try {
      console.log('💾 Saving queue to localStorage:', queuedStrings.length, 'items')
      localStorage.setItem(QUEUE_STORAGE_KEY, JSON.stringify(queuedStrings))
    } catch {}
  }, [queuedStrings])

  // Save dashboard settings to localStorage whenever they change
  useEffect(() => {
    const settings = {
      viewMode,
      sortBy,
      statusFilter,
      complianceFilter,
      riskFilter
    }
    try {
      localStorage.setItem(DASHBOARD_SETTINGS_KEY, JSON.stringify(settings))
    } catch (error) {
      console.warn('Failed to save dashboard settings:', error)
    }
  }, [viewMode, sortBy, statusFilter, complianceFilter, riskFilter])

  // Auto-submit is handled by QueuedStrings component (polls every 3s, reacts to serverStatus?.available)

  // Silent queue removal — used internally after successful submission
  const dequeueString = (id: string) => {
    setQueuedStrings(prev => {
      const item = prev.find(q => q.id === id)
      if (item) {
        console.log('✅ Dequeued after successful submission:', item.tldString)
      }
      return prev.filter(q => q.id !== id)
    })
  }

  // User-initiated queue removal — shows toast (used by X button)
  const removeFromQueue = (id: string) => {
    setQueuedStrings(prev => {
      const item = prev.find(q => q.id === id)
      if (item) {
        console.log('🗑️ Removed from queue:', item.tldString)
        showToast(`🗑️ .${item.tldString} removed from queue`, 'info')
      }
      return prev.filter(q => q.id !== id)
    })
  }

  const submitQueuedString = async (queuedString: QueuedString) => {
    console.log('🚀 Submitting queued string:', queuedString.tldString)

    try {
      // Submit to API FIRST — only dequeue after confirmed success
      await submitEvaluationDirect(queuedString.tldString, queuedString.useCase, true)
      // Success — silently remove from queue (no toast)
      dequeueString(queuedString.id)
    } catch (error) {
      if (error instanceof ServerBusyError) {
        // Server still busy — keep in queue silently for next retry
        console.log('⏳ Server still busy, keeping in queue:', queuedString.tldString)
        return
      }
      // Real failure — show error toast but keep in queue
      console.error('❌ Failed to submit queued string:', error)
      showToast(`❌ Failed to submit .${queuedString.tldString}: ${error instanceof Error ? error.message : 'Unknown error'}`, 'error')
      throw error
    }
  }

  const toggleAutoSubmit = () => {
    setAutoSubmit(prev => !prev)
    console.log('🔄 Auto-submit toggled:', !autoSubmit)
  }

  const handleSuccess = async (tldString: string, useCase: string, autoExecution: boolean, stringType?: 'primary' | 'secondary') => {
    setIsModalOpen(false)

    if (!autoExecution) {
      // For manual workflows, just create the entry without workflows
      try {
        await submitEvaluationDirect(tldString, useCase, false, stringType)
      } catch (error: any) {
        console.error('❌ Failed to create evaluation:', error)
        showToast(`❌ Failed to create evaluation: ${error.message}`, 'error')
      }
      return
    }
    
    // For auto-execution, check if server is available with timeout and better error handling
    try {
      console.log('🔍 Checking server status before submitting:', tldString)
      
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 3000) // 3 second timeout
      
      const statusResponse = await fetch(`${getApiBase()}/api/server-status`, {
        signal: controller.signal,
        headers: { 'Content-Type': 'application/json' }
      })
      clearTimeout(timeoutId)
      
      if (!statusResponse.ok) {
        throw new Error(`Server status check failed: ${statusResponse.status}`)
      }
      
      const serverStatus = await statusResponse.json()
      console.log('📊 Server status:', serverStatus)
      
      if (serverStatus.available === true && serverStatus.running_count === 0) {
        // Server is definitely free - submit immediately
        console.log('🚀 Server available, submitting immediately:', tldString)
        await submitEvaluationDirect(tldString, useCase, true, stringType)
      } else {
        // Server is busy or has running tasks - add to queue
        console.log('⏳ Server busy, adding to queue:', tldString)
        addToQueue(tldString, useCase)
      }
    } catch (error) {
      console.error('❌ Error checking server status, defaulting to queue:', error)
      // On any error (timeout, network failure, etc.), default to queueing
      addToQueue(tldString, useCase)
    }
  }

  const submitEvaluationDirect = async (tldString: string, useCase: string, autoExecution: boolean, stringType?: 'primary' | 'secondary') => {
    console.log('📡 Submitting evaluation to API:', { tldString, useCase, autoExecution })

    const response = await fetch(`${getApiBase()}/api/evaluations/auto-submit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        tld_string: tldString,
        use_case: useCase,
        enable_auto_execution: autoExecution,
        string_type: stringType || 'primary'
      })
    })

    if (response.status === 409) {
      // Server is busy — throw typed error so callers can keep the string in queue
      const errorData = await response.json().catch(() => ({ detail: 'Server busy' }))
      throw new ServerBusyError(errorData.detail || 'Server is busy')
    }

    if (!response.ok) {
      const errorData = await response.text()
      console.error('❌ API error response:', errorData)
      throw new Error(errorData || 'Failed to submit evaluation')
    }

    const result = await response.json()
    console.log('✅ API submission successful:', result)

    if (autoExecution) {
      showToast(`🚀 .${tldString} evaluation started!`, 'success')
    } else {
      showToast(`✅ Evaluation created for .${tldString}!`, 'info')
    }

    refetch()
  }


  // Queue system removed - no more polling needed

  // Basic initialization
  useEffect(() => {
    console.log('Dashboard mounted, evaluations loaded:', evaluations.length)
    console.log('Supabase URL:', import.meta.env.VITE_SUPABASE_URL)
    console.log('Has Supabase key:', !!import.meta.env.VITE_SUPABASE_ANON_KEY)
    console.log('Loading state:', loading)
    console.log('Error state:', error)
    console.log('Raw evaluations data:', evaluations)
  }, [evaluations.length, loading, error])

  // Helper function to determine if TLD has active workflows
  const hasActiveWorkflowsForTld = (evaluationId: string): boolean => {
    // Check workflow status using evaluation ID
    const workflowStatus = workflowStatuses.get(evaluationId)
    return workflowStatus ? !workflowStatus.all_complete : false
  }

  // Helper function to get workflow progress summary
  const getWorkflowProgress = (tldId: string) => {
    const workflowStatus = workflowStatuses.get(tldId)
    if (!workflowStatus) return null
    
    const total = workflowStatus.workflows.length
    const completed = workflowStatus.workflows.filter(w => w.status === 'COMPLETED').length
    const running = workflowStatus.workflows.filter(w => w.status === 'RUNNING').length
    
    return { total, completed, running }
  }

  // Helper function to determine compliance status from evaluation
  const getComplianceStatus = (evaluation: any): ComplianceFilter => {
    // This would need to be enhanced based on actual task execution data
    // For now, we'll use basic logic based on status
    if (evaluation.status === 'COMPLETED') {
      // Check if any tasks were blocked
      const hasBlockedTasks = evaluation.task_executions?.some((task: any) => 
        task.result_status === 'BLOCKED' || task.result_status === 'FAIL'
      )
      if (hasBlockedTasks) return 'blocked'
      
      const hasExceptionTasks = evaluation.task_executions?.some((task: any) => 
        task.result_status === 'REQUIRES_EXCEPTION'
      )
      if (hasExceptionTasks) return 'requires-exception'
      
      return 'pass'
    }
    return 'pass' // Default for incomplete evaluations
  }

  // Helper function to determine risk level from evaluation using actual risk scores
  const getRiskLevel = (evaluation: any): RiskFilter => {
    // Check for risk data in generated_report.risk_assessment
    const riskAssessment = evaluation.generated_report?.risk_assessment
    if (riskAssessment) {
      const riskScore = riskAssessment.risk_score
      if (riskScore !== undefined) {
        if (riskScore === 1) return 'low'
        if (riskScore === 2) return 'medium'
        if (riskScore === 3) return 'high'
        if (riskScore === 4) return 'critical'
      }
      
      // Fallback to risk level
      const riskLevel = riskAssessment.risk_level
      if (riskLevel) {
        const level = riskLevel.toLowerCase()
        if (level.includes('low')) return 'low'
        if (level.includes('moderate')) return 'medium'
        if (level.includes('concerning')) return 'high'
        if (level.includes('high')) return 'high'
        if (level.includes('critical')) return 'critical'
      }
    }
    
    // Use actual risk score if available (legacy)
    if (evaluation.risk_score !== undefined) {
      if (evaluation.risk_score <= 20) return 'low'
      if (evaluation.risk_score <= 40) return 'low' // Still considered low-moderate
      if (evaluation.risk_score <= 60) return 'medium'
      if (evaluation.risk_score <= 80) return 'high'
      return 'critical'
    }
    
    // Fallback to risk level classification (legacy)
    if (evaluation.risk_level) {
      const level = evaluation.risk_level.toLowerCase()
      if (level.includes('low')) return 'low'
      if (level.includes('medium') || level.includes('moderate')) return 'medium'
      if (level.includes('high')) return 'high'
      if (level.includes('critical')) return 'critical'
    }
    
    // Legacy logic for older evaluations without risk scores
    if (evaluation.workflow_type === 'technical_risk_assessment' && evaluation.status === 'COMPLETED') {
      // Look for risk scores in task executions
      const riskTasks = evaluation.task_executions?.filter((task: any) => 
        task.workflow_context?.risk_score || task.workflow_context?.risk_level
      )
      
      if (riskTasks?.length > 0) {
        const highestRisk = Math.max(...riskTasks.map((task: any) => 
          task.workflow_context?.risk_score || 1
        ))
        
        if (highestRisk >= 4) return 'high'
        if (highestRisk >= 2) return 'medium'
        return 'low'
      }
    }
    return 'low' // Default for binary compliance or incomplete evaluations
  }

  // Filtered and sorted evaluations - WITH SAFETY CHECKS
  const filteredAndSortedEvaluations = useMemo(() => {
    try {
      console.log('🔍 DEBUG: Processing evaluations in filteredAndSortedEvaluations')

      // Use search results if there's a search term AND we got results, otherwise use regular evaluations
      // If search failed (searchError exists), fall back to client-side filtering
      const hasSearchTerm = searchTerm.trim()
      const useServerSearch = hasSearchTerm && !searchError && searchResults.length > 0
      const sourceEvaluations = useServerSearch ? searchResults : evaluations

      console.log('🔍 DEBUG: source evaluations type:', typeof sourceEvaluations)
      console.log('🔍 DEBUG: source evaluations length:', sourceEvaluations?.length)
      console.log('🔍 DEBUG: using server search:', useServerSearch)
      console.log('🔍 DEBUG: search error:', searchError)

      if (!Array.isArray(sourceEvaluations)) {
        console.warn('Source evaluations is not an array:', sourceEvaluations)
        return []
      }

      let filtered = sourceEvaluations.filter(evaluation => {
        if (!evaluation) return false

        try {
          // Apply client-side search filter if we're not using server search
          if (hasSearchTerm && !useServerSearch) {
            const term = searchTerm.toLowerCase().trim()
            const tldString = (evaluation.tld_string || '').toLowerCase()
            const useCase = (evaluation.use_case || '').toLowerCase()
            const matchesTld = tldString.includes(term)
            const matchesUseCase = useCase.includes(term)
            if (!matchesTld && !matchesUseCase) return false
          }

          // Status filter
          if (statusFilter !== 'all') {
            const hasData = (evaluation.task_executions?.length || 0) > 0 ||
                          evaluation.status === 'RUNNING' ||
                          evaluation.status === 'COMPLETED' ||
                          !!evaluation.use_case
            const status = getDisplayStatus(evaluation.status || 'PENDING', evaluation.overall_status, hasData)
            switch (statusFilter) {
              case 'completed':
                if (status !== 'Completed') return false
                break
              case 'running':
                if (status !== 'Evaluating' && !hasActiveWorkflowsForTld(evaluation.id || '')) return false
                break
              case 'failed':
                if (status !== 'Failed') return false
                break
              case 'pending':
                if (status !== 'Evaluating' && status !== 'No Data') return false
                break
            }
          }

          // Compliance filter
          if (complianceFilter !== 'all') {
            const compliance = getComplianceStatus(evaluation)
            if (compliance !== complianceFilter) return false
          }

          // Risk filter
          if (riskFilter !== 'all') {
            const risk = getRiskLevel(evaluation)
            if (risk !== riskFilter) return false
          }

          return true
        } catch (error) {
          console.warn('Error filtering evaluation:', evaluation, error)
          return false
        }
      })

    // Apply sorting
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'name-asc':
          return (a.tld_string || '').localeCompare(b.tld_string || '')
        case 'name-desc':
          return (b.tld_string || '').localeCompare(a.tld_string || '')
        case 'date-asc':
          return new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
        case 'date-desc':
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        case 'status':
          const hasDataA = (a.task_executions?.length || 0) > 0 || a.status === 'RUNNING' || a.status === 'COMPLETED' || !!a.use_case
          const hasDataB = (b.task_executions?.length || 0) > 0 || b.status === 'RUNNING' || b.status === 'COMPLETED' || !!b.use_case
          const statusA = getDisplayStatus(a.status || 'PENDING', a.overall_status, hasDataA)
          const statusB = getDisplayStatus(b.status || 'PENDING', b.overall_status, hasDataB)
          return statusA.localeCompare(statusB)
        case 'risk-asc':
          const riskScoreA = a.generated_report?.risk_assessment?.risk_score || a.risk_score || 0
          const riskScoreB = b.generated_report?.risk_assessment?.risk_score || b.risk_score || 0
          return riskScoreA - riskScoreB
        case 'risk-desc':
          const riskScoreA2 = a.generated_report?.risk_assessment?.risk_score || a.risk_score || 0
          const riskScoreB2 = b.generated_report?.risk_assessment?.risk_score || b.risk_score || 0
          return riskScoreB2 - riskScoreA2
        default:
          return 0
      }
    })

    return filtered
    } catch (error) {
      console.warn('Error in filteredAndSortedEvaluations:', error)
      return []
    }
  }, [evaluations, searchResults, statusFilter, complianceFilter, riskFilter, sortBy, searchTerm, searchError])

  const showToast = (message: string, type: 'success' | 'info' | 'warning' | 'error') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 5000) // Auto-hide after 5 seconds
  }

  const clearQueue = () => {
    setQueuedStrings([])
    showToast('Queue cleared', 'info')
  }

  const handleRefresh = () => {
    refetch()
  }

  // Cleanup mode functions
  const toggleCleanupMode = () => {
    setCleanupMode(!cleanupMode)
    setSelectedItems(new Set()) // Clear selections when toggling
  }

  const toggleItemSelection = (tldId: string) => {
    const newSelected = new Set(selectedItems)
    if (newSelected.has(tldId)) {
      newSelected.delete(tldId)
    } else {
      newSelected.add(tldId)
    }
    setSelectedItems(newSelected)
  }

  const selectAllItems = () => {
    const allIds = new Set(filteredAndSortedEvaluations.map(evaluation => evaluation.id))
    setSelectedItems(allIds)
  }

  const clearSelection = () => {
    setSelectedItems(new Set())
  }

  const handleCreateApplication = (tldString: string, evaluationId: string) => {
    console.log(`📋 Opening application creation modal for .${tldString} (evaluation: ${evaluationId})`)
    setSelectedTldForApp({ tldString, evaluationId })
    setCreateAppModalOpen(true)
  }

  const deleteSelectedItems = async () => {
    if (selectedItems.size === 0) return

    setIsDeleting(true)
    console.log('🗑️ Starting deletion of items:', Array.from(selectedItems))
    
    try {
      const results: Array<{tldId: string, success: boolean, result: any}> = []
      const failures: Array<{tldId: string, error: string}> = []
      
      // Delete each selected item with individual error handling
      for (const tldId of selectedItems) {
        try {
          console.log(`🗑️ Deleting TLD: ${tldId}`)
          await deleteTldEvaluation(tldId)
          console.log(`✅ Successfully deleted ${tldId}`)
          results.push({ tldId, success: true, result: { message: 'Deleted successfully' } })
        } catch (error: unknown) {
          console.error(`❌ Network error deleting ${tldId}:`, error)
          failures.push({ tldId, error: error instanceof Error ? error.message : String(error) })
        }
      }
      
      // Immediately refetch data after deletion
      console.log('🔄 Refreshing data after deletion...')
      refetch()
      
      // Show appropriate toast message based on results
      if (failures.length === 0) {
        // All deletions successful
        showToast(`Successfully deleted ${results.length} TLD evaluation(s)`, 'success')
        setSelectedItems(new Set())
        setCleanupMode(false)
      } else if (results.length === 0) {
        // All deletions failed
        showToast(`Failed to delete all ${failures.length} TLD evaluation(s)`, 'error')
      } else {
        // Some deletions succeeded, some failed
        showToast(`Deleted ${results.length} items, ${failures.length} failed`, 'warning')
        // Remove successfully deleted items from selection
        const remainingItems = new Set(failures.map(f => f.tldId))
        setSelectedItems(remainingItems)
      }
      
    } catch (error) {
      console.error('❌ Unexpected error in delete operation:', error)
      showToast('Unexpected error during deletion', 'error')
    } finally {
      setIsDeleting(false)
    }
  }

  const handleRetryEvaluation = async (evaluationId: string, tldString: string) => {
    setRetryingItems(prev => new Set([...prev, evaluationId]))
    
    try {
      console.log(`🔄 Retrying evaluation for .${tldString}`)
      await retryTldEvaluation(evaluationId)
      
      showToast(`🔄 Restarted evaluation for .${tldString}`, 'success')
      
      // Refetch data to show updated status
      refetch()
      
    } catch (error: unknown) {
      console.error('❌ Retry failed:', error)
      showToast(
        `Failed to retry .${tldString}: ${error instanceof Error ? error.message : 'Unknown error'}`, 
        'error'
      )
    } finally {
      setRetryingItems(prev => {
        const newSet = new Set(prev)
        newSet.delete(evaluationId)
        return newSet
      })
    }
  }

  // Show loading only for the initial fetch or when we have data
  if (loading && evaluations.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
        <div className="max-w-7xl mx-auto">
          <div className="flex justify-center items-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            <span className="ml-3 text-lg">Loading evaluations...</span>
          </div>
        </div>
      </div>
    )
  }

  // Show error state
  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-col items-center justify-center h-64">
            <div className="text-red-600 text-lg mb-4">⚠️ Error loading dashboard</div>
            <div className="text-gray-600 text-sm mb-4">{error}</div>
            <button 
              onClick={handleRefresh}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    )
  }

  if (evaluations.length === 0) {
    return (
      <div className="min-h-screen bg-background">
        <div className="container mx-auto px-4 py-8">
          <div className="flex justify-between items-center mb-8">
            <div>
              <h1 className="text-3xl font-bold tracking-tight">TLD Evaluations</h1>
              <p className="text-muted-foreground">
                Manage and track your TLD evaluation workflows
              </p>
            </div>
            <Button onClick={() => setIsModalOpen(true)}>
              <Plus className="w-4 h-4 mr-2" />
              Add New String
            </Button>
          </div>

          <Card className="max-w-md mx-auto mt-8">
            <CardContent className="pt-6">
              <div className="text-center">
                <FileText className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-lg font-semibold mb-2">No TLD Evaluations Found</h3>
                <p className="text-sm text-muted-foreground mb-4">
                  Get started by creating your first TLD evaluation workflow.
                </p>
                <Button onClick={() => setIsModalOpen(true)}>
                  <Plus className="w-4 h-4 mr-2" />
                  Create First Evaluation
                </Button>
              </div>
            </CardContent>
          </Card>

          <NewEvaluationModal
            isOpen={isModalOpen}
            onClose={() => setIsModalOpen(false)}
            onSuccess={handleSuccess}
          />
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <Navigation />
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex flex-col gap-6 mb-8">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold tracking-tight">TLD Evaluations</h1>
              <p className="text-muted-foreground">
                Manage and track your TLD evaluation workflows
              </p>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={handleRefresh}>
                Refresh
              </Button>
              <Button 
                variant={cleanupMode ? "destructive" : "outline"} 
                size="sm" 
                onClick={toggleCleanupMode}
              >
                <Trash2 className="w-4 h-4 mr-2" />
                {cleanupMode ? 'Cancel Cleanup' : 'Cleanup Mode'}
              </Button>
              {!cleanupMode && (
                <Button onClick={() => setIsModalOpen(true)}>
                  <Plus className="w-4 h-4 mr-2" />
                  Add New String
                </Button>
              )}
            </div>
          </div>

          {/* Queued Strings Component */}
          <QueuedStrings
            queuedStrings={queuedStrings}
            onRemoveFromQueue={removeFromQueue}
            onSubmitString={submitQueuedString}
            autoSubmit={autoSubmit}
            onToggleAutoSubmit={toggleAutoSubmit}
            onClearQueue={clearQueue}
          />

          {/* Controls Bar */}
          <div className="flex flex-wrap items-center justify-between gap-4 p-4 bg-muted/30 rounded-lg">
            {/* Search and View Mode */}
            <div className="flex items-center gap-4">
              {/* Search Input */}
              <div className="relative">
                {isSearching ? (
                  <Loader2 className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground animate-spin" />
                ) : (
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                )}
                <Input
                  placeholder="Search all strings..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-9 w-64"
                />
              </div>

              {/* View Mode Toggle */}
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">View:</span>
                <div className="flex rounded-md border">
                  <Button
                    variant={viewMode === 'grid' ? 'default' : 'ghost'}
                    size="sm"
                    onClick={() => setViewMode('grid')}
                    className="rounded-r-none"
                  >
                    <Grid3X3 className="w-4 h-4" />
                  </Button>
                  <Button
                    variant={viewMode === 'list' ? 'default' : 'ghost'}
                    size="sm"
                    onClick={() => setViewMode('list')}
                    className="rounded-l-none"
                  >
                    <List className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </div>

            {/* Filters */}
            <div className="flex flex-wrap items-center gap-4">
              {/* Sort */}
              <div className="flex items-center gap-2">
                <ArrowUpDown className="w-4 h-4 text-muted-foreground" />
                <Select value={sortBy} onValueChange={(value: SortOption) => setSortBy(value)}>
                  <SelectTrigger className="w-40">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="name-asc">Name A-Z</SelectItem>
                    <SelectItem value="name-desc">Name Z-A</SelectItem>
                    <SelectItem value="date-desc">Newest First</SelectItem>
                    <SelectItem value="date-asc">Oldest First</SelectItem>
                    <SelectItem value="status">By Status</SelectItem>
                    <SelectItem value="risk-asc">Lowest Risk</SelectItem>
                    <SelectItem value="risk-desc">Highest Risk</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Status Filter */}
              <div className="flex items-center gap-2">
                <Filter className="w-4 h-4 text-muted-foreground" />
                <Select value={statusFilter} onValueChange={(value: StatusFilter) => setStatusFilter(value)}>
                  <SelectTrigger className="w-32">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Status</SelectItem>
                    <SelectItem value="completed">Completed</SelectItem>
                    <SelectItem value="running">Evaluating</SelectItem>
                    <SelectItem value="failed">Failed</SelectItem>
                    <SelectItem value="pending">Evaluating</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Compliance Filter */}
              <Select value={complianceFilter} onValueChange={(value: ComplianceFilter) => setComplianceFilter(value)}>
                <SelectTrigger className="w-36">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Compliance</SelectItem>
                  <SelectItem value="pass">Pass</SelectItem>
                  <SelectItem value="blocked">Blocked</SelectItem>
                  <SelectItem value="requires-exception">Needs Exception</SelectItem>
                </SelectContent>
              </Select>

              {/* Risk Filter */}
              <Select value={riskFilter} onValueChange={(value: RiskFilter) => setRiskFilter(value)}>
                <SelectTrigger className="w-32">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Risk</SelectItem>
                  <SelectItem value="low">Low Risk</SelectItem>
                  <SelectItem value="medium">Medium Risk</SelectItem>
                  <SelectItem value="high">High Risk</SelectItem>
                  <SelectItem value="critical">Critical Risk</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Results Count and Hints */}
            <div className="text-sm text-muted-foreground space-y-1">
              <div>{filteredAndSortedEvaluations.length} of {evaluations.length} evaluations</div>
              {!cleanupMode && (
                <div className="text-xs opacity-75">
                  💡 Right-click or Cmd+click cards to open in new tab
                </div>
              )}
            </div>
          </div>

          {/* Cleanup Mode Controls */}
          {cleanupMode && (
            <div className="flex items-center justify-between p-4 bg-destructive/10 border border-destructive/20 rounded-lg">
              <div className="flex items-center gap-4">
                <span className="text-sm font-medium text-destructive">
                  Cleanup Mode: Select items to delete
                </span>
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <span>{selectedItems.size} selected</span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={selectAllItems}
                  disabled={filteredAndSortedEvaluations.length === 0}
                >
                  Select All ({filteredAndSortedEvaluations.length})
                </Button>
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={clearSelection}
                  disabled={selectedItems.size === 0}
                >
                  Clear Selection
                </Button>
                <Button 
                  variant="destructive" 
                  size="sm" 
                  onClick={deleteSelectedItems}
                  disabled={selectedItems.size === 0 || isDeleting}
                >
                  {isDeleting ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      Deleting...
                    </>
                  ) : (
                    <>
                      <Trash2 className="w-4 h-4 mr-2" />
                      Delete Selected ({selectedItems.size})
                    </>
                  )}
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* Evaluations Display */}
        <div className={viewMode === 'grid' 
          ? "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" 
          : "space-y-4"
        }>
          {filteredAndSortedEvaluations.length === 0 ? (
            <div className="col-span-full">
              <Card className="max-w-md mx-auto mt-8">
                <CardContent className="pt-6">
                  <div className="text-center">
                    <Filter className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                    <h3 className="text-lg font-semibold mb-2">No Evaluations Match Filters</h3>
                    <p className="text-sm text-muted-foreground mb-4">
                      Try adjusting your filters or create a new evaluation.
                    </p>
                    <div className="flex gap-2 justify-center">
                      <Button 
                        variant="outline" 
                        size="sm"
                        onClick={() => {
                          setStatusFilter('all')
                          setComplianceFilter('all')
                          setRiskFilter('all')
                          setSearchTerm('')
                        }}
                      >
                        Clear Filters
                      </Button>
                      <Button size="sm" onClick={() => setIsModalOpen(true)}>
                        <Plus className="w-4 h-4 mr-2" />
                        New Evaluation
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          ) : (
            filteredAndSortedEvaluations.map((evaluation) => {
              // Check if evaluation has actual data - use correct database fields
              const hasData = (evaluation.task_executions?.length || 0) > 0 || 
                            evaluation.status === 'RUNNING' || 
                            evaluation.status === 'COMPLETED' || 
                            !!evaluation.use_case
              
              // Check if there are active workflows for this TLD
              const hasActiveWorkflows = hasActiveWorkflowsForTld(evaluation.id || '')
              const workflowProgress = getWorkflowProgress(evaluation.id)
              
              // Override status if there are active workflows - use correct database field
              const actualStatus = hasActiveWorkflows ? 'RUNNING' : evaluation.status
              const displayStatus = getDisplayStatus(actualStatus, evaluation.overall_status, hasData)
              
              const handleCardClick = (e: React.MouseEvent) => {
                if (cleanupMode) {
                  e.preventDefault()
                  e.stopPropagation()
                  toggleItemSelection(evaluation.id || '')
                } else {
                  // Check for Cmd/Ctrl + click to open in new tab
                  if (e.metaKey || e.ctrlKey) {
                    e.preventDefault()
                    e.stopPropagation()
                    const evaluationUrl = `/evaluation/${evaluation.tld_string || 'unknown'}`
                    const fullUrl = window.location.origin + evaluationUrl
                    window.open(fullUrl, '_blank')
                  } else {
                    e.preventDefault()
                    navigate(`/evaluation/${evaluation.tld_string || 'unknown'}`, { state: { evaluation } })
                  }
                }
              }

              const handleCardRightClick = (e: React.MouseEvent) => {
                if (cleanupMode) return
                
                e.preventDefault()
                e.stopPropagation()
                
                // Open evaluation in new tab
                const evaluationUrl = `/evaluation/${evaluation.tld_string || 'unknown'}`
                const fullUrl = window.location.origin + evaluationUrl
                window.open(fullUrl, '_blank')
              }

              const isSelected = selectedItems.has(evaluation.id || '')

              // Get risk info from the new risk assessment data
              const riskAssessment = evaluation.generated_report?.risk_assessment
              const riskScore = riskAssessment?.risk_score
              const riskLevel = riskAssessment?.risk_level
              const riskColor = riskAssessment?.risk_color
              
              // Get risk badge info - prioritize new risk assessment data
              const riskBadgeInfo = getRiskBadgeInfo(
                riskScore ? riskScore * 25 : evaluation.risk_score, // Convert 1-4 scale to 25-100 for display
                riskLevel || evaluation.risk_level
              )
              
              // Check for binary compliance failures
              const binaryComplianceFailures = evaluation.task_executions?.filter((task: any) => 
                ['iana_database_check', 'blocked_names_check', 'reserved_names_check'].includes(task.task_name) &&
                ['BLOCKED', 'FAIL', 'FAILED'].includes(task.result_status?.toUpperCase())
              ) || []
              
              const hasBinaryFailures = binaryComplianceFailures.length > 0
              
              // Check for high risk - separate new vs legacy detection
              const isHighRiskNew = riskAssessment && (riskScore === 4 || riskLevel === 'HIGH')
              const isHighRiskLegacy = !riskAssessment && evaluation.risk_score !== undefined && evaluation.risk_score > 50
              const isHighRisk = isHighRiskNew || isHighRiskLegacy

              return (
                <Card 
                  key={evaluation.id} 
                  className={`hover:shadow-md transition-all cursor-pointer hover:bg-accent/50 ${
                    actualStatus === 'RUNNING' || hasActiveWorkflows ? 'ring-2 ring-blue-200 bg-blue-50/50 evaluation-running' : ''
                  } ${viewMode === 'list' ? 'w-full' : ''} ${
                    cleanupMode && isSelected ? 'ring-2 ring-destructive bg-destructive/5' : ''
                  } ${cleanupMode ? 'hover:ring-2 hover:ring-destructive/50' : ''} ${
                    hasBinaryFailures || isHighRiskLegacy ? 'ring-2 ring-red-300 bg-red-50/30' : ''
                  }`}
                  onClick={handleCardClick}
                  onContextMenu={handleCardRightClick}
                  title={cleanupMode ? "Click to select" : "Left click to open, right-click or Cmd+click to open in new tab"}
                >
                  <CardHeader className="pb-3">
                    <div className={`flex items-center justify-between ${viewMode === 'list' ? 'flex-row' : 'flex-col sm:flex-row'}`}>
                      <CardTitle className="text-lg flex items-center space-x-2">
                        {cleanupMode && (
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => toggleItemSelection(evaluation.id)}
                            className="w-4 h-4 text-destructive bg-gray-100 border-gray-300 rounded focus:ring-destructive focus:ring-2"
                            onClick={(e) => e.stopPropagation()}
                          />
                        )}
                        <span>.{evaluation.tld_string || 'unknown'}</span>
                        {evaluation.string_type === 'secondary' && (
                          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-700 border border-amber-200">
                            Secondary
                          </span>
                        )}
                        {(actualStatus === 'RUNNING' || hasActiveWorkflows) && (
                          <div className="flex items-center space-x-1">
                            <div className="animate-bounce">
                              <div className="w-1.5 h-1.5 bg-blue-500 rounded-full"></div>
                            </div>
                            <div className="animate-bounce" style={{ animationDelay: '0.1s' }}>
                              <div className="w-1.5 h-1.5 bg-blue-500 rounded-full"></div>
                            </div>
                            <div className="animate-bounce" style={{ animationDelay: '0.2s' }}>
                              <div className="w-1.5 h-1.5 bg-blue-500 rounded-full"></div>
                            </div>
                          </div>
                        )}
                      </CardTitle>
                      <div className="flex items-center gap-2">
                        {/* Card Actions Menu */}
                        {!cleanupMode && (
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button 
                                variant="ghost" 
                                size="sm" 
                                className="h-6 w-6 p-0 hover:bg-gray-100"
                                onClick={(e) => e.stopPropagation()}
                              >
                                <MoreVertical className="h-3 w-3" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end" className="w-48">
                              <DropdownMenuItem onClick={(e) => {
                                e.stopPropagation()
                                handleCreateApplication(evaluation.tld_string, evaluation.id)
                              }}>
                                <FileText className="mr-2 h-4 w-4" />
                                Create Application
                              </DropdownMenuItem>
                              <DropdownMenuItem onClick={(e) => {
                                e.stopPropagation()
                                navigate(`/evaluation/${evaluation.tld_string || 'unknown'}`)
                              }}>
                                <CheckCircle className="mr-2 h-4 w-4" />
                                View Evaluation
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        )}
                        
                        {/* Binary Compliance Failure Badge */}
                        {hasBinaryFailures && (
                          <Badge variant="destructive" className="text-xs font-semibold">
                            ⚠️ BLOCKED
                          </Badge>
                        )}
                        
                        {/* High Risk Score Badge - Only show for legacy high risk */}
                        {isHighRiskLegacy && (
                          <Badge variant="destructive" className="text-xs font-semibold">
                            🚨 HIGH RISK
                          </Badge>
                        )}
                        
                        {/* Only show status badge for FAILED evaluations */}
                        {actualStatus === 'FAILED' && (
                          <Badge variant="destructive" className="text-xs font-semibold">
                            ❌ FAILED
                          </Badge>
                        )}

                        {/* Risk Level Badge - Only show risk classification */}
                        {riskAssessment && (
                          <Badge 
                            variant={
                              riskColor === 'red' ? 'destructive' :
                              riskColor === 'orange' ? 'concerning' :
                              riskColor === 'yellow' ? 'warning' :
                              riskColor === 'green' ? 'success' : 'secondary'
                            }
                            className="text-xs"
                          >
                            {riskLevel}
                          </Badge>
                        )}
                        
                        {/* Legacy Risk Level Badge - Only show if no new risk data */}
                        {!riskAssessment && evaluation.risk_score !== undefined && !isHighRisk && (
                          <Badge 
                            variant={riskBadgeInfo.variant}
                            className={`text-xs ${riskBadgeInfo.color}`}
                          >
                            {riskBadgeInfo.text.includes('/') ? 
                              (evaluation.risk_score <= 20 ? 'LOW' : 
                               evaluation.risk_score <= 40 ? 'MEDIUM' : 
                               evaluation.risk_score <= 70 ? 'HIGH' : 'CRITICAL') 
                              : riskBadgeInfo.text}
                          </Badge>
                        )}
                        
                        {/* Retry Button for Failed Evaluations */}
                        {(actualStatus === 'FAILED' || displayStatus === 'Failed') && !cleanupMode && (
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-8 px-2 text-xs"
                            onClick={(e) => {
                              e.preventDefault()
                              e.stopPropagation()
                              handleRetryEvaluation(evaluation.id, evaluation.tld_string)
                            }}
                            disabled={retryingItems.has(evaluation.id)}
                          >
                            {retryingItems.has(evaluation.id) ? (
                              <>
                                <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                                Retrying...
                              </>
                            ) : (
                              <>
                                <RotateCcw className="w-3 h-3 mr-1" />
                                Retry
                              </>
                            )}
                          </Button>
                        )}
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {/* Simple evaluation summary */}
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-muted-foreground">
                          {evaluation.use_case || 'General Evaluation'}
                        </span>
                        {(actualStatus === 'RUNNING' || hasActiveWorkflows) && (
                          <span className="text-xs text-blue-600 flex items-center gap-1">
                            <Loader2 className="w-3 h-3 animate-spin" />
                            {workflowProgress ? `${workflowProgress.running} running, ${workflowProgress.completed}/${workflowProgress.total} complete` : 'Evaluating...'}
                          </span>
                        )}
                        {hasBinaryFailures && (
                          <span className="text-xs text-red-600 font-medium">
                            ⚠️ Blocked
                          </span>
                        )}
                        {!hasBinaryFailures && isHighRiskNew && (
                          <span className="text-xs text-red-600 font-medium">
                            ⚠️ High Risk
                          </span>
                        )}
                      </div>

                      {/* Simple footer with date */}
                      <div className="flex items-center justify-between pt-2 border-t text-xs text-muted-foreground">
                        <span>
                          {formatDistanceToNow(new Date(evaluation.created_at), { addSuffix: true })}
                        </span>
                        {(actualStatus === 'RUNNING' || hasActiveWorkflows) && (
                          <span className="text-xs text-muted-foreground">
                            Evaluating...
                          </span>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )
            })
          )}
        </div>

        {/* Load More Button */}
        {hasMore && !loading && (
          <div className="flex justify-center mt-8">
            <Button 
              variant="outline" 
              onClick={loadMore}
              disabled={loadingMore}
              className="min-w-32"
            >
              {loadingMore ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Loading...
                </>
              ) : (
                <>
                  <Plus className="w-4 h-4 mr-2" />
                  Load More ({evaluations.length} shown)
                </>
              )}
            </Button>
          </div>
        )}

        {/* End of results indicator */}
        {!hasMore && evaluations.length > 0 && (
          <div className="text-center mt-8 text-sm text-muted-foreground">
            All evaluations loaded ({evaluations.length} total)
          </div>
        )}

        {/* Toast Notification */}
        {toast && (
          <Toast 
            message={toast.message} 
            type={toast.type} 
            onClose={() => setToast(null)} 
          />
        )}

        {/* Modals */}
        <NewEvaluationModal
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          onSuccess={handleSuccess}
        />
        
        <CreateApplicationModal
          isOpen={createAppModalOpen}
          onClose={() => {
            setCreateAppModalOpen(false)
            setSelectedTldForApp(null)
          }}
          tldString={selectedTldForApp?.tldString || ''}
          evaluationId={selectedTldForApp?.evaluationId}
          onApplicationCreated={(applicationId) => {
            console.log(`✅ Application created: ${applicationId}`)
            showToast(`Application created successfully!`, 'success')
            setCreateAppModalOpen(false)
            setSelectedTldForApp(null)
          }}
        />
      </div>
    </div>
  )
} 