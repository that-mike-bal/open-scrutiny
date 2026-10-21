import { useState, useEffect } from 'react'
import { getApiBase } from '@/lib/api-config'
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card"
import { Button } from "./ui/button"
import { Badge } from "./ui/badge"
import { FileText, Download, Sparkles, Code, BookOpen, ClipboardCheck, RefreshCw, CheckCircle2, XCircle, Clock, ChevronDown, ChevronRight, Search, Cpu, AlertTriangle, Info } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { type TldEvaluationWithAnalysis } from "@/types"

interface IntegrityIssue {
  severity: 'CRITICAL' | 'WARNING' | 'INFO'
  task_name: string
  workflow: string
  issue: string
  detail: string
}

interface TaskNarrative {
  task_name: string
  display_name: string
  workflow: string
  agent: string
  api_calls: number
  data_reliability: string
  key_findings: string[]
  result_status: string
  narrative: string
  started_at?: string | null
  completed_at?: string | null
  execution_time_seconds?: number | null
  expects_api_calls?: boolean
  checks_performed?: string[]
  actions_performed?: string[]
}

interface WorkflowSummary {
  tasks_completed: number
  total_api_calls: number
  successful_api_calls: number
  expected_api_tasks?: number
  local_only_tasks?: number
  data_sources: string[]
  overall_reliability: string
  status?: 'completed' | 'completed_with_notes' | 'failed'
  total_execution_time_seconds?: number
}

interface AuditLog {
  audit_id: string | null
  generated_at: string
  total_tasks: number
  audit_health?: 'PASS' | 'WARNING' | 'FAIL'
  integrity_issues?: IntegrityIssue[]
  workflow_summaries: Record<string, WorkflowSummary>
  audit_log: {
    audit_health?: 'PASS' | 'WARNING' | 'FAIL'
    integrity_issues?: IntegrityIssue[]
    task_narratives: TaskNarrative[]
  }
  markdown: string
}

const WORKFLOW_ORDER = [
  'technical_risk_assessment',
  'legal_risk_assessment',
  'policy_safeguard_review'
] as const

const WORKFLOW_DISPLAY_NAMES: Record<string, string> = {
  technical_risk_assessment: 'Technical Risk Assessment',
  legal_risk_assessment: 'Legal Risk Assessment',
  policy_safeguard_review: 'Policy & Safeguard Review'
}

const SUCCESS_STATUSES = new Set([
  'SUCCESS', 'COMPLETED', 'CLEAR', 'PASS',
  'LOW_RISK', 'MEDIUM_RISK', 'HIGH_RISK', 'VERIFIED'
])

function formatDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return '--'
  if (seconds < 60) return `${Math.round(seconds)}s`
  const mins = Math.floor(seconds / 60)
  const secs = Math.round(seconds % 60)
  return `${mins}m ${secs}s`
}

function formatTimestamp(iso: string | null | undefined): string {
  if (!iso) return '--'
  return new Date(iso).toLocaleTimeString('en-US', {
    hour: '2-digit', minute: '2-digit', second: '2-digit'
  })
}

