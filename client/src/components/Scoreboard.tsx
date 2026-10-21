import { useState, useEffect, useMemo } from 'react'
import { formatDistanceToNow } from 'date-fns'
import Navigation from '@/components/Navigation'
import { useNavigate } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { BarChart3, Search, TrendingUp, AlertTriangle, CheckCircle, Clock } from 'lucide-react'
import { useTldEvaluations } from '@/hooks/useTldEvaluations'
import { useSearchEvaluations } from '@/hooks/useSearchEvaluations'
import { useDebounce } from '@/hooks/useDebounce'
import { type TldEvaluationWithAnalysis } from '@/types'

// Types for sorting and filtering
type SortOption = 'string-asc' | 'string-desc' | 'risk-score-asc' | 'risk-score-desc' | 'risk-level-asc' | 'risk-level-desc' | 'date-asc' | 'date-desc'
type RiskFilter = 'all' | 'low' | 'medium' | 'high' | 'critical'
type StatusFilter = 'all' | 'completed' | 'running' | 'failed' | 'pending'

// Extract unified risk data from evaluation
function getUnifiedRiskData(evaluation: TldEvaluationWithAnalysis): { 
  riskScore: number; 
  riskLevel: string; 
  riskSummary: string[];
  confidence: number;
} {
  // Try to get risk assessment from generated_report (new unified system)
  const riskAssessment = evaluation.generated_report?.risk_assessment
  
  if (riskAssessment) {
    return {
      riskScore: Math.round((riskAssessment.risk_score || 1) * 25), // Convert 1-4 scale to 25-100
      riskLevel: riskAssessment.risk_level || 'MEDIUM',
      riskSummary: riskAssessment.summary_points || ['Risk assessment data not available'],
      confidence: riskAssessment.confidence || 0.8
    }
  }
  
  // Legacy fallback - use existing risk data if available
  if (evaluation.risk_score !== undefined) {
    return {
      riskScore: evaluation.risk_score,
      riskLevel: evaluation.risk_level || determineRiskLevel(evaluation.risk_score),
      riskSummary: ['Legacy risk assessment - detailed analysis not available'],
      confidence: 0.6
    }
  }
  
  // Default for evaluations without risk data
  return {
    riskScore: 0,
    riskLevel: 'PENDING',
    riskSummary: ['Risk assessment not yet completed'],
    confidence: 0
  }
}

// Determine risk level from score (legacy compatibility, 25-100 scale)
function determineRiskLevel(riskScore: number): string {
  if (riskScore >= 88) return 'CRITICAL'  // 4 * 25 = 100
  if (riskScore >= 63) return 'HIGH'      // 3 * 25 = 75
  if (riskScore >= 38) return 'MEDIUM'    // 2 * 25 = 50
  return 'LOW'                            // 1 * 25 = 25
}

// Risk level badge component with enhanced color coding
function RiskLevelBadge({ riskLevel, confidence }: { 
  riskLevel: string; 
  riskScore: number;
  confidence?: number;
}) {
  const getVariant = () => {
    switch (riskLevel.toUpperCase()) {
      case 'CRITICAL': return 'destructive'
      case 'HIGH': return 'destructive' 
      case 'MEDIUM': return 'secondary'
      case 'LOW': return 'success'
      default: return 'secondary'
    }
  }

  const getColorClasses = () => {
    switch (riskLevel.toUpperCase()) {
      case 'CRITICAL': return 'bg-red-800 text-white border-red-900 hover:bg-red-900'
      case 'HIGH': return 'bg-red-600 text-white border-red-700 hover:bg-red-700'
      case 'MEDIUM': return 'bg-yellow-500 text-white border-yellow-600 hover:bg-yellow-600'
      case 'LOW': return 'bg-green-600 text-white border-green-700 hover:bg-green-700'
      case 'PENDING': return 'bg-gray-400 text-white border-gray-500 hover:bg-gray-500'
      default: return 'bg-gray-500 text-white border-gray-600 hover:bg-gray-600'
    }
  }

  const getIcon = () => {
    switch (riskLevel.toUpperCase()) {
      case 'CRITICAL': return <AlertTriangle className="w-3 h-3" />
      case 'HIGH': return <TrendingUp className="w-3 h-3" />
      case 'MEDIUM': return <Clock className="w-3 h-3" />
      case 'LOW': return <CheckCircle className="w-3 h-3" />
      default: return <Clock className="w-3 h-3" />
    }
  }

  return (
    <div className="flex items-center gap-2">
      <Badge variant={getVariant()} className={`flex items-center gap-1 ${getColorClasses()}`}>
        {getIcon()}
        {riskLevel.toUpperCase()}
      </Badge>
      {confidence && confidence < 0.7 && (
        <span className="text-xs text-yellow-600" title={`Confidence: ${Math.round(confidence * 100)}%`}>
          ⚠️
        </span>
      )}
    </div>
  )
}

