import { useMemo } from 'react'
import type { WorkflowProgress } from '../lib/supabase-api'

interface BinaryGateResult {
  name: string
  status: 'PASS' | 'BLOCKED' | 'PENDING' | 'RUNNING'
  description: string
  details?: string
  timestamp?: string
  agent?: string
  confidence?: number
}

interface BinaryGateStatus {
  gates: BinaryGateResult[]
  overallStatus: 'PASS' | 'BLOCKED' | 'PENDING' | 'RUNNING'
  isComplete: boolean
  blockedGates: BinaryGateResult[]
}

// Define the expected binary gates based on our workflow configuration
const BINARY_GATES = [
  {
    name: 'IANA Database Check',
    description: 'Verify TLD is not already delegated in IANA root database',
    agent: 'IANA Compliance Gatekeeper',
    taskKeywords: ['iana_verification', 'iana database', 'existing tld']
  },
  {
    name: 'Blocked Names Check',
    description: 'Check against ICANN blocked names list (Special-use domains, country names, etc.)',
    agent: 'IANA Compliance Gatekeeper',
    taskKeywords: ['blocked_names_check', 'blocked names', 'special-use']
  },
  {
    name: 'Reserved Names Check',
    description: 'Verify against reserved names (IGO, RCRC, IOC organizations)',
    agent: 'Data Validation & Fact-Checking Specialist',
    taskKeywords: ['reserved_names_check', 'reserved names', 'igo', 'rcrc', 'ioc']
  },
  {
    name: 'DNS Stability Review',
    description: 'Assess DNS stability and Root Zone Label Generation Rules compliance',
    agent: 'Data Validation & Fact-Checking Specialist', 
    taskKeywords: ['dns_stability_review', 'dns stability', 'root zone', 'technical compliance']
  },
  {
    name: 'Validation & Fact-Checking',
    description: 'Cross-reference all binary gate findings against actual data sources',
    agent: 'Data Validation & Fact-Checking Specialist',
    taskKeywords: ['findings_validation', 'validation', 'fact-checking', 'cross-reference']
  }
]

export function useBinaryGateStatus(progress: WorkflowProgress | null): BinaryGateStatus {
  return useMemo(() => {
    if (!progress) {
      return {
        gates: BINARY_GATES.map(gate => ({
          name: gate.name,
          status: 'PENDING' as const,
          description: gate.description,
          agent: gate.agent
        })),
        overallStatus: 'PENDING' as const,
        isComplete: false,
        blockedGates: []
      }
    }

    // Parse agent responses and progress messages to determine gate status
    const gates: BinaryGateResult[] = BINARY_GATES.map(gateConfig => {
      const gate: BinaryGateResult = {
        name: gateConfig.name,
        status: 'PENDING',
        description: gateConfig.description,
        agent: gateConfig.agent
      }

      // Check if this gate is mentioned in progress messages
      const progressText = progress.message?.toLowerCase() || ''
      const combinedText = progressText

      // Check for gate-specific keywords
      const hasKeywordMatch = gateConfig.taskKeywords.some(keyword => 
        combinedText.includes(keyword.toLowerCase())
      )

      if (hasKeywordMatch) {
        // Determine status based on BINARY_GATE_RESULT specifically, not general keywords
        if (combinedText.includes('binary_gate_result: blocked') || combinedText.includes('❌ blocked')) {
          gate.status = 'BLOCKED'
          gate.details = extractBlockingReason(combinedText)
        } else if (combinedText.includes('binary_gate_result: pass') || combinedText.includes('✅ pass') || combinedText.includes('✅ not found')) {
          gate.status = 'PASS'
          gate.details = extractPassDetails(combinedText)
        } else if (combinedText.includes('running') || combinedText.includes('executing') || combinedText.includes('checking')) {
          gate.status = 'RUNNING'
        }
        
        // Extract confidence if available
        const confidenceMatch = combinedText.match(/confidence[:\s]*(\d+)%?/i)
        if (confidenceMatch) {
          gate.confidence = parseInt(confidenceMatch[1])
        }
        
        gate.timestamp = progress.timestamp
      }

      // Check if agent is currently working on this gate
      if (progress.agent_role?.includes(gateConfig.agent)) {
        const taskText = progress.task_description?.toLowerCase() || ''
        const hasTaskMatch = gateConfig.taskKeywords.some(keyword => 
          taskText.includes(keyword.toLowerCase())
        )
        
        if (hasTaskMatch && gate.status === 'PENDING') {
          gate.status = 'RUNNING'
        }
      }

      return gate
    })

    // Determine overall status
    const blockedGates = gates.filter(gate => gate.status === 'BLOCKED')
    const runningGates = gates.filter(gate => gate.status === 'RUNNING')
    const passedGates = gates.filter(gate => gate.status === 'PASS')

    let overallStatus: 'PASS' | 'BLOCKED' | 'PENDING' | 'RUNNING'
    let isComplete = false

    if (blockedGates.length > 0) {
      overallStatus = 'BLOCKED'
      isComplete = true
    } else if (passedGates.length === gates.length) {
      overallStatus = 'PASS'
      isComplete = true
    } else if (runningGates.length > 0) {
      overallStatus = 'RUNNING'
    } else {
      overallStatus = 'PENDING'
    }

    // Check workflow-level status from message or type
    const isWorkflowCompleted = progress.type === 'crew_completed' || 
                               progress.message?.toLowerCase().includes('completed') ||
                               progress.message?.toLowerCase().includes('finished')
    const isWorkflowBlocked = progress.type === 'crew_failed' ||
                             progress.message?.toLowerCase().includes('blocked') ||
                             progress.error !== undefined

    if (isWorkflowCompleted || isWorkflowBlocked) {
      isComplete = true
      if (isWorkflowBlocked) {
        overallStatus = 'BLOCKED'
      } else if (blockedGates.length === 0) {
        overallStatus = 'PASS'
      }
    }

    return {
      gates,
      overallStatus,
      isComplete,
      blockedGates
    }
  }, [progress])
}

function extractBlockingReason(text: string): string {
  // Look for specific blocking reasons
  if (text.includes('already delegated') || text.includes('existing tld')) {
    return 'TLD already exists in IANA database'
  }
  if (text.includes('blocked name') || text.includes('special-use')) {
    return 'TLD matches ICANN blocked names list'
  }
  if (text.includes('reserved') && (text.includes('igo') || text.includes('rcrc') || text.includes('ioc'))) {
    return 'TLD is reserved for international organizations'
  }
  if (text.includes('dns') && (text.includes('stability') || text.includes('technical'))) {
    return 'DNS stability or technical compliance issues'
  }
  
  return 'Gate blocked - see detailed analysis'
}

function extractPassDetails(text: string): string {
  // Look for specific pass details
  if (text.includes('available') || text.includes('not found')) {
    return 'TLD is available and passes verification'
  }
  if (text.includes('no conflicts') || text.includes('no blocking')) {
    return 'No conflicts detected'
  }
  if (text.includes('compliant') || text.includes('meets requirements')) {
    return 'Meets all technical requirements'
  }
  
  return 'Gate passed successfully'
} 