function TaskTimelineRow({ task }: { task: TaskNarrative }) {
  const [expanded, setExpanded] = useState(false)

  const statusIcon = (() => {
    const status = task.result_status?.toUpperCase()
    if (SUCCESS_STATUSES.has(status)) {
      return <CheckCircle2 className="w-4 h-4 text-green-500 shrink-0" />
    }
    if (status === 'FAILED') {
      return <XCircle className="w-4 h-4 text-red-500 shrink-0" />
    }
    return <CheckCircle2 className="w-4 h-4 text-gray-400 shrink-0" />
  })()

  return (
    <div className="bg-white">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-3 flex items-center gap-3 hover:bg-gray-50 transition-colors text-left"
      >
        {statusIcon}
        <span className="font-medium text-sm text-gray-900 flex-1">
          {task.display_name}
        </span>
        <div className="flex items-center gap-3 text-xs text-gray-500">
          {task.expects_api_calls && task.api_calls > 0 ? (
            <span className="flex items-center gap-1">
              <Search className="w-3 h-3" />
              {task.api_calls} call{task.api_calls !== 1 ? 's' : ''}
            </span>
          ) : task.expects_api_calls ? (
            <span className="flex items-center gap-1 text-amber-500">
              <Search className="w-3 h-3" />
              0 calls
            </span>
          ) : (
            <span className="flex items-center gap-1 text-gray-400">
              <Cpu className="w-3 h-3" />
              Local
            </span>
          )}
          {task.execution_time_seconds != null && (
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {formatDuration(task.execution_time_seconds)}
            </span>
          )}
        </div>
        {expanded
          ? <ChevronDown className="w-4 h-4 text-gray-400 shrink-0" />
          : <ChevronRight className="w-4 h-4 text-gray-400 shrink-0" />
        }
      </button>

      {expanded && (
        <div className="px-4 pb-4 pl-11 space-y-3 bg-gray-50 border-t border-gray-100">
          <p className="text-xs text-gray-500">
            Agent: {task.agent} &middot; Status: {task.result_status}
          </p>

          {(task.started_at || task.completed_at) && (
            <p className="text-xs text-gray-500">
              {task.started_at && <>Started: {formatTimestamp(task.started_at)}</>}
              {task.started_at && task.completed_at && <> &rarr; </>}
              {task.completed_at && <>Completed: {formatTimestamp(task.completed_at)}</>}
              {task.execution_time_seconds != null && <> ({formatDuration(task.execution_time_seconds)})</>}
            </p>
          )}

          {task.actions_performed && task.actions_performed.length > 0 && (
            <div>
              <p className="text-xs font-medium text-gray-600 mb-1">Actions performed:</p>
              <ul className="text-xs text-gray-600 space-y-0.5 list-disc pl-4">
                {task.actions_performed.map((action, i) => (
                  <li key={i}>{action}</li>
                ))}
              </ul>
            </div>
          )}

          {task.expects_api_calls && (
            <div className="text-xs text-gray-600">
              <span>API Calls: {task.api_calls} total</span>
              {task.data_reliability && task.data_reliability !== 'UNKNOWN' && (
                <span className="ml-2">
                  &middot; Data: {task.data_reliability === 'FULL' ? 'Verified' :
                                  task.data_reliability === 'PARTIAL' ? 'Partial' :
                                  'Model knowledge'}
                </span>
              )}
            </div>
          )}

          {task.key_findings && task.key_findings.length > 0 && (
            <div>
              <p className="text-xs font-medium text-gray-600 mb-1">Findings:</p>
              <ul className="text-xs text-gray-600 space-y-0.5 list-disc pl-4">
                {task.key_findings.map((finding, i) => (
                  <li key={i}>{finding}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="text-xs text-gray-500 italic border-l-2 border-gray-200 pl-3 mt-2">
            {task.narrative}
          </div>
        </div>
      )}
    </div>
  )
}

function WorkflowStatusBadge({ summary }: { summary: WorkflowSummary }) {
  const status = summary.status || 'completed'

  if (status === 'failed') {
    return <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200 text-xs">Failed</Badge>
  }
  if (status === 'completed_with_notes') {
    return <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200 text-xs">Completed*</Badge>
  }
  return <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200 text-xs">Completed</Badge>
}

interface EvaluationReportViewerProps {
  evaluation: TldEvaluationWithAnalysis
}

export default function EvaluationReportViewer({ evaluation }: EvaluationReportViewerProps) {
  const [geminiReport, setGeminiReport] = useState<string>('')
  const [generatingReport, setGeneratingReport] = useState(false)
  const [reportError, setReportError] = useState<string | null>(null)
  const [, setAutoGenerationAttempted] = useState(false)
  const [viewMode, setViewMode] = useState<'crewai' | 'ai' | 'audit'>('crewai') // Toggle between views
  const [pollingForReport, setPollingForReport] = useState(false)

  // Audit log state
  const [auditLog, setAuditLog] = useState<AuditLog | null>(null)
  const [auditLoading, setAuditLoading] = useState(false)
  const [auditError, setAuditError] = useState<string | null>(null)

  useEffect(() => {
    setReportError(null) // Clear any previous errors when loading new evaluation
    setAutoGenerationAttempted(false) // Reset for new evaluation
    // Set initial view mode based on whether AI report exists
    const generatedReport = (evaluation as any)?.generated_report
    const hasLegacyReport = evaluation.task_executions?.find(t =>
      t.task_name === 'gemini_report_generation' && (t.result_data?.raw_output || t.result_data?.full_output)
    )
    if (generatedReport?.report_content || hasLegacyReport || (evaluation as any)?.gemini_report) {
      setViewMode('ai')
    } else {
      setViewMode('crewai')
    }
    loadGeminiReport()
  }, [evaluation.id])

  // Poll for backend-generated report when evaluation completes; don't auto-generate client-side
  useEffect(() => {
    const completed = (evaluation.status === 'COMPLETED' || evaluation.overall_status === 'COMPLETED')
    if (!completed) return
    if (geminiReport || generatingReport) return
    if (!evaluation.task_executions || evaluation.task_executions.length === 0) return

    let attempts = 0
    const maxAttempts = 18 // ~90s @ 5s interval
    setPollingForReport(true)
    const interval = setInterval(async () => {
      attempts += 1
      await loadGeminiReport()
      if (geminiReport) {
        clearInterval(interval)
        setPollingForReport(false)
        return
      }
      if (attempts >= maxAttempts) {
        clearInterval(interval)
        setPollingForReport(false)
      }
    }, 5000)

    return () => {
      clearInterval(interval)
      setPollingForReport(false)
    }
  }, [evaluation.status, evaluation.overall_status, evaluation.id, geminiReport, generatingReport, evaluation.task_executions?.length])

  // Simple refresh when evaluation data changes
  useEffect(() => {
    if (evaluation.status === 'COMPLETED' || evaluation.overall_status === 'COMPLETED') {
      console.log('📄 Evaluation completed, refreshing report data')
      loadGeminiReport()
    }
  }, [evaluation.status, evaluation.overall_status, evaluation.id])

  // Load audit log when switching to audit view
  useEffect(() => {
    if (viewMode === 'audit' && !auditLog && !auditLoading) {
      loadAuditLog()
    }
  }, [viewMode])

  const loadAuditLog = async () => {
    setAuditLoading(true)
    setAuditError(null)

    try {
      console.log('📋 Loading audit log for:', evaluation.id)

      // First try to get existing audit log
      const getResponse = await fetch(
        `${getApiBase()}/api/evaluations/${evaluation.id}/audit`
      )

      if (getResponse.ok) {
        const data = await getResponse.json()
        if (data.success !== false) {
          setAuditLog(data)
          console.log('📋 Loaded existing audit log')
          return
        }
      }

      // If no existing audit, generate one
      console.log('📋 No existing audit found, generating...')
      const postResponse = await fetch(
        `${getApiBase()}/api/evaluations/${evaluation.id}/audit`,
        { method: 'POST' }
      )

      if (!postResponse.ok) {
        throw new Error(`Failed to generate audit: ${postResponse.status}`)
      }

      const data = await postResponse.json()
      if (data.success) {
        setAuditLog(data)
        console.log('📋 Generated new audit log')
      } else {
        throw new Error(data.warning || 'Failed to generate audit')
      }
    } catch (error: any) {
      console.error('❌ Error loading audit log:', error)
      setAuditError(error.message || 'Failed to load audit log')
    } finally {
      setAuditLoading(false)
    }
  }

  const regenerateAuditLog = async () => {
    setAuditLog(null)
    await loadAuditLog()
  }

  const loadGeminiReport = async () => {
    try {
      console.log('📄 Loading report for evaluation:', evaluation.tld_string)

      // Clear any previous error when attempting to load
      setReportError(null)

      // Check if there's an existing generated report in the evaluation prop
      const generatedReport = (evaluation as any)?.generated_report

      if (generatedReport?.report_content) {
        setGeminiReport(generatedReport.report_content)
        setReportError(null)
        console.log('📄 Loaded AI report from generated_report field')
        return
      }

      // Fallback: Check for legacy Gemini report in task executions
      const geminiReportTask = evaluation.task_executions?.find(task =>
        task.task_name === 'gemini_report_generation'
      )

      if (geminiReportTask?.result_data?.raw_output || geminiReportTask?.result_data?.full_output) {
        setGeminiReport(geminiReportTask.result_data.raw_output || geminiReportTask.result_data.full_output)
        setReportError(null)
        console.log('📄 Loaded AI report from task execution (legacy)')
        return
      }

      if ((evaluation as any)?.gemini_report) {
        setGeminiReport((evaluation as any).gemini_report)
        setReportError(null)
        console.log('📄 Loaded AI report from legacy column')
        return
      }

      // No existing report found — just clear the data, don't touch viewMode
      setGeminiReport('')
      console.log('📄 No AI report found')
    } catch (error) {
      console.error('Error loading Gemini report:', error)
      setReportError('Failed to load report')
    }
  }

  const generateGeminiReport = async () => {
    setGeneratingReport(true)
    setReportError(null)
    setPollingForReport(false) // Stop any ongoing polling
    
    try {
      console.log('🤖 Manually generating AI report for:', evaluation.tld_string)
      
      // Call the CrewAI service report generation endpoint
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 240000) // 4 minute timeout (backend needs 3 minutes)
      
      const response = await fetch(`${getApiBase()}/reports/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          tld_string: evaluation.tld_string,
          evaluation_data: {
            task_executions: evaluation.task_executions || []
          },
          create_google_doc: false
        }),
        signal: controller.signal
      })
      
      clearTimeout(timeoutId)

      if (!response.ok) {
        const errorText = await response.text()
        console.error('❌ Report generation failed:', response.status, errorText)
        throw new Error(`Failed to generate report: ${response.status}`)
      }

      const result = await response.json()
      
      console.log('🔍 Raw API response:', {
        status: response.status,
        success: result.success,
        hasReport: !!result.report,
        reportLength: result.report ? result.report.length : 0,
        error: result.error
      })
      
      if (result.success && result.report) {
        setGeminiReport(result.report)
        setViewMode('ai') // Automatically switch to AI report view
        setReportError(null) // Clear any previous errors
        console.log('✅ Manual report generation successful')
      } else {
        console.error('❌ Report generation result details:', result)
        throw new Error(`Report generation failed: ${result.error || 'No content returned'}`)
      }
    } catch (error) {
      console.error('Error generating Gemini report:', error)
      if (error instanceof Error && error.name === 'AbortError') {
        setReportError('Report generation timed out. Please try again.')
      } else {
        setReportError('Failed to generate report. Please try again.')
      }
    } finally {
      setGeneratingReport(false)
    }
  }

  const generateCrewAIMarkdown = () => {
    const completedTasks = evaluation.task_executions?.filter(task => task.status === 'COMPLETED') || []
    
    if (completedTasks.length === 0) {
      return "# No Completed Tasks\n\nNo evaluation tasks have been completed yet."
    }

    // Simply concatenate all the CrewAI task outputs as one flowing document
    let markdown = ``
    
    completedTasks.forEach((task) => {
      const taskContent = getTaskOutputContent(task)
      
      // Just add the raw CrewAI markdown output directly
      if (taskContent && taskContent.trim() !== 'No output available') {
        markdown += taskContent + '\n\n'
      }
    })

    return markdown.trim()
  }

  const downloadReport = () => {
    let content: string
    let filename: string

    if (viewMode === 'audit' && auditLog?.markdown) {
      content = auditLog.markdown
      filename = `audit-log-${evaluation.tld_string}.md`
    } else if (viewMode === 'ai' && geminiReport) {
      content = geminiReport
      filename = `ai-report-${evaluation.tld_string}.md`
    } else {
      content = generateCrewAIMarkdown()
      filename = `crewai-evaluation-${evaluation.tld_string}.md`
    }

    const blob = new Blob([content], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const getTaskOutputContent = (task: any) => {
    // Try to get formatted output from different sources in order of preference
    if (task.result_data?.output) {
      return task.result_data.output
    }
    if (task.result_data?.raw_output) {
      return task.result_data.raw_output
    }
    if (task.result_data?.full_output) {
      return task.result_data.full_output
    }

    if (task.result && typeof task.result === 'string') {
      return task.result
    }
    if (task.result && typeof task.result === 'object') {
      return JSON.stringify(task.result, null, 2)
    }
    return 'No output available'
  }


  const completedTasks = evaluation.task_executions?.filter(task => task.status === 'COMPLETED') || []
  


  // Determine what content to show based on view mode
  const getMarkdownContent = () => {
    if (viewMode === 'ai' && geminiReport) {
      // Return raw Gemini content without any template formatting
      return geminiReport
    }
    const crewaiContent = generateCrewAIMarkdown()
    return `# 🔧 CrewAI Raw Analysis Output\n\n${crewaiContent}`
  }
  
  const markdownContent = getMarkdownContent()
  
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <CardTitle className="flex items-center space-x-2">
              <FileText className="w-5 h-5" />
              <span>Evaluation Report</span>
              {viewMode === 'ai' && geminiReport && (
                <Badge variant="secondary" className="ml-2">🤖 AI Generated Report</Badge>
              )}
              {viewMode === 'crewai' && (
                <Badge variant="outline" className="ml-2">🔧 CrewAI Raw Output</Badge>
              )}
              {viewMode === 'audit' && (
                <Badge variant="outline" className="ml-2">
                  <ClipboardCheck className="w-3 h-3 mr-1" />
                  Audit Log
                </Badge>
              )}
            </CardTitle>
            
            {/* View Mode Toggle Buttons */}
            {completedTasks.length > 0 && (
              <div className="flex items-center bg-gray-100 rounded-lg p-1">
                <Button
                  variant={viewMode === 'audit' ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => setViewMode('audit')}
                  className="px-3 py-1 h-8"
                >
                  <ClipboardCheck className="w-4 h-4 mr-1" />
                  Audit
                </Button>
                <Button
                  variant={viewMode === 'crewai' ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => setViewMode('crewai')}
                  className="px-3 py-1 h-8"
                >
                  <Code className="w-4 h-4 mr-1" />
                  Raw Output
                </Button>
                <Button
                  variant={viewMode === 'ai' ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => setViewMode('ai')}
                  className="px-3 py-1 h-8"
                >
                  <BookOpen className="w-4 h-4 mr-1" />
                  Report
                </Button>
              </div>
            )}
          </div>
          <div className="flex items-center space-x-2">
            {/* Generate AI Report Button */}
            {!geminiReport && !generatingReport && completedTasks.length > 0 && viewMode === 'ai' && (
              <Button onClick={generateGeminiReport} variant="outline" size="sm">
                <Sparkles className="w-4 h-4 mr-2" />
                Generate AI Report
              </Button>
            )}
            
            {/* Regenerate Button */}
            {geminiReport && (
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={generateGeminiReport}
                disabled={generatingReport}
              >
                <Sparkles className="w-4 h-4 mr-2" />
                Regenerate
              </Button>
            )}
            
            {/* Download Button */}
            <Button variant="outline" size="sm" onClick={downloadReport}>
              <Download className="w-4 h-4 mr-2" />
              Download
            </Button>
          </div>
        </div>
        
        {/* Status Messages */}
        {reportError && (
          <div className="bg-red-50 border border-red-200 rounded-md p-3 mt-4">
            <p className="text-red-800 text-sm">{reportError}</p>
          </div>
        )}
        
        {generatingReport && (
          <div className="bg-blue-50 border border-blue-200 rounded-md p-3 mt-4">
            <div className="flex items-center space-x-2">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500"></div>
              <p className="text-blue-800 text-sm">Generating AI report...</p>
            </div>
          </div>
        )}
        
      </CardHeader>
      
      <CardContent>
        {completedTasks.length === 0 ? (
          <div className="text-center py-12">
            <FileText className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 mb-2">No Tasks Completed</h3>
            <p className="text-gray-600">
              Task results will appear here as the evaluation progresses.
            </p>
          </div>
        ) : viewMode === 'audit' ? (
          // Audit Log View
          <div className="bg-white">
            {auditLoading ? (
              <div className="text-center py-12">
                <RefreshCw className="w-16 h-16 text-green-300 mx-auto mb-4 animate-spin" />
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Loading Audit Log</h3>
                <p className="text-gray-600">Generating task-by-task audit narrative...</p>
              </div>
            ) : auditError ? (
              <div className="text-center py-12">
                <ClipboardCheck className="w-16 h-16 text-red-300 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Audit Log Error</h3>
                <p className="text-gray-600 mb-4">{auditError}</p>
                <Button onClick={regenerateAuditLog} variant="outline">
                  <RefreshCw className="w-4 h-4 mr-2" />
                  Retry
                </Button>
              </div>
            ) : auditLog ? (
              <div className="max-w-4xl mx-auto">
                {/* Compact Workflow Status Summary */}
                <div className="mb-6 bg-gray-50 border border-gray-200 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-medium text-gray-700">Workflow Status</span>
                      <span className="text-sm text-gray-500">
                        {auditLog.total_tasks} tasks completed across{' '}
                        {Object.keys(auditLog.workflow_summaries || {}).length} workflows
                      </span>
                    </div>
                    {(() => {
                      const issues = auditLog.audit_log?.integrity_issues || auditLog.integrity_issues || []
                      const criticals = issues.filter((i: IntegrityIssue) => i.severity === 'CRITICAL')
                      const warnings = issues.filter((i: IntegrityIssue) => i.severity === 'WARNING')
                      if (criticals.length > 0) {
                        return (
                          <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200">
                            {criticals.length} issue(s) need attention
                          </Badge>
                        )
                      }
                      if (warnings.length > 0) {
                        return (
                          <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200">
                            {warnings.length} note(s)
                          </Badge>
                        )
                      }
                      return (
                        <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                          All tasks completed
                        </Badge>
                      )
                    })()}
                  </div>
                </div>

                {/* Task Timeline grouped by Workflow */}
                <div className="space-y-4 mb-6">
                  {WORKFLOW_ORDER.map(workflowKey => {
                    const summary = (auditLog.workflow_summaries || {})[workflowKey]
                    if (!summary) return null

                    const tasks = (auditLog.audit_log?.task_narratives || [])
                      .filter((t: TaskNarrative) => t.workflow === workflowKey)

                    return (
                      <div key={workflowKey} className="border border-gray-200 rounded-lg overflow-hidden">
                        {/* Workflow Header */}
                        <div className="bg-gray-50 px-4 py-3 flex items-center justify-between border-b border-gray-200">
                          <div className="flex items-center gap-2">
                            <h4 className="font-medium text-gray-900 text-sm">
                              {WORKFLOW_DISPLAY_NAMES[workflowKey] || workflowKey}
                            </h4>
                            <span className="text-xs text-gray-500">
                              {summary.tasks_completed} task(s)
                              {(summary.total_execution_time_seconds ?? 0) > 0 && (
                                <> &middot; {formatDuration(summary.total_execution_time_seconds)}</>
                              )}
                              {(summary.expected_api_tasks ?? 0) > 0 && summary.total_api_calls > 0 && (
                                <> &middot; {summary.successful_api_calls}/{summary.total_api_calls} API calls</>
                              )}
                              {(summary.expected_api_tasks ?? 0) === 0 && (
                                <> &middot; local analysis</>
                              )}
                            </span>
                          </div>
                          <WorkflowStatusBadge summary={summary} />
                        </div>

                        {/* Task List */}
                        <div className="divide-y divide-gray-100">
                          {tasks.map((task: TaskNarrative) => (
                            <TaskTimelineRow key={task.task_name} task={task} />
                          ))}
                        </div>
                      </div>
                    )
                  })}

                  {/* Render any workflows not in WORKFLOW_ORDER */}
                  {Object.entries(auditLog.workflow_summaries || {})
                    .filter(([key]) => !WORKFLOW_ORDER.includes(key as any))
                    .map(([workflowKey, summary]) => {
                      const tasks = (auditLog.audit_log?.task_narratives || [])
                        .filter((t: TaskNarrative) => t.workflow === workflowKey)

                      return (
                        <div key={workflowKey} className="border border-gray-200 rounded-lg overflow-hidden">
                          <div className="bg-gray-50 px-4 py-3 flex items-center justify-between border-b border-gray-200">
                            <div className="flex items-center gap-2">
                              <h4 className="font-medium text-gray-900 text-sm">
                                {workflowKey.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                              </h4>
                              <span className="text-xs text-gray-500">
                                {summary.tasks_completed} task(s)
                              </span>
                            </div>
                            <WorkflowStatusBadge summary={summary} />
                          </div>
                          <div className="divide-y divide-gray-100">
                            {tasks.map((task: TaskNarrative) => (
                              <TaskTimelineRow key={task.task_name} task={task} />
                            ))}
                          </div>
                        </div>
                      )
                    })}
                </div>

                {/* Notes / Issues section — collapsible */}
                {(() => {
                  const issues = auditLog.audit_log?.integrity_issues || auditLog.integrity_issues || []
                  if (issues.length === 0) return null

                  const criticals = issues.filter((i: IntegrityIssue) => i.severity === 'CRITICAL')
                  const warnings = issues.filter((i: IntegrityIssue) => i.severity === 'WARNING')
                  const infos = issues.filter((i: IntegrityIssue) => i.severity === 'INFO')

                  return (
                    <details className="mb-6 border border-gray-200 rounded-lg" open={criticals.length > 0}>
                      <summary className="px-4 py-3 cursor-pointer text-sm font-medium text-gray-700 hover:bg-gray-50 rounded-lg">
                        {criticals.length > 0
                          ? `${criticals.length} issue(s) and ${warnings.length + infos.length} note(s)`
                          : `${warnings.length + infos.length} note(s)`
                        }
                      </summary>
                      <div className="px-4 pb-4 space-y-2 border-t border-gray-100">
                        {criticals.map((issue: IntegrityIssue, idx: number) => (
                          <div key={`c-${idx}`} className="flex items-start gap-2 text-sm text-red-700 pt-2">
                            <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
                            <span><strong>{issue.task_name.replace(/_/g, ' ')}:</strong> {issue.detail}</span>
                          </div>
                        ))}
                        {warnings.map((issue: IntegrityIssue, idx: number) => (
                          <div key={`w-${idx}`} className="flex items-start gap-2 text-sm text-amber-700 pt-2">
                            <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
                            <span><strong>{issue.task_name.replace(/_/g, ' ')}:</strong> {issue.detail}</span>
                          </div>
                        ))}
                        {infos.map((issue: IntegrityIssue, idx: number) => (
                          <div key={`i-${idx}`} className="flex items-start gap-2 text-sm text-gray-600 pt-2">
                            <Info className="w-4 h-4 mt-0.5 shrink-0" />
                            <span><strong>{issue.task_name.replace(/_/g, ' ')}:</strong> {issue.detail}</span>
                          </div>
                        ))}
                      </div>
                    </details>
                  )
                })()}

                {/* Full Audit Narrative — collapsible */}
                {auditLog.markdown && (
                  <details className="mb-4 border border-gray-200 rounded-lg">
                    <summary className="px-4 py-3 cursor-pointer text-sm font-medium text-gray-700 hover:bg-gray-50 rounded-lg">
                      Full Audit Narrative
                    </summary>
                    <div className="bg-white border-t border-gray-200 rounded-b-lg">
                      <div className="p-8 md:p-12">
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          components={{
                            h1: ({children}) => (
                              <h1 className="text-2xl font-bold text-gray-900 mb-4 pb-3 border-b border-gray-200 leading-tight">
                                {children}
                              </h1>
                            ),
                            h2: ({children}) => (
                              <h2 className="text-xl font-semibold text-gray-800 mt-8 mb-4 leading-snug">
                                {children}
                              </h2>
                            ),
                            h3: ({children}) => (
                              <h3 className="text-lg font-medium text-gray-700 mt-6 mb-3 leading-snug">
                                {children}
                              </h3>
                            ),
                            h4: ({children}) => (
                              <h4 className="text-base font-medium text-gray-700 mt-5 mb-2 leading-snug">
                                {children}
                              </h4>
                            ),
                            p: ({children}) => (
                              <p className="text-gray-700 mb-4 leading-7 text-sm">
                                {children}
                              </p>
                            ),
                            strong: ({children}) => (
                              <strong className="font-semibold text-gray-900">{children}</strong>
                            ),
                            blockquote: ({children}) => (
                              <blockquote className="border-l-3 border-gray-300 pl-4 py-1 my-3 text-gray-600 text-sm">
                                {children}
                              </blockquote>
                            ),
                            hr: () => <hr className="border-gray-200 my-4" />,
                            ul: ({children}) => (
                              <ul className="list-disc pl-6 mb-4 space-y-1">{children}</ul>
                            ),
                            li: ({children}) => (
                              <li className="text-gray-700 text-sm leading-6">{children}</li>
                            ),
                          }}
                        >
                          {auditLog.markdown}
                        </ReactMarkdown>
                      </div>
                    </div>
                  </details>
                )}

                {/* Regenerate button */}
                <div className="mt-4 text-center">
                  <Button onClick={regenerateAuditLog} variant="ghost" size="sm">
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Regenerate Audit Log
                  </Button>
                </div>
              </div>
            ) : (
              <div className="text-center py-12">
                <ClipboardCheck className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-gray-900 mb-2">No Audit Log Available</h3>
                <p className="text-gray-600 mb-4">
                  Generate an audit log to see a task-by-task breakdown of what the evaluation did.
                </p>
                <Button onClick={loadAuditLog} variant="outline">
                  <ClipboardCheck className="w-4 h-4 mr-2" />
                  Generate Audit Log
                </Button>
              </div>
            )}
          </div>
        ) : viewMode === 'ai' && !geminiReport && (generatingReport || pollingForReport) ? (
          <div className="text-center py-12">
            <Sparkles className="w-16 h-16 text-blue-300 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Generating AI Report</h3>
            <p className="text-gray-600 mb-2">Were generating your AI report from the CrewAI results. This can take up to a couple of minutes.</p>
          </div>
        ) : viewMode === 'ai' && !geminiReport && !generatingReport ? (
          <div className="text-center py-12">
            <Sparkles className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 mb-2">No AI Report Generated</h3>
            <p className="text-gray-600 mb-4">
              Generate an AI-powered report to get a comprehensive analysis of your evaluation results.
            </p>
            <Button onClick={generateGeminiReport} variant="outline">
              <Sparkles className="w-4 h-4 mr-2" />
              Generate AI Report
            </Button>
          </div>
        ) : (
          <div className="bg-white">
            {/* Document-style container with better typography */}
            <div className="max-w-4xl mx-auto bg-white shadow-sm border border-gray-200 rounded-lg">
              <div className="p-8 md:p-12">
                <ReactMarkdown 
                  remarkPlugins={[remarkGfm]}
                  components={{
                    // Document-style heading with proper hierarchy
                    h1: ({children}) => (
                      <h1 className="text-3xl font-bold text-gray-900 mb-6 pb-4 border-b-2 border-gray-200 leading-tight">
                        {children}
                      </h1>
                    ),
                    h2: ({children}) => (
                      <h2 className="text-2xl font-semibold text-gray-800 mt-10 mb-5 leading-snug">
                        {children}
                      </h2>
                    ),
                    h3: ({children}) => (
                      <h3 className="text-xl font-medium text-gray-700 mt-8 mb-4 leading-snug">
                        {children}
                      </h3>
                    ),
                    h4: ({children}) => (
                      <h4 className="text-lg font-medium text-gray-700 mt-6 mb-3 leading-snug">
                        {children}
                      </h4>
                    ),
                    // Document-style paragraphs with proper spacing
                    p: ({children}) => (
                      <p className="text-gray-700 mb-5 leading-7 text-base">
                        {children}
                      </p>
                    ),
                    // Enhanced emphasis styling
                    strong: ({children}) => (
                      <strong className="font-semibold text-gray-900">{children}</strong>
                    ),
                    em: ({children}) => (
                      <em className="italic text-gray-800">{children}</em>
                    ),
                    // Code styling for technical content
                    code: ({children}) => (
                      <code className="bg-gray-100 text-gray-800 px-2 py-1 rounded text-sm font-mono border">
                        {children}
                      </code>
                    ),
                    pre: ({children}) => (
                      <pre className="bg-gray-50 border border-gray-200 rounded-lg p-6 overflow-x-auto mb-6 text-sm">
                        {children}
                      </pre>
                    ),
                    // Professional blockquote styling
                    blockquote: ({children}) => (
                      <blockquote className="border-l-4 border-blue-500 pl-6 py-2 my-6 bg-blue-50 italic text-gray-700 rounded-r">
                        {children}
                      </blockquote>
                    ),
                    // Clean separator
                    hr: () => <hr className="border-gray-200 my-10" />,
                    // Well-spaced lists
                    ul: ({children}) => (
                      <ul className="list-disc pl-8 mb-6 space-y-2">{children}</ul>
                    ),
                    ol: ({children}) => (
                      <ol className="list-decimal pl-8 mb-6 space-y-2">{children}</ol>
                    ),
                    li: ({children}) => (
                      <li className="text-gray-700 leading-6">{children}</li>
                    ),
                    // Table styling for structured data
                    table: ({children}) => (
                      <div className="overflow-x-auto mb-6">
                        <table className="min-w-full border border-gray-200 rounded-lg">
                          {children}
                        </table>
                      </div>
                    ),
                    thead: ({children}) => (
                      <thead className="bg-gray-50">{children}</thead>
                    ),
                    th: ({children}) => (
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-b border-gray-200">
                        {children}
                      </th>
                    ),
                    td: ({children}) => (
                      <td className="px-6 py-4 text-sm text-gray-700 border-b border-gray-200">
                        {children}
                      </td>
                    ),
                  }}
                >
                  {markdownContent}
                </ReactMarkdown>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}