export default function Scoreboard() {
  const navigate = useNavigate()
  const [searchTerm, setSearchTerm] = useState('')
  const [sortBy, setSortBy] = useState<SortOption>('risk-score-desc')
  const [riskFilter, setRiskFilter] = useState<RiskFilter>('all')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')

  const debouncedSearchTerm = useDebounce(searchTerm, 300)

  // Fetch evaluations based on search term
  const {
    searchResults,
    isSearching: searchLoading,
    searchError,
    searchEvaluations
  } = useSearchEvaluations()

  useEffect(() => {
    searchEvaluations(debouncedSearchTerm)
  }, [debouncedSearchTerm, searchEvaluations])

  const {
    evaluations: allEvaluations,
    loading: allLoading,
    error: allError,
    refetch
  } = useTldEvaluations(statusFilter === 'all' ? undefined : statusFilter.toUpperCase())

  // Use search results if searching, otherwise use all evaluations
  const evaluations = debouncedSearchTerm ? searchResults : allEvaluations
  const loading = debouncedSearchTerm ? searchLoading : allLoading
  const error = debouncedSearchTerm ? searchError : allError

  // Process evaluations with unified risk data
  const processedEvaluations = useMemo(() => {
    if (!evaluations) return []

    return evaluations
      .map(evaluation => {
        const riskData = getUnifiedRiskData(evaluation)
        return {
          ...evaluation,
          ...riskData
        }
      })
      .filter(evaluation => {
        // Status filter
        if (statusFilter !== 'all') {
          const status = evaluation.status?.toLowerCase() || evaluation.overall_status?.toLowerCase()
          if (status !== statusFilter) return false
        }

        // Risk filter based on unified risk level
        if (riskFilter !== 'all') {
          const riskLevel = evaluation.riskLevel.toLowerCase()
          if (riskLevel !== riskFilter) return false
        }

        return true
      })
      .sort((a, b) => {
        switch (sortBy) {
          case 'string-asc':
            return a.tld_string.localeCompare(b.tld_string)
          case 'string-desc':
            return b.tld_string.localeCompare(a.tld_string)
          case 'risk-score-asc':
            return a.riskScore - b.riskScore
          case 'risk-score-desc':
            return b.riskScore - a.riskScore
          case 'risk-level-asc':
            return a.riskLevel.localeCompare(b.riskLevel)
          case 'risk-level-desc':
            return b.riskLevel.localeCompare(a.riskLevel)
          case 'date-asc':
            return new Date(a.updated_at).getTime() - new Date(b.updated_at).getTime()
          case 'date-desc':
            return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
          default:
            return b.riskScore - a.riskScore
        }
      })
  }, [evaluations, sortBy, riskFilter, statusFilter])

  // Auto-refresh every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      refetch()
    }, 30000)

    return () => clearInterval(interval)
  }, [refetch])

  // Statistics based on unified risk data
  const stats = useMemo(() => {
    // Get total from all evaluations (not filtered by current criteria)
    const allEvals = allEvaluations || []
    const total = allEvals.length
    
    // Calculate risk distribution from all evaluations
    const riskCounts = { critical: 0, high: 0, medium: 0, low: 0, pending: 0 }
    let totalScore = 0
    let scoredCount = 0

    allEvals.forEach(evaluation => {
      const riskData = getUnifiedRiskData(evaluation)

      switch (riskData.riskLevel.toUpperCase()) {
        case 'CRITICAL': riskCounts.critical++; break
        case 'HIGH': riskCounts.high++; break
        case 'MEDIUM': riskCounts.medium++; break
        case 'LOW': riskCounts.low++; break
        default: riskCounts.pending++; break
      }

      // Only include scored evaluations in average
      if (riskData.riskScore > 0) {
        totalScore += riskData.riskScore
        scoredCount++
      }
    })

    const avgScore = scoredCount > 0 ? Math.round(totalScore / scoredCount) : 0

    return { 
      total, 
      criticalRisk: riskCounts.critical,
      highRisk: riskCounts.high, 
      mediumRisk: riskCounts.medium,
      lowRisk: riskCounts.low,
      avgScore,
      filtered: processedEvaluations.length
    }
  }, [allEvaluations, processedEvaluations])

  return (
    <div className="min-h-screen bg-gray-50">
      <Navigation />
      
      <div className="container mx-auto px-4 py-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-3">
            <BarChart3 className="w-8 h-8 text-blue-600" />
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Risk Scoreboard</h1>
              <p className="text-gray-600">TLD evaluations with AI-powered risk assessment</p>
            </div>
          </div>
          <Button 
            onClick={() => refetch()} 
            variant="outline"
            className="flex items-center gap-2"
          >
            <TrendingUp className="w-4 h-4" />
            Refresh Data
          </Button>
        </div>

        {/* Statistics Cards */}
        <div className="grid grid-cols-1 md:grid-cols-6 gap-4 mb-6">
          <Card>
            <CardContent className="pt-6">
              <div className="text-2xl font-bold">{stats.total}</div>
              <p className="text-xs text-muted-foreground">Total Evaluations</p>
              {stats.filtered !== stats.total && (
                <p className="text-xs text-blue-600">({stats.filtered} filtered)</p>
              )}
            </CardContent>
          </Card>
          <Card className="border-red-200 bg-red-50">
            <CardContent className="pt-6">
              <div className="text-2xl font-bold text-red-800">{stats.criticalRisk}</div>
              <p className="text-xs text-muted-foreground">Critical Risk</p>
            </CardContent>
          </Card>
          <Card className="border-red-200 bg-red-50">
            <CardContent className="pt-6">
              <div className="text-2xl font-bold text-red-600">{stats.highRisk}</div>
              <p className="text-xs text-muted-foreground">High Risk</p>
            </CardContent>
          </Card>
          <Card className="border-yellow-200 bg-yellow-50">
            <CardContent className="pt-6">
              <div className="text-2xl font-bold text-yellow-600">{stats.mediumRisk}</div>
              <p className="text-xs text-muted-foreground">Moderate Risk</p>
            </CardContent>
          </Card>
          <Card className="border-green-200 bg-green-50">
            <CardContent className="pt-6">
              <div className="text-2xl font-bold text-green-600">{stats.lowRisk}</div>
              <p className="text-xs text-muted-foreground">Low Risk</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="text-2xl font-bold">{stats.avgScore}</div>
              <p className="text-xs text-muted-foreground">Average Risk Score</p>
            </CardContent>
          </Card>
        </div>

        {/* Filters and Search */}
        <Card className="mb-6">
          <CardContent className="pt-6">
            <div className="flex flex-wrap gap-4">
              <div className="flex-1 min-w-64">
                <div className="relative">
                  <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                  <Input
                    placeholder="Search TLD strings..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="pl-10"
                  />
                </div>
              </div>
              
              <Select value={sortBy} onValueChange={(value: SortOption) => setSortBy(value)}>
                <SelectTrigger className="w-48">
                  <SelectValue placeholder="Sort by" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="risk-score-desc">Risk Score (High to Low)</SelectItem>
                  <SelectItem value="risk-score-asc">Risk Score (Low to High)</SelectItem>
                  <SelectItem value="string-asc">String (A to Z)</SelectItem>
                  <SelectItem value="string-desc">String (Z to A)</SelectItem>
                  <SelectItem value="date-desc">Recently Updated</SelectItem>
                  <SelectItem value="date-asc">Oldest First</SelectItem>
                </SelectContent>
              </Select>

              <Select value={riskFilter} onValueChange={(value: RiskFilter) => setRiskFilter(value)}>
                <SelectTrigger className="w-32">
                  <SelectValue placeholder="Risk Level" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Risks</SelectItem>
                  <SelectItem value="low">Low</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                  <SelectItem value="critical">Critical</SelectItem>
                </SelectContent>
              </Select>

              <Select value={statusFilter} onValueChange={(value: StatusFilter) => setStatusFilter(value)}>
                <SelectTrigger className="w-32">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="completed">Completed</SelectItem>
                  <SelectItem value="running">Running</SelectItem>
                  <SelectItem value="failed">Failed</SelectItem>
                  <SelectItem value="pending">Pending</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Results Table */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span>Risk Assessment Results ({processedEvaluations.length})</span>
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="text-xs">AI-Powered Assessment</Badge>
                <Badge variant="outline">Auto-refreshes every 30s</Badge>
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <div className="text-center">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
                  <p className="text-gray-500">Loading evaluations...</p>
                </div>
              </div>
            ) : error ? (
              <div className="text-center py-8">
                <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-2" />
                <p className="text-red-600 mb-4">Error loading evaluations: {error}</p>
                <Button onClick={() => refetch()} variant="outline">
                  Try Again
                </Button>
              </div>
            ) : processedEvaluations.length === 0 ? (
              <div className="text-center py-8">
                <BarChart3 className="w-12 h-12 text-gray-400 mx-auto mb-2" />
                <p className="text-gray-500">No evaluations found matching your criteria</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left py-3 px-4 font-medium">TLD String</th>
                      <th className="text-left py-3 px-4 font-medium">Risk Level</th>
                      <th className="text-left py-3 px-4 font-medium">Risk Score</th>
                      <th className="text-left py-3 px-4 font-medium">Top Risk Factors</th>
                      <th className="text-left py-3 px-4 font-medium">Last Updated</th>
                    </tr>
                  </thead>
                  <tbody>
                    {processedEvaluations.map((evaluation) => (
                      <tr 
                        key={evaluation.id} 
                        className="border-b hover:bg-gray-50 cursor-pointer"
                        onClick={() => navigate(`/evaluation/${evaluation.tld_string}`)}
                      >
                        <td className="py-3 px-4">
                          <div className="font-medium text-blue-600">
                            .{evaluation.tld_string}
                          </div>
                          {evaluation.use_case && (
                            <div className="text-sm text-gray-500 mt-1">
                              {evaluation.use_case}
                            </div>
                          )}
                        </td>
                        <td className="py-3 px-4">
                          <RiskLevelBadge 
                            riskLevel={evaluation.riskLevel}
                            riskScore={evaluation.riskScore}
                            confidence={evaluation.confidence}
                          />
                        </td>
                        <td className="py-3 px-4">
                          {evaluation.riskScore > 0 ? (
                            <div className="flex items-center gap-2">
                              <span className={`font-bold text-lg ${
                                evaluation.riskScore >= 76 ? 'text-red-800' :
                                evaluation.riskScore >= 51 ? 'text-red-600' :
                                evaluation.riskScore >= 26 ? 'text-yellow-600' :
                                'text-green-600'
                              }`}>
                                {evaluation.riskScore}
                              </span>
                              <span className="text-gray-500 text-sm">/100</span>
                            </div>
                          ) : (
                            <span className="text-gray-400 text-sm italic">Pending</span>
                          )}
                        </td>
                        <td className="py-3 px-4">
                          <div className="text-sm text-gray-700 max-w-md">
                            <ul className="space-y-1">
                              {evaluation.riskSummary.slice(0, 3).map((risk, index) => (
                                <li key={index} className="flex items-start gap-1">
                                  <span className="text-gray-400 mt-1 text-xs">•</span>
                                  <span className="leading-tight">{risk}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        </td>
                        <td className="py-3 px-4 text-sm text-gray-500">
                          {formatDistanceToNow(new Date(evaluation.updated_at), { addSuffix: true })}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}