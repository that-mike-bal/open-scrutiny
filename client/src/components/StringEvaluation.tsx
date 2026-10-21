import { useState, useEffect } from 'react'
import { useParams, useNavigate, useLocation } from 'react-router-dom'
import { getTldEvaluationsByString } from '@/lib/supabase-api'
import type { TldEvaluationWithAnalysis } from '@/types'
import { Button } from './ui/button'
import { ArrowLeft, AlertTriangle, RefreshCw, Play, RotateCcw, FileText } from 'lucide-react'
import EvaluationReportViewer from './EvaluationReportViewer' 
import { Badge } from './ui/badge'
import CreateApplicationModal from './CreateApplicationModal'

export default function StringEvaluation() {
  const { tldString: urlTldString } = useParams<{ tldString: string }>()
  const navigate = useNavigate()
  const location = useLocation()
  
  const [evaluation, setEvaluation] = useState<TldEvaluationWithAnalysis | null>(location.state?.evaluation || null)
  const [loading, setLoading] = useState(!location.state?.evaluation)
  const [error, setError] = useState<string | null>(null)
  const [triggeringEvaluation, setTriggeringEvaluation] = useState(false)
  const [createAppModalOpen, setCreateAppModalOpen] = useState(false)
  
  const currentTldString = urlTldString || 'unknown'

  // Debug logging
  console.log('StringEvaluation - Current TLD:', currentTldString)
  console.log('StringEvaluation - Has evaluation from state:', !!location.state?.evaluation)
  console.log('StringEvaluation - Evaluation object:', evaluation)

  // Fetch evaluation data directly from Supabase (no backend dependency)
  const refreshEvaluation = async () => {
    if (!evaluation) {
      setLoading(true)
    }
    setError(null)
    try {
      console.log(`🔄 Fetching evaluation for TLD: ${currentTldString}`)

      const results = await getTldEvaluationsByString(currentTldString)

      if (!results || results.length === 0) {
        console.log(`❌ Evaluation not found for TLD: ${currentTldString}`)
        throw new Error('NOT_FOUND')
      }

      // Use the most recent evaluation
      const evaluationData = results[0]
      console.log('✅ Evaluation data loaded from Supabase:', evaluationData)

      setEvaluation(evaluationData)
    } catch (err: any) {
      console.error('❌ Error fetching evaluation:', err)
      if (err.message === 'NOT_FOUND') {
        setError("Not Found")
      } else {
        setError(err.message)
      }
    } finally {
      if (loading) setLoading(false)
    }
  }
  
  // Initial fetch and polling
  useEffect(() => {
    // Always do initial fetch to get latest data
    console.log('📡 Fetching evaluation data from API...')
    refreshEvaluation()
  }, [currentTldString])

  // Set up polling based on evaluation status
  useEffect(() => {
    // Only poll if we have an evaluation and it's in a running state
    const shouldPoll = evaluation && (
      evaluation.status === 'RUNNING' || 
      evaluation.overall_status === 'RUNNING' ||
      evaluation.status === 'PENDING'
    )
    
    let intervalId: NodeJS.Timeout | null = null
    if (shouldPoll) {
      console.log('🔄 Setting up polling for running evaluation:', evaluation.status || evaluation.overall_status)
      intervalId = setInterval(() => {
        console.log('⏰ Polling for updates...')
        refreshEvaluation()
      }, 5000) // Reduced to 5 seconds for better responsiveness
    }

    // Clean up interval on component unmount or status change
    return () => {
      if (intervalId) {
        clearInterval(intervalId)
        console.log('🛑 Stopped polling for evaluation updates')
      }
    }
  }, [evaluation?.status, evaluation?.overall_status])

  const handleBackToDashboard = () => {
    navigate('/')
  }

  const handleCreateApplication = () => {
    console.log(`📋 Opening application creation modal for .${currentTldString} from evaluation screen`)
    setCreateAppModalOpen(true)
  }

  const triggerManualEvaluation = async () => {
    setTriggeringEvaluation(true)
    setError(null)
    
    try {
      console.log(`🚀 Manually triggering evaluation for: ${currentTldString}`)
      
      // Call the CrewAI service directly to restart/continue evaluation
      const isDev = import.meta.env.VITE_DEV_MODE === 'true'
      const crewaiEndpoint = import.meta.env.VITE_CREWAI_ENDPOINT || 'http://localhost:8000'
      
      if (isDev) {
        const response = await fetch(`${crewaiEndpoint}/evaluations/run`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            tld_string: currentTldString,
            use_case: evaluation?.use_case || 'General evaluation',
            workflow_type: evaluation?.workflow_type || 'technical_risk_assessment',
            force_restart: true // Add flag to indicate manual trigger
          })
        })

        if (!response.ok) {
          throw new Error(`Failed to trigger evaluation: ${response.statusText}`)
        }

        const result = await response.json()
        console.log('✅ Manual evaluation triggered:', result)
        
        // Refresh the evaluation data after a short delay
        setTimeout(() => {
          refreshEvaluation()
        }, 2000)
        
      } else {
        // For production, you might want to call a different endpoint
        console.warn('Manual trigger not implemented for production mode')
        throw new Error('Manual trigger not available in production mode')
      }
      
    } catch (err: any) {
      console.error('❌ Error triggering manual evaluation:', err)
      setError(`Failed to trigger evaluation: ${err.message}`)
    } finally {
      setTriggeringEvaluation(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-12 h-12 text-blue-500 animate-spin mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900">Loading Evaluation...</h2>
          <p className="text-gray-600">Please wait while we fetch the details for .{currentTldString}</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="max-w-md mx-auto px-6 py-8 text-center">
          <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Error Loading Evaluation</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <Button variant="outline" onClick={handleBackToDashboard}>
            Back to Dashboard
          </Button>
        </div>
      </div>
    )
  }

  if (error === "Not Found" || !evaluation) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="max-w-4xl mx-auto px-6 py-8">
          <div className="mb-8">
            <Button variant="ghost" onClick={handleBackToDashboard}>
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Dashboard
            </Button>
          </div>
          
          <div className="bg-white rounded-lg shadow-sm border p-8 text-center">
            <AlertTriangle className="w-12 h-12 text-yellow-500 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Evaluation Not Found</h2>
            <p className="text-gray-600 mb-4">
              The evaluation for <strong>.{currentTldString}</strong> could not be found. 
              It may have been deleted or never existed.
            </p>
            <Button variant="outline" onClick={handleBackToDashboard}>
              Back to Dashboard
            </Button>
          </div>
        </div>
      </div>
    )
  }
  
  const { tld_string, use_case, status, overall_status } = evaluation

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <Button variant="ghost" onClick={handleBackToDashboard}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Dashboard
          </Button>
        </div>

        <header className="bg-white shadow-sm rounded-lg mb-8">
          <div className="px-6 py-5">
            <div className="flex items-center justify-between">
              <div>
                <div className="flex items-center space-x-3">
                  <div className="bg-blue-100 text-blue-800 font-bold rounded-md px-4 py-2 text-lg">
                    .{tld_string}
                  </div>
                  <h1 className="text-2xl font-bold text-gray-900">TLD Evaluation Report</h1>
                </div>
                <p className="mt-1 text-sm text-gray-600">
                  Comprehensive analysis for .{tld_string} domain • {use_case}
                </p>
              </div>
              <div className="flex items-center space-x-3">
                {/* Manual trigger button - show for failed, stuck, or incomplete evaluations */}
                {((overall_status || status) === 'FAILED' || 
                  (overall_status || status) === 'PENDING' || 
                  ((overall_status || status) === 'RUNNING' && (!evaluation?.task_executions || evaluation.task_executions.length === 0))) && (
                  <Button 
                    onClick={triggerManualEvaluation} 
                    disabled={triggeringEvaluation}
                    variant="outline"
                    size="sm"
                  >
                    {triggeringEvaluation ? (
                      <RotateCcw className="w-4 h-4 mr-2 animate-spin" />
                    ) : (
                      <Play className="w-4 h-4 mr-2" />
                    )}
                    {triggeringEvaluation ? 'Starting...' : 'Run Evaluation'}
                  </Button>
                )}
                
                {/* Create Application button - show for completed evaluations */}
                {((overall_status || status) === 'completed' || (overall_status || status) === 'COMPLETED') && (
                  <Button 
                    onClick={handleCreateApplication}
                    variant="default"
                    size="sm"
                    className="bg-green-600 hover:bg-green-700"
                  >
                    <FileText className="w-4 h-4 mr-2" />
                    Create Application
                  </Button>
                )}
                
                <Badge variant={
                  (overall_status || status) === 'completed' || (overall_status || status) === 'COMPLETED' ? 'default' : 
                  (overall_status || status) === 'in_progress' || (overall_status || status) === 'RUNNING' ? 'secondary' : 
                  'outline'
                }>
                  {overall_status || status}
                </Badge>
              </div>
            </div>
          </div>
        </header>

        <div className="max-w-4xl mx-auto">
          <EvaluationReportViewer evaluation={evaluation} />
        </div>
      </div>
      
      {/* Application Creation Modal */}
      <CreateApplicationModal
        isOpen={createAppModalOpen}
        onClose={() => setCreateAppModalOpen(false)}
        tldString={currentTldString}
        evaluationId={evaluation?.id}
        onApplicationCreated={(applicationId) => {
          console.log(`✅ Application created: ${applicationId}`)
          setCreateAppModalOpen(false)
          // Could show a success message here if needed
        }}
      />
    </div>
  )
} 