import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Badge } from './ui/badge'
import { CheckCircle, XCircle, Clock, AlertTriangle, ChevronDown, ChevronUp, User, Shield, FileText } from 'lucide-react'

interface BinaryGateResult {
  name: string
  status: 'PASS' | 'BLOCKED' | 'PENDING' | 'RUNNING'
  description: string
  details?: string
  timestamp?: string
  agent?: string
  confidence?: number
  output?: string
  recommendation?: string
  blocking_reason?: string
}

interface BinaryGateStatusProps {
  gates: BinaryGateResult[]
  overallStatus: 'PASS' | 'BLOCKED' | 'PENDING' | 'RUNNING'
  tldString: string
}

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'PASS':
      return <CheckCircle className="w-5 h-5 text-green-600" />
    case 'BLOCKED':
      return <XCircle className="w-5 h-5 text-red-600" />
    case 'RUNNING':
      return <Clock className="w-5 h-5 text-blue-600 animate-spin" />
    case 'PENDING':
      return <Clock className="w-5 h-5 text-gray-400" />
    default:
      return <AlertTriangle className="w-5 h-5 text-yellow-600" />
  }
}

const getStatusBadgeVariant = (status: string): "default" | "secondary" | "destructive" | "outline" | "success" | "warning" | "info" => {
  switch (status) {
    case 'PASS':
      return 'success'
    case 'BLOCKED':
      return 'destructive'
    case 'RUNNING':
      return 'info'
    case 'PENDING':
      return 'secondary'
    default:
      return 'outline'
  }
}

const getOverallStatusColor = (status: string) => {
  switch (status) {
    case 'PASS':
      return 'text-green-600 border-green-200 bg-green-50'
    case 'BLOCKED':
      return 'text-red-600 border-red-200 bg-red-50'
    case 'RUNNING':
      return 'text-blue-600 border-blue-200 bg-blue-50'
    case 'PENDING':
      return 'text-gray-600 border-gray-200 bg-gray-50'
    default:
      return 'text-yellow-600 border-yellow-200 bg-yellow-50'
  }
}

