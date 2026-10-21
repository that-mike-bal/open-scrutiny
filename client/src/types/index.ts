export interface TldString {
  id: string
  tld_string: string
  use_case: string
  created_at: string
  updated_at: string
  has_evaluation: boolean
  has_application_draft: boolean
  has_feasibility_study: boolean
  status?: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'Evaluated'
  evaluation_status?: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED'
  evaluation_result?: 'PROCEED' | 'CONDITIONAL' | 'HIGH_RISK' | 'BLOCKED'
  feasibility_determination?: 'PROCEED' | 'CONDITIONAL' | 'HIGH_RISK' | 'DO_NOT_PROCEED'
  workflow_type?: 'comprehensive_feasibility' | 'technical_risk_assessment' | 'legal_risk_assessment' | 'policy_safeguard_review' | 'government_sensitivity_workflow' | 'market_intelligence_deep_dive' | 'tld_evaluation' | 'compliance_only' | 'market_analysis'
  expert_review_required?: boolean
  confidence_score?: number
  risk_score?: number
  risk_classification?: string
  risk_level?: string
  risk_recommendation?: string
  // Backend writes uppercase workflow states; older rows use the lowercase form
  overall_status?: 'not_started' | 'in_progress' | 'completed' | 'failed' | 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED'
  string_type?: 'primary' | 'secondary'
}

export interface EvaluationResult {
  id: string
  tld_string_id: string
  workflow_type: string
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED'
  result: 'PROCEED' | 'BLOCKED' | 'REVIEW_REQUIRED'
  results_data: Record<string, any>
  created_at: string
  completed_at?: string
  risk_score?: number
  risk_classification?: string
  risk_level?: string
  risk_recommendation?: string
}

export interface TaskExecution {
  id: string
  tld_string_id: string
  task_definition_id: string
  workflow_execution_id: string
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED'
  result: Record<string, any>
  created_at: string
  updated_at: string
  completed_at?: string
  task_name: string
  workflow_type?: string
  model_name?: string
  output_format?: 'json' | 'markdown' | 'text'
  confidence_score?: number
  result_data?: {
    output?: string
    raw_output?: string
    [key: string]: any
  }
}

export interface WorkflowExecution {
  id: string;
  tld_string_id: string;
  workflow_type: string;
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED';
  started_at: string;
  completed_at: string | null;
  created_by: string;
  planned_tasks: string[];
  completed_tasks: string[];
  failed_tasks: string[];
}

export type TldEvaluationWithAnalysis = TldString & {
  task_executions?: TaskExecution[]
  workflow_executions?: WorkflowExecution[]
  overall_status?: string
  generated_report?: any
  // Present only when use-case analysis metrics have been merged in
  overall_risk_level?: string
  overall_business_score?: number
}


export type ViewMode = 'grid' | 'list'
export type SortField = 'name' | 'created' | 'updated' | 'status' | 'risk_score'
export type SortDirection = 'asc' | 'desc'