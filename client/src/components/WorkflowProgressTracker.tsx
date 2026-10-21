import { Card, CardContent, CardHeader, CardTitle } from "./ui/card"
import { CheckCircle, XCircle, RefreshCw, AlertCircle, Clock } from 'lucide-react'
import { type TldEvaluationWithAnalysis } from "@/types"

interface WorkflowProgressTrackerProps {
  evaluation: TldEvaluationWithAnalysis;
  onRefresh: () => void;
}

export default function WorkflowProgressTracker({ evaluation, onRefresh }: WorkflowProgressTrackerProps) {
  const allWorkflows = [
    { id: 'technical_risk_assessment', name: 'Technical Risk Assessment', description: 'DNS stability, name collision, security threats' },
    { id: 'legal_risk_assessment', name: 'Legal & Regulatory Risk', description: 'Trademarks, GAC advice, string confusion' },
    { id: 'policy_safeguard_review', name: 'Policy & Safeguard Compliance', description: 'ICANN policies, rights protection, sensitive strings' },
  ]

  // Simple status based on task completions
  const getWorkflowStatus = (workflowId: string): 'COMPLETED' | 'RUNNING' | 'FAILED' | 'NOT_STARTED' => {
    if (!evaluation.task_executions?.length) return 'NOT_STARTED'
    // Prefer explicit workflow_type tagging if available
    const relevantTasks = evaluation.task_executions.filter(task => {
      const taskWorkflow = (task.workflow_type || '').toString().toLowerCase()
      if (taskWorkflow) return taskWorkflow === workflowId.toLowerCase()
      // Fallback to keyword match if workflow_type is missing
      const taskName = task.task_name?.toLowerCase() || ''
      const workflowName = workflowId.replace('_', ' ').toLowerCase()
      return workflowName.split(' ').some(word => taskName.includes(word))
    })
    
    if (relevantTasks.length === 0) return 'NOT_STARTED'
    
    const hasFailed = relevantTasks.some(task => task.status === 'FAILED')
    if (hasFailed) return 'FAILED'
    
    const hasCompleted = relevantTasks.some(task => task.status === 'COMPLETED')
    const hasRunning = relevantTasks.some(task => task.status === 'RUNNING')
    
    if (hasCompleted && !hasRunning) return 'COMPLETED'
    if (hasRunning || hasCompleted) return 'RUNNING'
    
    return 'NOT_STARTED'
  }

  const getTaskCount = (workflowId: string): { completed: number; total: number } => {
    const relevantTasks = evaluation.task_executions?.filter(task => {
      const taskWorkflow = (task.workflow_type || '').toString().toLowerCase()
      if (taskWorkflow) return taskWorkflow === workflowId.toLowerCase()
      const taskName = task.task_name?.toLowerCase() || ''
      const workflowName = workflowId.replace('_', ' ').toLowerCase()
      return workflowName.split(' ').some(word => taskName.includes(word))
    }) || []
    
    const completed = relevantTasks.filter(task => (task.status || '').toString().toUpperCase() === 'COMPLETED').length
    return { completed, total: relevantTasks.length }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'COMPLETED':
        return <CheckCircle className="w-6 h-6 text-green-500" />
      case 'RUNNING':
        return <RefreshCw className="w-6 h-6 text-blue-500 animate-spin" />
      case 'FAILED':
        return <XCircle className="w-6 h-6 text-red-500" />
      case 'NOT_STARTED':
        return <Clock className="w-6 h-6 text-gray-400" />
      default:
        return <AlertCircle className="w-6 h-6 text-yellow-500" />
    }
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Workflow Progress</CardTitle>
        <RefreshCw 
          className="w-5 h-5 text-gray-500 cursor-pointer hover:text-blue-600 transition-colors"
          onClick={onRefresh}
        />
      </CardHeader>
      <CardContent>
        <p className="text-sm text-gray-600 mb-6">
          Workflows run automatically in sequence using <code>/api/evaluations/auto-submit</code>
        </p>
        <div className="space-y-4">
          {allWorkflows.map((workflow) => {
            const status = getWorkflowStatus(workflow.id)
            const { completed, total } = getTaskCount(workflow.id)
            return (
              <div key={workflow.id} className="flex items-start space-x-4 p-4 bg-gray-50 rounded-lg">
                <div className="mt-1">
                  {getStatusIcon(status)}
                </div>
                <div className="flex-1">
                  <h4 className="font-semibold text-gray-800">{workflow.name}</h4>
                  <p className="text-sm text-gray-500">{workflow.description}</p>
                  <div className="flex items-center gap-4 mt-2">
                    <p className="text-xs text-gray-400">
                      Status: <span className="font-medium">{status}</span>
                    </p>
                    {total > 0 && (
                      <p className="text-xs text-gray-400">
                        Tasks: <span className="font-medium">{completed}/{total} completed</span>
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
} 