function ExpandableGateCard({ gate }: { gate: BinaryGateResult }) {
  const [isExpanded, setIsExpanded] = useState(false)

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <CardTitle className="text-base">{gate.name}</CardTitle>
          </div>
          <div className="flex items-center space-x-3">
            {/* Pass/Fail Indicator */}
            <div className={`flex items-center justify-center w-16 h-8 rounded-full font-medium text-sm transition-all duration-300 ${
              gate.status === 'PASS' 
                ? 'bg-green-100 text-green-800 border-2 border-green-300' 
                : gate.status === 'BLOCKED' 
                ? 'bg-red-100 text-red-800 border-2 border-red-300'
                : gate.status === 'RUNNING'
                ? 'bg-blue-100 text-blue-800 border-2 border-blue-300'
                : 'bg-gray-100 text-gray-600 border-2 border-gray-300'
            }`}>
              {gate.status === 'PASS' && <CheckCircle className="w-4 h-4" />}
              {gate.status === 'BLOCKED' && <XCircle className="w-4 h-4" />}
              {gate.status === 'RUNNING' && <Clock className="w-4 h-4 animate-spin" />}
              {gate.status === 'PENDING' && <Clock className="w-4 h-4" />}
            </div>
            
            {/* Status Text */}
            <div className={`text-sm font-medium min-w-[60px] text-center ${
              gate.status === 'PASS' ? 'text-green-700' :
              gate.status === 'BLOCKED' ? 'text-red-700' :
              gate.status === 'RUNNING' ? 'text-blue-700' :
              'text-gray-600'
            }`}>
              {gate.status}
            </div>
            
            {(gate.details || gate.output || gate.recommendation) && (
              <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="p-1 hover:bg-gray-100 rounded"
              >
                {isExpanded ? (
                  <ChevronUp className="w-4 h-4 text-gray-500" />
                ) : (
                  <ChevronDown className="w-4 h-4 text-gray-500" />
                )}
              </button>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground mb-3">
          {gate.description}
        </p>
        
        {/* Basic Details - Always Visible */}
        {gate.details && (
          <div className="bg-gray-50 rounded-md p-3 mb-3">
            <p className="text-xs text-gray-600">
              {gate.details}
            </p>
          </div>
        )}

        {/* Expandable Detailed Information */}
        {isExpanded && (
          <div className="space-y-3 border-t pt-3">
            {/* Agent Output */}
            {gate.output && (
              <div>
                <div className="flex items-center space-x-1 mb-2">
                  <User className="w-3 h-3 text-blue-600" />
                  <span className="text-xs font-medium text-blue-600">Agent Analysis</span>
                </div>
                <div className="bg-blue-50 rounded-md p-3">
                  <p className="text-xs text-blue-800 whitespace-pre-wrap">
                    {gate.output}
                  </p>
                </div>
              </div>
            )}

            {/* Blocking Reason */}
            {gate.blocking_reason && gate.status === 'BLOCKED' && (
              <div>
                <div className="flex items-center space-x-1 mb-2">
                  <Shield className="w-3 h-3 text-red-600" />
                  <span className="text-xs font-medium text-red-600">Blocking Reason</span>
                </div>
                <div className="bg-red-50 rounded-md p-3">
                  <p className="text-xs text-red-800">
                    {gate.blocking_reason}
                  </p>
                </div>
              </div>
            )}

            {/* Recommendation */}
            {gate.recommendation && (
              <div>
                <div className="flex items-center space-x-1 mb-2">
                  <FileText className="w-3 h-3 text-green-600" />
                  <span className="text-xs font-medium text-green-600">Recommendation</span>
                </div>
                <div className="bg-green-50 rounded-md p-3">
                  <p className="text-xs text-green-800">
                    {gate.recommendation}
                  </p>
                </div>
              </div>
            )}

            {/* Technical Details */}
            <div className="grid grid-cols-2 gap-3 text-xs">
              {gate.agent && (
                <div>
                  <span className="font-medium text-gray-600">Agent:</span>
                  <p className="text-gray-800">{gate.agent}</p>
                </div>
              )}
              {gate.confidence && (
                <div>
                  <span className="font-medium text-gray-600">Confidence:</span>
                  <p className="text-gray-800">{gate.confidence}%</p>
                </div>
              )}
              {gate.timestamp && (
                <div className="col-span-2">
                  <span className="font-medium text-gray-600">Completed:</span>
                  <p className="text-gray-800">{new Date(gate.timestamp).toLocaleString()}</p>
                </div>
              )}
            </div>
          </div>
        )}
        
        {/* Footer Info - Always Visible */}
        <div className="flex items-center justify-between text-xs text-muted-foreground mt-3 pt-2 border-t">
          <span>
            {gate.agent && `${gate.agent}`}
          </span>
          <span>
            {gate.confidence && `${gate.confidence}% confidence`}
            {gate.timestamp && ` • ${new Date(gate.timestamp).toLocaleTimeString()}`}
          </span>
        </div>
      </CardContent>
    </Card>
  )
}

export default function BinaryGateStatus({ gates, overallStatus, tldString }: BinaryGateStatusProps) {
  const passedGates = gates.filter(gate => gate.status === 'PASS').length
  const totalGates = gates.length
  const blockedGates = gates.filter(gate => gate.status === 'BLOCKED')
  const runningGates = gates.filter(gate => gate.status === 'RUNNING')

  return (
    <div className="space-y-6">
      {/* Overall Status Header */}
      <Card className={`border-2 ${getOverallStatusColor(overallStatus)}`}>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              {getStatusIcon(overallStatus)}
              <div>
                <CardTitle className="text-xl">
                  Binary Compliance Gates: .{tldString}
                </CardTitle>
                <p className="text-sm text-muted-foreground mt-1">
                  {overallStatus === 'PASS' && `All ${totalGates} gates passed successfully`}
                  {overallStatus === 'BLOCKED' && `${blockedGates.length} gate(s) blocked - evaluation halted`}
                  {overallStatus === 'RUNNING' && `${runningGates.length} gate(s) currently running...`}
                  {overallStatus === 'PENDING' && 'Waiting to start binary compliance checks'}
                </p>
              </div>
            </div>
            <div className="text-right">
              <Badge variant={getStatusBadgeVariant(overallStatus)} className="text-sm">
                {overallStatus}
              </Badge>
              <p className="text-xs text-muted-foreground mt-1">
                {passedGates}/{totalGates} Gates
              </p>
            </div>
          </div>
        </CardHeader>
        
        {/* Progress Bar */}
        <CardContent className="pt-0">
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className={`h-2 rounded-full transition-all duration-300 ${
                overallStatus === 'BLOCKED' ? 'bg-red-500' : 
                overallStatus === 'PASS' ? 'bg-green-500' : 'bg-blue-500'
              }`}
              style={{ width: `${(passedGates / totalGates) * 100}%` }}
            ></div>
          </div>
        </CardContent>
      </Card>

      {/* Individual Gate Results */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {gates.map((gate, index) => (
          <ExpandableGateCard key={index} gate={gate} />
        ))}
      </div>

      {/* Blocked Gate Alert */}
      {blockedGates.length > 0 && (
        <Card className="border-red-200 bg-red-50">
          <CardHeader>
            <div className="flex items-center space-x-2">
              <XCircle className="w-5 h-5 text-red-600" />
              <CardTitle className="text-red-800">Evaluation Blocked</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-red-700 mb-3">
              The following gate(s) have blocked the evaluation from proceeding:
            </p>
            <ul className="space-y-2">
              {blockedGates.map((gate, index) => (
                <li key={index} className="flex items-start space-x-2">
                  <XCircle className="w-4 h-4 text-red-600 mt-0.5 flex-shrink-0" />
                  <div>
                    <span className="font-medium text-red-800">{gate.name}</span>
                    {gate.blocking_reason && (
                      <p className="text-sm text-red-600 mt-1">{gate.blocking_reason}</p>
                    )}
                    {gate.details && !gate.blocking_reason && (
                      <p className="text-sm text-red-600 mt-1">{gate.details}</p>
                    )}
                  </div>
                </li>
              ))}
            </ul>
            <div className="mt-4 p-3 bg-red-100 rounded-md">
              <p className="text-sm text-red-800">
                <strong>Next Steps:</strong> Review the blocking reasons above and modify the TLD string to address the issues before resubmitting.
              </p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
} 