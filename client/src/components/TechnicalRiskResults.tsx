import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Badge } from './ui/badge'
import { Button } from './ui/button'
import { 
  CheckCircle, 
  XCircle, 
  AlertTriangle, 
  ChevronDown, 
  ChevronUp, 
  Shield, 
  Zap, 
  Eye,
  AlertCircle,
  TrendingUp,
  FileText,
  Clock,
  Target,
  Database,
  Network
} from 'lucide-react'

interface TechnicalRiskResult {
  task_name: string
  agent_name: string
  result_status: 'PASS' | 'FAIL' | 'BLOCKED' | 'REVIEW_REQUIRED' | 'CLEAR' | 'LOW_RISK' | 'MEDIUM_RISK' | 'HIGH_RISK'
  result_data: {
    output?: string
    risk_score?: number
    risk_level?: string
    magnitude_score?: number
    similarity_status?: string
    collision_evidence?: string[]
    technical_compliance?: string
    dns_violations?: string[]
    similarity_scores?: Array<{
      tld: string
      score: number
    }>
    confidence?: number
    recommendations?: string[]
  }
  confidence_score?: number
  completed_at: string
}

interface TechnicalRiskResultsProps {
  results: TechnicalRiskResult[]
  tldString: string
}

// Helper function to parse markdown content and extract structured information
const parseTaskOutput = (output: string) => {
  if (!output) return null

  const sections: { [key: string]: string } = {}
  const lines = output.split('\n')
  let currentSection = ''
  let currentContent: string[] = []

  for (const line of lines) {
    // Check for section headers (markdown headers)
    if (line.startsWith('#')) {
      // Save previous section
      if (currentSection && currentContent.length > 0) {
        sections[currentSection] = currentContent.join('\n').trim()
      }
      // Start new section
      currentSection = line.replace(/^#+\s*/, '').replace(/\*\*/g, '').trim()
      currentContent = []
    } else if (currentSection) {
      currentContent.push(line)
    }
  }
  
  // Save final section
  if (currentSection && currentContent.length > 0) {
    sections[currentSection] = currentContent.join('\n').trim()
  }

  return sections
}

// Helper function to extract key metrics from parsed content
const extractMetrics = (sections: { [key: string]: string }, taskName: string) => {
  const metrics: { [key: string]: any } = {}

  if (taskName === 'dns_stability_review') {
    // Extract DNS-specific metrics
    Object.entries(sections).forEach(([sectionName, content]) => {
      if (sectionName.includes('RISK ASSESSMENT SUMMARY')) {
        const riskScoreMatch = content.match(/Overall Risk Score.*?(\d+)/i)
        if (riskScoreMatch) metrics.riskScore = parseInt(riskScoreMatch[1])
        
        const statusMatch = content.match(/Binary Status.*?(PASS|BLOCKED|CLEAR)/i)
        if (statusMatch) metrics.binaryStatus = statusMatch[1]
        
        const complianceMatch = content.match(/Technical Compliance.*?(COMPLIANT|NON-COMPLIANT)/i)
        if (complianceMatch) metrics.technicalCompliance = complianceMatch[1]
      }
      
      if (sectionName.includes('RFC Standards Compliance')) {
        const rfcMatches = content.match(/RFC \d+.*?(COMPLIANT|NON-COMPLIANT)/gi)
        if (rfcMatches) {
          metrics.rfcCompliance = rfcMatches.map(match => {
            const parts = match.split(':')
            return {
              rfc: parts[0]?.trim() || '',
              status: parts[1]?.trim() || match.includes('COMPLIANT') ? 'COMPLIANT' : 'NON-COMPLIANT'
            }
          })
        }
      }
    })
  }

  if (taskName === 'name_collision_assessment') {
    Object.entries(sections).forEach(([sectionName, content]) => {
      if (sectionName.includes('COLLISION RISK SUMMARY')) {
        const riskScoreMatch = content.match(/Overall Risk Score.*?(\d+)/i)
        if (riskScoreMatch) metrics.riskScore = parseInt(riskScoreMatch[1])
        
        const collisionStatusMatch = content.match(/Collision Status.*?(CLEAR|BLOCKED|WARNING)/i)
        if (collisionStatusMatch) metrics.collisionStatus = collisionStatusMatch[1]
        
                 const magnitudeMatch = content.match(/Magnitude Score.*?(\d+\.?\d*|N\/A)/i)
         if (magnitudeMatch) {
           metrics.magnitudeScore = magnitudeMatch[1] === 'N/A' ? undefined : parseFloat(magnitudeMatch[1])
         }
      }
      
      if (sectionName.includes('ICANN DNS Magnitude Database Analysis')) {
        const queryVolumeMatch = content.match(/Query Volume.*?([^\n\r]+)/i)
        if (queryVolumeMatch) metrics.queryVolume = queryVolumeMatch[1].trim()
        
        const trafficMatch = content.match(/Traffic Pattern.*?([^\n\r]+)/i)
        if (trafficMatch) metrics.trafficPattern = trafficMatch[1].trim()
      }
    })
  }

  if (taskName === 'comprehensive_similarity_analysis') {
    // Handle similarity analysis (which may have data issues)
    if (sections['Data Integrity Issue'] || Object.values(sections).some(content => 
      content.includes('IANA_TLD_LIST not provided') || content.includes('DATA ERROR'))) {
      metrics.dataError = true
      metrics.errorReason = 'IANA data unavailable for similarity analysis'
    }
  }

  return metrics
}

const getRiskColor = (status: string, riskScore?: number) => {
  if (status === 'BLOCKED' || status === 'FAIL') return 'text-red-600 bg-red-50 border-red-200'
  if (status === 'REVIEW_REQUIRED') return 'text-amber-600 bg-amber-50 border-amber-200'
  if (status === 'PASS' || status === 'CLEAR') return 'text-green-600 bg-green-50 border-green-200'
  
  if (riskScore) {
    if (riskScore >= 4) return 'text-red-600 bg-red-50 border-red-200'
    if (riskScore >= 3) return 'text-orange-600 bg-orange-50 border-orange-200'
    if (riskScore >= 2) return 'text-yellow-600 bg-yellow-50 border-yellow-200'
    return 'text-green-600 bg-green-50 border-green-200'
  }
  
  switch (status) {
    case 'HIGH_RISK': return 'text-red-600 bg-red-50 border-red-200'
    case 'MEDIUM_RISK': return 'text-orange-600 bg-orange-50 border-orange-200'
    case 'LOW_RISK': return 'text-yellow-600 bg-yellow-50 border-yellow-200'
    default: return 'text-gray-600 bg-gray-50 border-gray-200'
  }
}

const getRiskIcon = (status: string, riskScore?: number) => {
  if (status === 'BLOCKED' || status === 'FAIL') return <XCircle className="w-5 h-5" />
  if (status === 'REVIEW_REQUIRED') return <AlertTriangle className="w-5 h-5" />
  if (status === 'PASS' || status === 'CLEAR') return <CheckCircle className="w-5 h-5" />
  
  if (riskScore) {
    if (riskScore >= 4) return <XCircle className="w-5 h-5" />
    if (riskScore >= 3) return <AlertTriangle className="w-5 h-5" />
    if (riskScore >= 2) return <AlertCircle className="w-5 h-5" />
    return <CheckCircle className="w-5 h-5" />
  }
  
  switch (status) {
    case 'HIGH_RISK': return <XCircle className="w-5 h-5" />
    case 'MEDIUM_RISK': return <AlertTriangle className="w-5 h-5" />
    case 'LOW_RISK': return <AlertCircle className="w-5 h-5" />
    default: return <Shield className="w-5 h-5" />
  }
}

const getRiskBadgeVariant = (status: string, riskScore?: number): "default" | "secondary" | "destructive" | "outline" | "success" | "warning" | "info" => {
  if (status === 'BLOCKED' || status === 'FAIL') return 'destructive'
  if (status === 'REVIEW_REQUIRED') return 'warning'
  if (status === 'PASS' || status === 'CLEAR') return 'success'
  
  if (riskScore) {
    if (riskScore >= 4) return 'destructive'
    if (riskScore >= 3) return 'warning'
    if (riskScore >= 2) return 'secondary'
    return 'success'
  }
  
  switch (status) {
    case 'HIGH_RISK': return 'destructive'
    case 'MEDIUM_RISK': return 'warning'
    case 'LOW_RISK': return 'secondary'
    default: return 'outline'
  }
}

const getTaskDisplayName = (taskName: string) => {
  switch (taskName) {
    case 'dns_stability_review': return 'DNS Stability Review'
    case 'name_collision_assessment': return 'Name Collision Assessment'
    case 'comprehensive_similarity_analysis': return 'Similarity Analysis'
    case 'findings_validation': return 'Findings Validation'
    default: return taskName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
  }
}

const getTaskIcon = (taskName: string) => {
  switch (taskName) {
    case 'dns_stability_review': return <Shield className="w-4 h-4" />
    case 'name_collision_assessment': return <Zap className="w-4 h-4" />
    case 'comprehensive_similarity_analysis': return <Eye className="w-4 h-4" />
    case 'findings_validation': return <CheckCircle className="w-4 h-4" />
    default: return <TrendingUp className="w-4 h-4" />
  }
}

function TechnicalRiskCard({ result, tldString }: { result: TechnicalRiskResult; tldString: string }) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [detailedOutput, setDetailedOutput] = useState<string | null>(null)
  const [loadingDetails, setLoadingDetails] = useState(false)
  
  const riskScore = result.result_data.risk_score
  const riskLevel = result.result_data.risk_level || result.result_status
  const colorClass = getRiskColor(result.result_status, riskScore)
  const icon = getRiskIcon(result.result_status, riskScore)
  const badgeVariant = getRiskBadgeVariant(result.result_status, riskScore)

  // Parse the output to extract structured information
  const outputToUse = detailedOutput || result.result_data.output
  const parsedSections = outputToUse ? parseTaskOutput(outputToUse) : null
  const extractedMetrics = parsedSections ? extractMetrics(parsedSections, result.task_name) : {}

  // Handle null values for risk score
  const displayRiskScore = riskScore ?? extractedMetrics.riskScore ?? undefined

  // Function to load detailed output from markdown file
  const loadDetailedOutput = async (tldString: string) => {
    if (detailedOutput || loadingDetails) return // Already loaded or loading
    
    setLoadingDetails(true)
    try {
      const response = await fetch(`/api/crewai/outputs/${result.task_name}_${tldString}.md`)
      if (response.ok) {
        const markdown = await response.text()
        setDetailedOutput(markdown)
      }
    } catch (error) {
      console.error('Failed to load detailed output:', error)
    } finally {
      setLoadingDetails(false)
    }
  }

  // Load detailed output when expanded
  const handleExpand = () => {
    setIsExpanded(!isExpanded)
    if (!isExpanded && !detailedOutput) {
      // Extract TLD string from somewhere - we'll need to pass this as a prop
      // For now, we'll try to infer it from the context or use a placeholder
             loadDetailedOutput(tldString)
    }
  }

  return (
    <Card className={`border-2 ${colorClass}`}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            {getTaskIcon(result.task_name)}
            <div>
              <CardTitle className="text-lg">{getTaskDisplayName(result.task_name)}</CardTitle>
              <p className="text-sm text-muted-foreground">{result.agent_name}</p>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            {/* Risk Score */}
            {displayRiskScore && (
              <div className="text-center">
                <div className="text-2xl font-bold">{displayRiskScore}</div>
                <div className="text-xs text-muted-foreground">Risk Score</div>
              </div>
            )}
            
            {/* Status Badge */}
            <div className="flex flex-col items-center space-y-1">
              <div className={`flex items-center justify-center w-12 h-12 rounded-full ${colorClass}`}>
                {icon}
              </div>
              <Badge variant={badgeVariant} className="text-xs">
                {riskLevel}
              </Badge>
            </div>
            
            {/* Expand Button */}
            <Button
              variant="ghost"
              size="sm"
              onClick={handleExpand}
              disabled={loadingDetails}
            >
              {loadingDetails ? (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600"></div>
              ) : isExpanded ? (
                <ChevronUp className="w-4 h-4" />
              ) : (
                <ChevronDown className="w-4 h-4" />
              )}
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent>
        {/* Quick Summary */}
        <div className="space-y-2">
          {/* Task-specific key metrics */}
          {result.task_name === 'dns_stability_review' && (
            <>
              {extractedMetrics.technicalCompliance && (
                <div className="flex justify-between text-sm">
                  <span className="font-medium">Technical Compliance:</span>
                  <Badge variant={extractedMetrics.technicalCompliance === 'COMPLIANT' ? 'success' : 'destructive'} className="text-xs">
                    {extractedMetrics.technicalCompliance}
                  </Badge>
                </div>
              )}
              {extractedMetrics.binaryStatus && (
                <div className="flex justify-between text-sm">
                  <span className="font-medium">Binary Status:</span>
                  <Badge variant={extractedMetrics.binaryStatus === 'PASS' ? 'success' : 'destructive'} className="text-xs">
                    {extractedMetrics.binaryStatus}
                  </Badge>
                </div>
              )}
            </>
          )}

          {result.task_name === 'name_collision_assessment' && (
            <>
              {extractedMetrics.collisionStatus && (
                <div className="flex justify-between text-sm">
                  <span className="font-medium">Collision Status:</span>
                  <Badge variant={extractedMetrics.collisionStatus === 'CLEAR' ? 'success' : 'warning'} className="text-xs">
                    {extractedMetrics.collisionStatus}
                  </Badge>
                </div>
              )}
                             {extractedMetrics.magnitudeScore !== undefined && (
                 <div className="flex justify-between text-sm">
                   <span className="font-medium">Magnitude Score:</span>
                   <span>{extractedMetrics.magnitudeScore ?? 'N/A'}</span>
                 </div>
               )}
            </>
          )}

          {result.task_name === 'comprehensive_similarity_analysis' && extractedMetrics.dataError && (
            <div className="flex items-center space-x-2 text-sm">
              <AlertTriangle className="w-4 h-4 text-orange-500" />
              <span className="text-orange-700">Data Error: {extractedMetrics.errorReason}</span>
            </div>
          )}

          {/* Legacy fields */}
          {result.result_data.magnitude_score !== undefined && (
            <div className="flex justify-between text-sm">
              <span className="font-medium">Magnitude Score:</span>
              <span>{result.result_data.magnitude_score || 'Not Found'}</span>
            </div>
          )}
          
          {result.result_data.similarity_status && (
            <div className="flex justify-between text-sm">
              <span className="font-medium">Similarity Status:</span>
              <span>{result.result_data.similarity_status}</span>
            </div>
          )}
          
          {result.result_data.technical_compliance && (
            <div className="flex justify-between text-sm">
              <span className="font-medium">Technical Compliance:</span>
              <span>{result.result_data.technical_compliance}</span>
            </div>
          )}
          
          {result.confidence_score && (
            <div className="flex justify-between text-sm">
              <span className="font-medium">Confidence:</span>
              <span>{result.confidence_score}%</span>
            </div>
          )}
        </div>

        {/* Expandable Details */}
        {isExpanded && (
          <div className="mt-4 space-y-4 border-t pt-4">
            {/* Enhanced Parsed Content Display */}
            {parsedSections && Object.keys(parsedSections).length > 0 && (
              <div>
                <h4 className="font-medium text-sm mb-3 flex items-center space-x-2">
                  <FileText className="w-4 h-4" />
                  <span>Detailed Assessment</span>
                </h4>
                <div className="space-y-3">
                  {Object.entries(parsedSections).map(([sectionName, content], index) => {
                    // Skip empty sections
                    if (!content.trim()) return null
                    
                    return (
                      <div key={index} className="bg-gray-50 rounded-md p-3 border-l-4 border-blue-500">
                        <h5 className="font-medium text-xs text-blue-900 mb-2 uppercase tracking-wide">
                          {sectionName}
                        </h5>
                        <div className="text-xs text-gray-700 whitespace-pre-wrap">
                          {content}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {/* RFC Compliance Details (for DNS tasks) */}
            {result.task_name === 'dns_stability_review' && extractedMetrics.rfcCompliance && (
              <div>
                <h4 className="font-medium text-sm mb-2 flex items-center space-x-2">
                  <Network className="w-4 h-4" />
                  <span>RFC Standards Compliance</span>
                </h4>
                <div className="space-y-1">
                  {extractedMetrics.rfcCompliance.map((rfc: any, index: number) => (
                    <div key={index} className="flex justify-between items-center text-xs bg-white rounded p-2">
                      <span className="font-mono">{rfc.rfc}</span>
                      <Badge variant={rfc.status === 'COMPLIANT' ? 'success' : 'destructive'} className="text-xs">
                        {rfc.status}
                      </Badge>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Collision Analysis Details */}
            {result.task_name === 'name_collision_assessment' && (
              <div className="space-y-3">
                {extractedMetrics.queryVolume && (
                  <div>
                    <h4 className="font-medium text-sm mb-2 flex items-center space-x-2">
                      <Database className="w-4 h-4" />
                      <span>Query Volume Analysis</span>
                    </h4>
                    <div className="bg-white rounded p-2 text-xs">
                      {extractedMetrics.queryVolume}
                    </div>
                  </div>
                )}
                
                {extractedMetrics.trafficPattern && (
                  <div>
                    <h4 className="font-medium text-sm mb-2 flex items-center space-x-2">
                      <TrendingUp className="w-4 h-4" />
                      <span>Traffic Pattern Assessment</span>
                    </h4>
                    <div className="bg-white rounded p-2 text-xs">
                      {extractedMetrics.trafficPattern}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Legacy detailed sections */}
            {/* Collision Evidence */}
            {result.result_data.collision_evidence && result.result_data.collision_evidence.length > 0 && (
              <div>
                <h4 className="font-medium text-sm mb-2">Collision Evidence</h4>
                <ul className="text-xs space-y-1">
                  {result.result_data.collision_evidence.map((evidence, index) => (
                    <li key={index} className="flex items-start space-x-2">
                      <span className="text-gray-400">•</span>
                      <span>{evidence}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* DNS Violations */}
            {result.result_data.dns_violations && result.result_data.dns_violations.length > 0 && (
              <div>
                <h4 className="font-medium text-sm mb-2">DNS Violations</h4>
                <ul className="text-xs space-y-1">
                  {result.result_data.dns_violations.map((violation, index) => (
                    <li key={index} className="flex items-start space-x-2">
                      <span className="text-red-400">⚠</span>
                      <span className="text-red-700">{violation}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Similarity Scores */}
            {result.result_data.similarity_scores && result.result_data.similarity_scores.length > 0 && (
              <div>
                <h4 className="font-medium text-sm mb-2">Top Similar TLDs</h4>
                <div className="space-y-1">
                  {result.result_data.similarity_scores.slice(0, 5).map((sim, index) => (
                    <div key={index} className="flex justify-between items-center text-xs">
                      <span className="font-mono">.{sim.tld}</span>
                      <div className="flex items-center space-x-2">
                        <div className="w-20 bg-gray-200 rounded-full h-2">
                          <div 
                            className={`h-2 rounded-full ${
                              sim.score > 0.8 ? 'bg-red-500' : 
                              sim.score > 0.6 ? 'bg-orange-500' : 
                              sim.score > 0.4 ? 'bg-yellow-500' : 'bg-green-500'
                            }`}
                            style={{ width: `${sim.score * 100}%` }}
                          ></div>
                        </div>
                        <span className="font-mono w-12 text-right">{sim.score.toFixed(3)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Recommendations */}
            {result.result_data.recommendations && result.result_data.recommendations.length > 0 && (
              <div>
                <h4 className="font-medium text-sm mb-2">Recommendations</h4>
                <ul className="text-xs space-y-1">
                  {result.result_data.recommendations.map((rec, index) => (
                    <li key={index} className="flex items-start space-x-2">
                      <span className="text-blue-400">→</span>
                      <span>{rec}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Fallback for raw output if no parsed sections */}
            {!parsedSections && result.result_data.output && (
              <div>
                <h4 className="font-medium text-sm mb-2">Raw Analysis Output</h4>
                <div className="bg-gray-50 rounded-md p-3">
                  <pre className="text-xs text-gray-700 whitespace-pre-wrap">
                    {result.result_data.output}
                  </pre>
                </div>
              </div>
            )}

            {/* Technical Details */}
            <div className="text-xs text-muted-foreground border-t pt-2">
              <div className="flex justify-between items-center">
                <div className="flex items-center space-x-4">
                  <div className="flex items-center space-x-1">
                    <Clock className="w-3 h-3" />
                    <span>Completed: {new Date(result.completed_at).toLocaleString()}</span>
                  </div>
                  {(result.result_data.confidence || extractedMetrics.confidence) && (
                    <div className="flex items-center space-x-1">
                      <Target className="w-3 h-3" />
                      <span>Confidence: {result.result_data.confidence || extractedMetrics.confidence}%</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default function TechnicalRiskResults({ results, tldString }: TechnicalRiskResultsProps) {
  // Calculate overall risk score
  const riskScores = results
    .map(r => r.result_data.risk_score)
    .filter((score): score is number => score !== undefined)
  
  const avgRiskScore = riskScores.length > 0 
    ? riskScores.reduce((a, b) => a + b, 0) / riskScores.length 
    : undefined

  const hasBlockedResults = results.some(r => r.result_status === 'BLOCKED')
  const hasHighRiskResults = results.some(r => 
    r.result_status === 'HIGH_RISK' || (r.result_data.risk_score && r.result_data.risk_score >= 4)
  )

  const overallStatus = hasBlockedResults ? 'BLOCKED' : 
                       hasHighRiskResults ? 'HIGH_RISK' : 
                       avgRiskScore && avgRiskScore >= 3 ? 'MEDIUM_RISK' : 'LOW_RISK'

  return (
    <div className="space-y-6">
      {/* Overall Summary */}
      <Card className={`border-2 ${getRiskColor(overallStatus, avgRiskScore)}`}>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              {getRiskIcon(overallStatus, avgRiskScore)}
              <div>
                <CardTitle className="text-xl">
                  Technical Risk Assessment: .{tldString}
                </CardTitle>
                <p className="text-sm text-muted-foreground">
                  {results.length} technical analysis tasks completed
                </p>
              </div>
            </div>
            <div className="text-right">
              {avgRiskScore && (
                <div className="text-center mb-2">
                  <div className="text-3xl font-bold">{avgRiskScore.toFixed(1)}</div>
                  <div className="text-xs text-muted-foreground">Avg Risk Score</div>
                </div>
              )}
              <Badge variant={getRiskBadgeVariant(overallStatus, avgRiskScore)} className="text-sm">
                {overallStatus.replace('_', ' ')}
              </Badge>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Individual Risk Assessments */}
      <div className="grid grid-cols-1 gap-4">
        {results.map((result, index) => (
          <TechnicalRiskCard key={index} result={result} tldString={tldString} />
        ))}
      </div>

      {/* Risk Summary */}
      {hasBlockedResults && (
        <Card className="border-red-200 bg-red-50">
          <CardHeader>
            <CardTitle className="text-red-800 flex items-center space-x-2">
              <XCircle className="w-5 h-5" />
              <span>Technical Issues Detected</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-red-700 text-sm">
              One or more technical assessments have identified blocking issues that require attention before proceeding.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  )
} 