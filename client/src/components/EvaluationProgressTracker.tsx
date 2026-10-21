import { Card, CardContent, CardHeader, CardTitle } from "./ui/card"
import { CheckCircle, Clock, RefreshCw, AlertCircle, XCircle } from 'lucide-react'
import { type TldEvaluationWithAnalysis } from "@/types"
import { Badge } from "./ui/badge"

interface EvaluationProgressTrackerProps {
  evaluation: TldEvaluationWithAnalysis
  onRefresh: () => void
}

// Workflow definitions matching crewai_service/evaluation/config/workflows.yaml
const WORKFLOWS = [
  {
    id: 'technical_risk_assessment',
    name: 'Technical Risk Assessment',
    description: 'DNS stability, collision analysis, and similarity analysis'
  },
  {
    id: 'legal_risk_assessment',
    name: 'Legal Risk Assessment', 
    description: 'Global trademark conflict analysis and legal risk evaluation'
  },
  {
    id: 'policy_safeguard_review',
    name: 'Policy Safeguard Review',
    description: 'Geographic names, cultural assessment, and safeguard compliance'
  }
]

export default function EvaluationProgressTracker({ evaluation, onRefresh }: EvaluationProgressTrackerProps) {
  
  // Get workflow progress using workflow_executions data (preferred) or task-level fallback
  const getWorkflowProgress = (workflow: typeof WORKFLOWS[0]) => {
    // First try to get status from workflow_executions table
    const workflowExecution = evaluation.workflow_executions?.find(
      we => we.workflow_type === workflow.id
    )
    
    if (workflowExecution) {
      // Use workflow-level status - much simpler and more reliable
      const completedTasks = workflowExecution.completed_tasks?.length || 0
      const totalTasks = workflowExecution.planned_tasks?.length || 0
      const failedTasks = workflowExecution.failed_tasks?.length || 0
      
      return {
        status: workflowExecution.status,
        completed: completedTasks,
        total: totalTasks,
        running: workflowExecution.status === 'RUNNING' ? 1 : 0,
        failed: failedTasks,
        tasks: evaluation.task_executions?.filter(task => 
          task.workflow_execution_id === workflowExecution.id
        ) || []
      }
    }
    
    // Fallback to task-level analysis using workflow_executions if available
    let workflowTasks: any[] = []
    
    // If we have workflow_executions data, use that to filter tasks
    if (evaluation.workflow_executions && evaluation.workflow_executions.length > 0) {
      const workflowExecution = evaluation.workflow_executions.find(we => we.workflow_type === workflow.id)
      if (workflowExecution) {
        // Use the task lists from workflow_executions
        const allWorkflowTaskNames = [
          ...(workflowExecution.planned_tasks || []),
          ...(workflowExecution.completed_tasks || []),
          ...(workflowExecution.failed_tasks || [])
        ]
        
        workflowTasks = evaluation.task_executions?.filter(task => 
          allWorkflowTaskNames.some(taskName => 
            task.task_name?.toLowerCase().includes(taskName.toLowerCase()) ||
            taskName.toLowerCase().includes(task.task_name?.toLowerCase() || '')
          )
        ) || []
      }
    }
    
    // If no tasks found with workflow_execution_id, try name-based matching (legacy)
    if (workflowTasks.length === 0) {
      // Define expected task patterns for each workflow
      const workflowTaskPatterns: Record<string, string[]> = {
        'technical_risk_assessment': ['dns_stability', 'collision_assessment', 'similarity_analysis', 'technical_risk'],
        'legal_risk_assessment': ['trademark_assessment', 'patent_conflict', 'legal_risk'],
        'policy_safeguard_review': ['geographic_name', 'safeguard_assessment', 'gac_risk', 'cultural_linguistic', 'policy_safeguard']
      }
      
      const patterns = workflowTaskPatterns[workflow.id] || []
      workflowTasks = evaluation.task_executions?.filter(task => 
        patterns.some(pattern => 
          task.task_name?.toLowerCase().includes(pattern.toLowerCase())
        )
      ) || []
    }

    const completedTasks = workflowTasks.filter(task => task.status === 'COMPLETED')
    const runningTasks = workflowTasks.filter(task => task.status === 'RUNNING')
    const failedTasks = workflowTasks.filter(task => task.status === 'FAILED')

    let status: 'COMPLETED' | 'RUNNING' | 'FAILED' | 'PENDING' = 'PENDING'
    
    if (failedTasks.length > 0) {
      status = 'FAILED'
    } else if (runningTasks.length > 0) {
      status = 'RUNNING'
    } else if (completedTasks.length > 0 && workflowTasks.length > 0) {
      // Only mark as completed if we have a reasonable number of completed tasks
      status = completedTasks.length >= Math.floor(workflowTasks.length * 0.5) ? 'COMPLETED' : 'RUNNING'
    }

    return {
      status,
      completed: completedTasks.length,
      total: workflowTasks.length,
      running: runningTasks.length,
      failed: failedTasks.length,
      tasks: workflowTasks
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'COMPLETED':
        return <CheckCircle className="w-5 h-5 text-green-500" />
      case 'RUNNING':
        return <RefreshCw className="w-5 h-5 text-blue-500 animate-spin" />
      case 'FAILED':
        return <XCircle className="w-5 h-5 text-red-500" />
      case 'PENDING':
        return <Clock className="w-5 h-5 text-gray-400" />
      default:
        return <AlertCircle className="w-5 h-5 text-yellow-500" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'COMPLETED': return 'text-green-600'
      case 'RUNNING': return 'text-blue-600'
      case 'FAILED': return 'text-red-600'
      case 'PENDING': return 'text-gray-500'
      default: return 'text-yellow-600'
    }
  }

  // Calculate overall progress using workflow status
  const workflowProgresses = WORKFLOWS.map(w => getWorkflowProgress(w))
  const totalWorkflows = WORKFLOWS.length
  const completedWorkflows = workflowProgresses.filter(p => p.status === 'COMPLETED').length
  const overallProgress = totalWorkflows > 0 ? Math.round((completedWorkflows / totalWorkflows) * 100) : 0
  
  // For display, show task-level detail if available
  const totalTasks = workflowProgresses.reduce((sum, p) => sum + p.total, 0)
  const completedTasks = workflowProgresses.reduce((sum, p) => sum + p.completed, 0)

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle>Evaluation Progress</CardTitle>
          <p className="text-sm text-gray-600 mt-1">
            {completedTasks}/{totalTasks} tasks completed ({overallProgress}%)
          </p>
        </div>
        <RefreshCw 
          className="w-5 h-5 text-gray-500 cursor-pointer hover:text-blue-600 transition-colors"
          onClick={onRefresh}
        />
      </CardHeader>
      <CardContent>
        {/* Overall Progress Bar */}
        <div className="mb-6">
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className="bg-blue-500 h-2 rounded-full transition-all duration-300"
              style={{ width: `${overallProgress}%` }}
            />
          </div>
        </div>

        {/* Workflow Progress */}
        <div className="space-y-4">
          {WORKFLOWS.map((workflow) => {
            const progress = getWorkflowProgress(workflow)
            const progressPercent = progress.total > 0 ? Math.round((progress.completed / progress.total) * 100) : 0
            
            return (
              <div key={workflow.id} className="border rounded-lg p-4 bg-gray-50">
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center space-x-3">
                    {getStatusIcon(progress.status)}
                    <div>
                      <h4 className="font-semibold text-gray-800">{workflow.name}</h4>
                      <p className="text-sm text-gray-600">{workflow.description}</p>
                    </div>
                  </div>
                  <Badge 
                    variant={progress.status === 'COMPLETED' ? 'default' : 
                             progress.status === 'RUNNING' ? 'secondary' : 'outline'}
                  >
                    {progress.status}
                  </Badge>
                </div>

                {/* Workflow Progress Bar */}
                <div className="mb-3">
                  <div className="flex justify-between text-xs text-gray-500 mb-1">
                    <span>{progress.completed}/{progress.total} tasks</span>
                    <span>{progressPercent}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-1.5">
                    <div 
                      className={`h-1.5 rounded-full transition-all duration-300 ${
                        progress.status === 'COMPLETED' ? 'bg-green-500' :
                        progress.status === 'RUNNING' ? 'bg-blue-500' :
                        progress.status === 'FAILED' ? 'bg-red-500' : 'bg-gray-300'
                      }`}
                      style={{ width: `${progressPercent}%` }}
                    />
                  </div>
                </div>

                {/* Task Details */}
                {progress.tasks.length > 0 && (
                  <div className="space-y-1">
                    {progress.tasks.map((task) => (
                      <div key={task.id} className="flex items-center space-x-2 text-xs">
                        {getStatusIcon(task.status)}
                        <span className={getStatusColor(task.status)}>
                          {task.task_name || 'Unknown Task'}
                        </span>
                        {task.status === 'COMPLETED' && task.completed_at && (
                          <span className="text-gray-400">
                            • {new Date(task.completed_at).toLocaleTimeString()}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {/* Active Task Info */}
                {progress.status === 'RUNNING' && progress.running > 0 && (
                  <div className="mt-2 p-2 bg-blue-50 rounded text-xs text-blue-700">
                    ⚡ {progress.running} task{progress.running > 1 ? 's' : ''} currently running
                  </div>
                )}

                {/* Failed Task Info */}
                {progress.failed > 0 && (
                  <div className="mt-2 p-2 bg-red-50 rounded text-xs text-red-700">
                    ❌ {progress.failed} task{progress.failed > 1 ? 's' : ''} failed
                  </div>
                )}
              </div>
            )
          })}
        </div>

        {/* Overall Status */}
        <div className="mt-6 pt-4 border-t">
          <div className="text-center">
            <Badge 
              variant={evaluation.status === 'COMPLETED' ? 'default' : 
                       evaluation.status === 'RUNNING' ? 'secondary' : 'outline'}
              className="text-sm"
            >
              Overall Status: {evaluation.status || evaluation.overall_status || 'PENDING'}
            </Badge>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}