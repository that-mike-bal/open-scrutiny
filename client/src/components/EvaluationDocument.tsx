import { useState, useEffect } from 'react'
import { getApiBase } from '@/lib/api-config'
import { getTldEvaluationsByString } from '../lib/supabase-api'
import { Button } from './ui/button'
import { Download, FileText, Sparkles, ExternalLink } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface TaskExecution {
  id: string
  task_name?: string
  task_display_name?: string
  result_status?: string
  status?: string
  agent_name?: string
  execution_time_seconds?: number
  completed_at?: string
  raw_output?: string
  result_data?: {
    output?: string
    raw_output?: string
    [key: string]: any
  }
  tools_used?: string[]
  confidence_score?: number
}

interface TldEvaluationWithAnalysis {
  id: string
  tld_string: string
  status?: string
  created_at: string
  use_case?: string
  workflow_type?: string
  task_executions?: TaskExecution[]
}

interface EvaluationDocumentProps {
  evaluation: TldEvaluationWithAnalysis
}

export default function EvaluationDocument({ evaluation }: EvaluationDocumentProps) {
  const [allEvaluations, setAllEvaluations] = useState<TldEvaluationWithAnalysis[]>([])
  const [loading, setLoading] = useState(true)
  const [taskOutputs, setTaskOutputs] = useState<Record<string, string>>({})
  const [loadingOutputs, setLoadingOutputs] = useState<Record<string, boolean>>({})
  const [documentContent, setDocumentContent] = useState<string>('')
  const [generatingPreview, setGeneratingPreview] = useState(false)
  const [generatingReport, setGeneratingReport] = useState(false)
  const [geminiReport, setGeminiReport] = useState<string>('')
  const [googleDocUrl, setGoogleDocUrl] = useState<string | null>(null)
  const [googleDocsEnabled, setGoogleDocsEnabled] = useState(false)
  const [viewMode, setViewMode] = useState<'markdown' | 'report'>('markdown')

  useEffect(() => {
    loadAllEvaluations()
  }, [evaluation.tld_string])

  useEffect(() => {
    if (!loading) {
      generatePreview()
    }
  }, [allEvaluations, loading]) // eslint-disable-line react-hooks/exhaustive-deps

  const loadAllEvaluations = async () => {
    try {
      setLoading(true)
      // Use direct Supabase API function
      const allEvals = await getTldEvaluationsByString(evaluation.tld_string)
      setAllEvaluations(allEvals.length > 0 ? allEvals : [evaluation])
      
      // Check if there's an existing generated report in the generated_report field
      const evaluationWithReport = allEvals.length > 0 ? allEvals[0] : evaluation
      const generatedReport = (evaluationWithReport as any)?.generated_report
      
      if (generatedReport?.report_content) {
        setGeminiReport(generatedReport.report_content)
        console.log('📄 Loaded AI report from generated_report field')
      } else {
        // Fallback: Check for legacy Gemini report in task executions
        const taskExecutions = evaluationWithReport?.task_executions || []
        const geminiReportTask = taskExecutions.find((task: TaskExecution) => 
          task.task_name === 'gemini_report_generation'
        )
        
        if (geminiReportTask?.result_data?.raw_output || geminiReportTask?.result_data?.full_output) {
          setGeminiReport(geminiReportTask.result_data.raw_output || geminiReportTask.result_data.full_output)
          console.log('📄 Loaded AI report from task execution (legacy)')
        } else if ((evaluationWithReport as any)?.gemini_report) {
          // Fallback to legacy column if it exists
          setGeminiReport((evaluationWithReport as any).gemini_report)
          console.log('📄 Loaded AI report from legacy column')
        }
      }
    } catch (error) {
      console.error('Error loading all evaluations:', error)
      setAllEvaluations([evaluation])
    } finally {
      setLoading(false)
    }
  }

  // Load detailed markdown output for a task
  const loadTaskOutput = async (taskName: string, tldString: string): Promise<string> => {
    const cacheKey = `${taskName}_${tldString}`
    
    if (taskOutputs[cacheKey]) {
      return taskOutputs[cacheKey]
    }

    if (loadingOutputs[cacheKey]) {
      return 'Loading detailed content...'
    }

    setLoadingOutputs(prev => ({ ...prev, [cacheKey]: true }))

    try {
      // Use the standardized Next.js API route instead of direct CrewAI call
      const response = await fetch(`/api/outputs/${taskName}_${tldString}.md`)
      if (response.ok) {
        const content = await response.text()
        setTaskOutputs(prev => ({ ...prev, [cacheKey]: content }))
        return content
      } else {
        return `Task completed with status: ${taskName.toUpperCase()}`
      }
    } catch (error) {
      console.error(`Error loading task output for ${taskName}:`, error)
      return `Task completed with status: ${taskName.toUpperCase()}`
    } finally {
      setLoadingOutputs(prev => ({ ...prev, [cacheKey]: false }))
    }
  }

  // Generate a comprehensive markdown document from ALL evaluation data
  const generateMarkdownDocument = async (): Promise<string> => {
    // Aggregate all tasks from all evaluations for this TLD string
    const allTasks = allEvaluations.flatMap(evaluation => evaluation.task_executions || [])
    const tldString = evaluation.tld_string
    const createdAt = new Date(evaluation.created_at).toLocaleDateString()
    const allWorkflowTypes = [...new Set(allEvaluations.map(evaluation => evaluation.workflow_type).filter(Boolean))]
    
    // Define validation task names for proper categorization
    const validationTaskNames = [
      'findings_validation', // Legacy validation task
      'binary_compliance_validation',
      'technical_risk_validation', 
      'legal_risk_validation',
      'policy_safeguard_validation'
    ]
    
    // Group tasks by type - INCLUDE all validation tasks in binary gates
    const binaryGates = allTasks.filter((task: TaskExecution) => 
      ['iana_database_check', 'blocked_names_check', 'reserved_names_check', ...validationTaskNames].includes(task.task_name || '')
    )
    const analysisTask = allTasks.find((task: TaskExecution) => task.task_name === 'string_analysis')
    
    // Categorize risk assessment tasks
    const riskAssessmentTasks = allTasks.filter((task: TaskExecution) => 
      ![...['iana_database_check', 'blocked_names_check', 'reserved_names_check', 'string_analysis'], ...validationTaskNames].includes(task.task_name || '')
    )
    
    // Calculate overall execution stats
    const totalTasks = allTasks.length
    const completedTasks = allTasks.filter(task => task.status === 'COMPLETED').length
    const passedTasks = allTasks.filter(task => task.result_status === 'PASS').length
    const failedTasks = allTasks.filter(task => task.result_status === 'FAIL' || task.result_status === 'BLOCKED').length
    const avgConfidence = allTasks.reduce((sum, task) => sum + (task.confidence_score || 0), 0) / allTasks.length
    const totalExecutionTime = allTasks.reduce((sum, task) => sum + (task.execution_time_seconds || 0), 0)
    
    // Get unique agents used
    const uniqueAgents = [...new Set(allTasks.map(task => task.agent_name).filter(Boolean))]
    
    // Get unique tools used
    const uniqueTools = [...new Set(allTasks.flatMap(task => task.tools_used || []))]
    
    // Categorize policy assessment tasks  
    const policyTasks = allTasks.filter((task: TaskExecution) => 
      ['gac_risk_analysis', 'safeguard_assessment', 'geographic_name_assessment', 'global_trademark_assessment'].includes(task.task_name || '')
    )
    
    // Define all categorized task names for filtering
    const categorizedTaskNames = [
      'iana_database_check', 'blocked_names_check', 'reserved_names_check', 'string_analysis',
      'dns_stability_review', 'name_collision_assessment', 'comprehensive_similarity_analysis',
      'gac_risk_analysis', 'safeguard_assessment', 'geographic_name_assessment', 'global_trademark_assessment',
      ...validationTaskNames
    ]
    
    // Any remaining tasks not categorized above
    const otherTasks = allTasks.filter((task: TaskExecution) => 
      !categorizedTaskNames.includes(task.task_name || '')
    )

    let document = `# TLD Evaluation Report: .${tldString}

**Evaluation Date:** ${createdAt}  
**Use Case:** ${evaluation.use_case || 'Not specified'}  
**Comprehensive Analysis:** All Workflow Types  
**Total Tasks:** ${allTasks.length}

---

## Executive Summary

This report presents the comprehensive evaluation results for the proposed Top-Level Domain (TLD) string ".${tldString}". The evaluation covers technical compliance, policy adherence, and risk assessment according to ICANN guidelines and industry best practices.

## Evaluation Overview

**Total Tasks Executed:** ${totalTasks}  
**Completed Tasks:** ${completedTasks}  
**Passed Tasks:** ${passedTasks}  
**Failed/Blocked Tasks:** ${failedTasks}  
**Average Confidence Score:** ${avgConfidence.toFixed(2)}%  
**Total Execution Time:** ${Math.round(totalExecutionTime)}s  

**Workflows Analyzed:** ${allWorkflowTypes.join(', ')}  

**AI Agents Used:** ${uniqueAgents.length > 0 ? uniqueAgents.join(', ') : 'N/A'}  

**Tools Utilized:** ${uniqueTools.length > 0 ? uniqueTools.join(', ') : 'N/A'}  

---

## Task Execution Summary

The following table provides a comprehensive overview of all tasks executed during the evaluation:

| Task | Status | Agent | Confidence | Duration | Tools Used |
|------|--------|-------|------------|----------|------------|
${allTasks.map(task => {
  const status = task.result_status === 'PASS' ? '✅ PASS' : 
                task.result_status === 'BLOCKED' ? '❌ BLOCKED' : 
                task.result_status === 'FAIL' ? '❌ FAIL' : 
                task.result_status === 'REVIEW_REQUIRED' ? '⚠️ REVIEW' : '⚠️ PENDING'
  const taskName = task.task_display_name || getTaskDisplayName(task.task_name || '')
  const agent = task.agent_name || 'System'
  const confidence = task.confidence_score ? `${(task.confidence_score * 100).toFixed(1)}%` : 'N/A'
  const duration = task.execution_time_seconds ? `${task.execution_time_seconds}s` : 'N/A'
  const tools = task.tools_used?.join(', ') || 'N/A'
  
  return `| ${taskName} | ${status} | ${agent} | ${confidence} | ${duration} | ${tools} |`
}).join('\n')}

---

**Analysis Coverage:**
- Binary Compliance Gates (IANA, Blocked Names, Reserved Names, Findings Validation)
- Technical Risk Assessment (DNS Stability, Name Collision, Similarity Analysis)  
- Legal Risk Assessment (Trademark, Geographic Names)
- Policy Safeguard Review (GAC Risk, Safeguards)

---

## Binary Compliance Gates

The following critical compliance checks determine whether the TLD string can proceed to application:

`

    // Add binary gate results with enhanced content loading
    for (const task of binaryGates) {
      const status = task.result_status === 'PASS' ? '✅ PASS' : 
                    task.result_status === 'BLOCKED' ? '❌ BLOCKED' : 
                    task.result_status === 'FAIL' ? '❌ FAIL' : '⚠️ PENDING'
      
      const taskDisplayName = task.task_display_name || getTaskDisplayName(task.task_name || '')
      
      document += `### ${taskDisplayName}

**Status:** ${status}  
**Agent:** ${task.agent_name || 'System'}  
**Confidence Score:** ${task.confidence_score ? `${(task.confidence_score * 100).toFixed(1)}%` : 'N/A'}  
**Execution Time:** ${task.execution_time_seconds ? `${task.execution_time_seconds}s` : 'N/A'}  
**Completed:** ${task.completed_at ? new Date(task.completed_at).toLocaleString() : 'Pending'}  
**Tools Used:** ${task.tools_used?.join(', ') || 'N/A'}

`
      
      // Try to get detailed output from result_data
      let taskOutput = task.result_data?.raw_output || 
                      task.result_data?.full_output ||
                      task.result_data?.output

      if (!taskOutput && task.task_name) {
        // Load from markdown file if database content is missing
        taskOutput = await loadTaskOutput(task.task_name, tldString)
      }
      
      if (taskOutput && taskOutput.trim()) {
        document += `${taskOutput}

`
      } else {
        document += `Task completed with status: ${task.result_status || 'Unknown'}

`
      }
      
      document += '---\n\n'
    }

    // Add string analysis section if available
    if (analysisTask) {
      document += `## Technical String Analysis

**Status:** ${analysisTask.result_status ? 
  (analysisTask.result_status === 'PASS' ? '✅ PASS' : 
   analysisTask.result_status === 'BLOCKED' ? '❌ BLOCKED' : 
   analysisTask.result_status === 'FAIL' ? '❌ FAIL' : '⚠️ PENDING') : 'N/A'}  
**Agent:** ${analysisTask.agent_name || 'System'}  
**Confidence Score:** ${analysisTask.confidence_score ? `${(analysisTask.confidence_score * 100).toFixed(1)}%` : 'N/A'}  
**Execution Time:** ${analysisTask.execution_time_seconds ? `${analysisTask.execution_time_seconds}s` : 'N/A'}  
**Completed:** ${analysisTask.completed_at ? new Date(analysisTask.completed_at).toLocaleString() : 'Pending'}  
**Tools Used:** ${analysisTask.tools_used?.join(', ') || 'N/A'}

`
      
      // Get detailed output
      let analysisOutput = analysisTask.raw_output || 
                          analysisTask.result_data?.raw_output || 
                          analysisTask.result_data?.output

      if (!analysisOutput && analysisTask.task_name) {
        analysisOutput = await loadTaskOutput(analysisTask.task_name, tldString)
      }
      
      if (analysisOutput && analysisOutput.trim()) {
        document += `${analysisOutput}

`
      } else {
        document += `Task completed with status: ${analysisTask.result_status || 'Unknown'}

`
      }
      
      // Add tools used if available
      if (analysisTask.tools_used && analysisTask.tools_used.length > 0) {
        document += `**Tools Used:** ${analysisTask.tools_used.join(', ')}

`
      }
      
      document += '---\n\n'
    }

    // Add risk assessment section with enhanced content loading
    if (riskAssessmentTasks.length > 0) {
      document += `## Risk Assessment Analysis

`
      for (const task of riskAssessmentTasks) {
        const taskDisplayName = task.task_display_name || getTaskDisplayName(task.task_name || '')
        const status = task.result_status === 'PASS' ? '✅ PASS' : 
                      task.result_status === 'BLOCKED' ? '❌ BLOCKED' : 
                      task.result_status === 'FAIL' ? '❌ FAIL' : 
                      task.result_status === 'REVIEW_REQUIRED' ? '⚠️ REVIEW' : '⚠️ PENDING'
        
        document += `### ${taskDisplayName}

**Status:** ${status}  
**Agent:** ${task.agent_name || 'System'}  
**Confidence Score:** ${task.confidence_score ? `${(task.confidence_score * 100).toFixed(1)}%` : 'N/A'}  
**Execution Time:** ${task.execution_time_seconds ? `${task.execution_time_seconds}s` : 'N/A'}  
**Completed:** ${task.completed_at ? new Date(task.completed_at).toLocaleString() : 'Pending'}  
**Tools Used:** ${task.tools_used?.join(', ') || 'N/A'}

`
        
        // Get detailed output
        let taskOutput = task.raw_output || 
                        task.result_data?.raw_output || 
                        task.result_data?.output

        if (!taskOutput && task.task_name) {
          taskOutput = await loadTaskOutput(task.task_name, tldString)
        }
        
        if (taskOutput && taskOutput.trim()) {
          document += `${taskOutput}

`
        } else {
          document += `Task completed with status: ${task.result_status || 'Unknown'}

`
        }
        
        // Add tools used if available
        if (task.tools_used && task.tools_used.length > 0) {
          document += `**Tools Used:** ${task.tools_used.join(', ')}

`
        }
        
        document += '---\n\n'
      }
    }

    // Add policy assessment section
    if (policyTasks.length > 0) {
      document += `## Policy Assessment Analysis

`
      for (const task of policyTasks) {
        const taskDisplayName = task.task_display_name || getTaskDisplayName(task.task_name || '')
        const status = task.result_status === 'PASS' ? '✅ PASS' : 
                      task.result_status === 'BLOCKED' ? '❌ BLOCKED' : 
                      task.result_status === 'FAIL' ? '❌ FAIL' : 
                      task.result_status === 'REVIEW_REQUIRED' ? '⚠️ REVIEW' : '⚠️ PENDING'
        
        document += `### ${taskDisplayName}

**Status:** ${status}  
**Agent:** ${task.agent_name || 'System'}  
**Confidence Score:** ${task.confidence_score ? `${(task.confidence_score * 100).toFixed(1)}%` : 'N/A'}  
**Execution Time:** ${task.execution_time_seconds ? `${task.execution_time_seconds}s` : 'N/A'}  
**Completed:** ${task.completed_at ? new Date(task.completed_at).toLocaleString() : 'Pending'}  
**Tools Used:** ${task.tools_used?.join(', ') || 'N/A'}

`
        
        // Get detailed output
        let taskOutput = task.raw_output || 
                        task.result_data?.raw_output || 
                        task.result_data?.output

        if (!taskOutput && task.task_name) {
          taskOutput = await loadTaskOutput(task.task_name, tldString)
        }
        
        if (taskOutput && taskOutput.trim()) {
          document += `${taskOutput}

`
        } else {
          document += `Task completed with status: ${task.result_status || 'Unknown'}

`
        }
        
        // Add tools used if available
        if (task.tools_used && task.tools_used.length > 0) {
          document += `**Tools Used:** ${task.tools_used.join(', ')}

`
        }
        
        document += '---\n\n'
      }
    }

    // Add other assessments
    if (otherTasks.length > 0) {
      document += `## Additional Assessments

`
      for (const task of otherTasks) {
        const taskDisplayName = task.task_display_name || getTaskDisplayName(task.task_name || '')
        document += `### ${taskDisplayName}

**Status:** ${task.result_status || 'Pending'}  
**Agent:** ${task.agent_name || 'System'}  
**Execution Time:** ${task.execution_time_seconds ? `${task.execution_time_seconds}s` : 'N/A'}  
**Completed:** ${task.completed_at ? new Date(task.completed_at).toLocaleString() : 'Pending'}

`
        
        // Get detailed output
        let taskOutput = task.raw_output || 
                        task.result_data?.raw_output || 
                        task.result_data?.output

        if (!taskOutput && task.task_name) {
          taskOutput = await loadTaskOutput(task.task_name, tldString)
        }
        
        if (taskOutput && taskOutput.trim()) {
          document += `${taskOutput}

`
        } else {
          document += `Task completed with status: ${task.result_status || 'Unknown'}

`
        }
        
        // Add tools used if available
        if (task.tools_used && task.tools_used.length > 0) {
          document += `**Tools Used:** ${task.tools_used.join(', ')}

`
        }
        
        document += '---\n\n'
      }
    }

    // Add conclusion
    const overallStatus = binaryGates.every((task: TaskExecution) => task.result_status === 'PASS') ? 
      'CLEARED FOR APPLICATION' : 
      binaryGates.some((task: TaskExecution) => task.result_status === 'BLOCKED') ? 
      'BLOCKED - CANNOT PROCEED' : 
      'REQUIRES REVIEW'

    document += `## Conclusion

**Overall Status:** ${overallStatus}

Based on the comprehensive evaluation conducted, the TLD string ".${tldString}" has ${overallStatus === 'CLEARED FOR APPLICATION' ? 'successfully passed all critical compliance gates and is ready for ICANN application submission' : overallStatus === 'BLOCKED - CANNOT PROCEED' ? 'failed one or more critical compliance requirements and cannot proceed to application' : 'completed evaluation with results requiring expert review before proceeding'}.

### Next Steps

${overallStatus === 'CLEARED FOR APPLICATION' ? 
  '- Proceed with ICANN gTLD application preparation\n- Compile supporting documentation\n- Prepare application fee and technical specifications' :
  overallStatus === 'BLOCKED - CANNOT PROCEED' ?
  '- Review blocking issues identified in the evaluation\n- Consider alternative TLD strings\n- Address policy conflicts if possible' :
  '- Expert review of flagged items\n- Additional documentation may be required\n- Stakeholder consultation recommended'
}

---

**Report Generated:** ${new Date().toLocaleString()}  
**Total Evaluations Included:** ${allEvaluations.length}  
**Workflow Types:** ${allWorkflowTypes.join(', ') || 'Not specified'}
`

    return document
  }

  // Helper function to get display names
  const getTaskDisplayName = (taskName: string): string => {
    const displayNames: Record<string, string> = {
      // Legacy binary compliance tasks
      'iana_database_check': 'IANA Database Check',
      'blocked_names_check': 'Blocked Names Check', 
      'reserved_names_check': 'Reserved Names Check',
      'findings_validation': 'Findings Validation (Legacy)',
      'binary_compliance_validation': 'Binary Compliance Validation',
      'string_analysis': 'Technical String Analysis',
      
      // Technical Risk Assessment Workflow Tasks
      'dns_stability_review': 'DNS Stability Review',
      'name_collision_assessment': 'Name Collision Assessment',
      'comprehensive_similarity_analysis': 'Comprehensive Similarity Analysis',
      'technical_risk_validation': 'Technical Risk Validation',
      
      // Legal Risk Assessment Workflow Tasks  
      'global_trademark_assessment': 'Global Trademark Assessment',
      'patent_conflict_assessment': 'Patent Conflict Assessment',
      'legal_risk_validation': 'Legal Risk Validation',
      
      // Policy Safeguard Review Workflow Tasks
      'geographic_name_assessment': 'Geographic Name Assessment',
      'safeguard_assessment': 'ICANN Safeguard Assessment', 
      'gac_risk_analysis': 'GAC Risk Assessment',
      'cultural_linguistic_assessment': 'Cultural & Linguistic Assessment',
      'policy_safeguard_validation': 'Policy Safeguard Validation'
    }
    return displayNames[taskName] || taskName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
  }

  const downloadDocument = async () => {
    try {
      const content = await generateMarkdownDocument()
      const blob = new Blob([content], { type: 'text/markdown' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `tld_evaluation_${evaluation.tld_string}_${new Date().toISOString().split('T')[0]}.md`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Error downloading document:', error)
      alert('Failed to download document. Please try again.')
    }
  }

  const generatePreview = async () => {
    try {
      setGeneratingPreview(true)
      const content = await generateMarkdownDocument()
      setDocumentContent(content)
    } catch (error) {
      console.error('Error generating preview:', error)
    } finally {
      setGeneratingPreview(false)
    }
  }

  const generateGeminiReport = async () => {
    try {
      setGeneratingReport(true)
      console.log('🎯 Starting Gemini report generation for:', evaluation.tld_string)
      
      // Prepare evaluation data for Gemini - match backend ReportGenerationRequest model
      const requestData = {
        tld_string: evaluation.tld_string,
        evaluation_data: {
          tld_string: evaluation.tld_string,
          use_case: evaluation.use_case || "General purpose TLD",
          workflow_type: evaluation.workflow_type || "comprehensive_evaluation",
          task_executions: allEvaluations.flatMap(evalReport => evalReport.task_executions || []),
          evaluations: allEvaluations
        },
        create_google_doc: true
      }
      
      console.log('📊 Sending request data:', {
        tld_string: requestData.tld_string,
        task_count: requestData.evaluation_data.task_executions.length,
        evaluation_count: requestData.evaluation_data.evaluations.length
      })
      
      // Call the CrewAI service directly for report generation
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 240000) // 4 minute timeout (backend needs 3 minutes)
      
      const response = await fetch(`${getApiBase()}/reports/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData),
        signal: controller.signal
      })
      
      clearTimeout(timeoutId)

      console.log('📡 API response status:', response.status, response.statusText)

      if (response.ok) {
        const result = await response.json()
        console.log('✅ Report generated successfully, length:', result.report?.length || 0)
        
        setGeminiReport(result.report)
        setViewMode('report') // Automatically switch to report view
        setGoogleDocUrl(result.google_doc_url || null)
        setGoogleDocsEnabled(result.google_docs_enabled || false)
        
        console.log('✅ Report generated and automatically saved as task execution')
      } else {
        let errorMessage = 'Failed to generate report'
        try {
          const errorData = await response.json()
          errorMessage = errorData.detail || errorData.message || errorData.error || errorMessage
          console.error('❌ Backend error response:', errorData)
        } catch (parseError) {
          console.error('❌ Failed to parse error response:', parseError)
          errorMessage = `HTTP ${response.status}: ${response.statusText}`
        }
        throw new Error(errorMessage)
      }
    } catch (error) {
      console.error('❌ Error generating Gemini report:', error)
      alert(`Failed to generate report: ${error instanceof Error ? error.message : String(error)}`)
    } finally {
      setGeneratingReport(false)
      console.log('🏁 Report generation process completed')
    }
  }

  const downloadGeminiReport = () => {
    if (!geminiReport) return
    
    // Create a complete HTML document with professional styling and metadata
    const htmlContent = `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>gTLD Feasibility Analysis Report - .${evaluation.tld_string}</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px 20px;
            background: #fff;
        }
        .header {
            text-align: center;
            border-bottom: 3px solid #2563eb;
            padding-bottom: 30px;
            margin-bottom: 40px;
        }
        .metadata {
            background: #f8fafc;
            border-left: 4px solid #3b82f6;
            padding: 20px;
            margin: 30px 0;
            border-radius: 0 8px 8px 0;
        }
        .footer {
            margin-top: 50px;
            padding-top: 30px;
            border-top: 2px solid #e5e7eb;
            text-align: center;
            color: #6b7280;
            font-size: 0.9em;
        }
        @media print {
            body { padding: 20px; }
            .no-print { display: none; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>gTLD Feasibility Analysis Report</h1>
        <h2>Professional Assessment for .${evaluation.tld_string}</h2>
        <p><strong>Generated:</strong> ${new Date().toLocaleDateString()}</p>
    </div>
    
    <div class="metadata">
        <h3>Report Metadata</h3>
        <ul>
            <li><strong>TLD String:</strong> .${evaluation.tld_string}</li>
            <li><strong>Generated:</strong> ${new Date().toLocaleString()}</li>
            <li><strong>Analysis Type:</strong> Comprehensive Multi-Workflow Assessment</li>
            <li><strong>Data Sources:</strong> ICANN databases, trademark registries, GAC precedents</li>
            <li><strong>AI Model:</strong> Gemini 2.0 Flash (Google)</li>
            <li><strong>Service:</strong> CrewAI TLD Evaluation Platform</li>
        </ul>
    </div>
    
    <div class="content">
        ${geminiReport}
    </div>
    
    <div class="footer">
        <p><strong>This report was generated using advanced AI analysis of comprehensive TLD evaluation data.</strong></p>
        <p>All recommendations should be reviewed by qualified legal and technical experts before making application decisions.</p>
        <p><em>CrewAI TLD Evaluation Service - Professional gTLD Feasibility Assessment</em></p>
    </div>
</body>
</html>`
    
    const blob = new Blob([htmlContent], { type: 'text/html' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `gemini_analysis_report_${evaluation.tld_string}_${new Date().toISOString().split('T')[0]}.html`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const hasComprehensiveData = () => {
    // Check if we have completed workflows data
    if (evaluation && 'completed_workflows' in evaluation && Array.isArray(evaluation.completed_workflows)) {
      const completedWorkflows = new Set(evaluation.completed_workflows)
      
      // Define required workflows for a comprehensive report
      // Binary compliance is now done client-side, so we only need the 3 AI workflows
      const requiredWorkflows = [
        'technical_risk_assessment', 
        'legal_risk_assessment',
        'policy_safeguard_review'
      ]
      
      // Check if all required workflows are completed
      const allRequiredCompleted = requiredWorkflows.every(workflow => 
        completedWorkflows.has(workflow)
      )
      
      console.log('🔍 Checking comprehensive data (workflow-based):', {
        completedWorkflows: Array.from(completedWorkflows),
        requiredWorkflows,
        allRequiredCompleted,
        completedCount: completedWorkflows.size,
        requiredCount: requiredWorkflows.length
      })
      
      return allRequiredCompleted
    }
    
    // Fallback to the old task-based logic for backward compatibility
    const allTasks = allEvaluations.flatMap(evaluation => evaluation.task_executions || [])
    
    // More lenient check - just need some meaningful data
    const taskTypes = new Set(allTasks.map(task => task.task_name).filter(Boolean))
    
    console.log('🔍 Checking comprehensive data (fallback task-based):', {
      evaluations: allEvaluations.length,
      totalTasks: allTasks.length,
      uniqueTaskTypes: taskTypes.size,
      taskTypes: Array.from(taskTypes),
      hasComprehensiveData: taskTypes.size >= 2 || allTasks.length >= 3
    })
    
    // Show button if we have at least 2 different task types OR at least 3 total tasks
    // (Lowered requirements since binary compliance is now client-side)
    return taskTypes.size >= 2 || allTasks.length >= 3
  }

  const formatDateTime = (dateString: string) => {
    const date = new Date(dateString)
    return {
      date: date.toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
      }),
      time: date.toLocaleTimeString('en-US', { 
        hour: '2-digit', 
        minute: '2-digit' 
      })
    }
  }

  const { date, time } = formatDateTime(evaluation.created_at)

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-sm border p-8">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-3/4 mb-4"></div>
          <div className="h-4 bg-gray-200 rounded w-1/2 mb-4"></div>
          <div className="h-4 bg-gray-200 rounded w-5/6"></div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border">
      {/* Header Section */}
      <div className="border-b border-gray-200 p-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">
          {evaluation.tld_string} String Evaluation Report
        </h1>
        <p className="text-gray-600">
          Generated on {date} at {time}
        </p>
      </div>

      {/* Controls Section */}
      <div className="border-b border-gray-200 p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {/* View Toggle Buttons */}
            <Button
              onClick={() => setViewMode('markdown')}
              variant={viewMode === 'markdown' ? "default" : "outline"}
              size="sm"
              className="flex items-center gap-2"
            >
              <FileText className="w-4 h-4" />
              Markdown Output
            </Button>
            
            {geminiReport && (
              <Button
                onClick={() => setViewMode('report')}
                variant={viewMode === 'report' ? "default" : "outline"}
                size="sm"
                className="flex items-center gap-2"
              >
                <Sparkles className="w-4 h-4" />
                AI Analysis Report
              </Button>
            )}

            {/* Generate String Analysis Report Button */}
            {hasComprehensiveData() && (
              <Button
                onClick={generateGeminiReport}
                disabled={generatingReport}
                className="bg-purple-600 hover:bg-purple-700 text-white flex items-center gap-2"
                size="sm"
              >
                <Sparkles className="w-4 h-4" />
                {generatingReport ? 'Generating...' : (geminiReport ? 'Regenerate Report' : 'Generate String Analysis Report')}
              </Button>
            )}
          </div>

          <div className="flex items-center gap-2">
            {/* Google Docs Integration */}
            {googleDocsEnabled && googleDocUrl && (
              <Button
                onClick={() => window.open(googleDocUrl, '_blank')}
                variant="outline"
                size="sm"
                className="flex items-center gap-2"
              >
                <ExternalLink className="w-4 h-4" />
                Open in Google Docs
              </Button>
            )}

            {/* Download Button - Icon Only */}
            <Button
              onClick={viewMode === 'report' && geminiReport ? downloadGeminiReport : downloadDocument}
              variant="outline"
              size="sm"
              className="flex items-center"
            >
              <Download className="w-4 h-4" />
            </Button>
          </div>
        </div>

        {/* Google Docs Integration Notice */}
        {!googleDocsEnabled && hasComprehensiveData() && (
          <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
            <div className="flex items-start gap-2">
              <ExternalLink className="w-4 h-4 text-blue-600 mt-0.5" />
              <div className="text-sm">
                <span className="font-medium text-blue-900">Google Docs Integration Available</span>
                <p className="text-blue-800 mt-1">
                  Google Docs integration is not configured. Reports will be generated as downloadable files.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Content Section */}
      <div className="p-6">
        {viewMode === 'report' && geminiReport ? (
          <div className="bg-white">
            {/* Document-style container matching EvaluationReportViewer */}
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
                  {geminiReport}
                </ReactMarkdown>
              </div>
            </div>
          </div>
        ) : (
          <div className="bg-gray-50 rounded-lg border p-6 max-h-[600px] overflow-y-auto">
            <div className="prose prose-sm max-w-none">
              {generatingPreview ? (
                <div className="text-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
                  <p className="text-gray-600">Generating document preview...</p>
                </div>
              ) : (
                <pre className="whitespace-pre-wrap text-sm text-gray-800 font-mono leading-relaxed">
                  {documentContent || 'No content available'}
                </pre>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
} 