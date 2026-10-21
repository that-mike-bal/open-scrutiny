import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Badge } from './ui/badge'
import { ChevronDown, ChevronUp, Eye, Volume2, Globe, AlertTriangle, CheckCircle, Database } from 'lucide-react'

interface SimilarityMatch {
  tld: string
  similarity_score: number
  similarity_type: 'visual' | 'phonetic' | 'semantic' | 'script_confusion'
  risk_level: 'CLEAR' | 'LOW_RISK' | 'MEDIUM_RISK' | 'HIGH_RISK' | 'BLOCKED'
  confusability_factors: string[]
  recommendation: string
}

interface SimilarityAnalysisData {
  string: string
  overall_risk_level: 'CLEAR' | 'LOW_RISK' | 'MEDIUM_RISK' | 'HIGH_RISK' | 'BLOCKED'
  data_source: 'agent_provided_iana_data' | 'internal_fallback_list'
  data_fresh: boolean
  iana_tlds_analyzed: number
  top_similarities: SimilarityMatch[]
  visual_similarity_results: SimilarityMatch[]
  phonetic_similarity_results: SimilarityMatch[]
  script_confusion_results: SimilarityMatch[]
  conservative_threshold: number
  expert_review_required: boolean
  mitigation_recommendations: string[]
  confidence_score: number
}

interface SimilarityAnalysisResultsProps {
  data: SimilarityAnalysisData
  isLoading?: boolean
}

const getRiskColor = (risk: string) => {
  switch (risk) {
    case 'CLEAR': return 'text-green-600'
    case 'LOW_RISK': return 'text-green-500'
    case 'MEDIUM_RISK': return 'text-yellow-600'
    case 'HIGH_RISK': return 'text-orange-600'
    case 'BLOCKED': return 'text-red-600'
    default: return 'text-gray-600'
  }
}

const getRiskBadgeVariant = (risk: string): "default" | "secondary" | "destructive" | "outline" | "success" | "warning" | "info" => {
  switch (risk) {
    case 'CLEAR': return 'success'
    case 'LOW_RISK': return 'outline'
    case 'MEDIUM_RISK': return 'warning'
    case 'HIGH_RISK': return 'destructive'
    case 'BLOCKED': return 'destructive'
    default: return 'secondary'
  }
}

const getSimilarityTypeIcon = (type: string) => {
  switch (type) {
    case 'visual': return <Eye className="w-4 h-4" />
    case 'phonetic': return <Volume2 className="w-4 h-4" />
    case 'semantic': return <Globe className="w-4 h-4" />
    case 'script_confusion': return <AlertTriangle className="w-4 h-4" />
    default: return <CheckCircle className="w-4 h-4" />
  }
}

function SimilarityMatchCard({ match }: { match: SimilarityMatch }) {
  const [isExpanded, setIsExpanded] = useState(false)

  return (
    <div className="border rounded-lg p-3 hover:bg-gray-50 transition-colors">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-2">
            {getSimilarityTypeIcon(match.similarity_type)}
            <span className="font-medium">.{match.tld}</span>
          </div>
          <Badge variant={getRiskBadgeVariant(match.risk_level)} className="text-xs">
            {match.risk_level.replace('_', ' ')}
          </Badge>
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-sm font-medium">
            {(match.similarity_score * 100).toFixed(1)}%
          </span>
          {match.confusability_factors.length > 0 && (
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

      {isExpanded && (
        <div className="mt-3 space-y-2 border-t pt-3">
          {match.confusability_factors.length > 0 && (
            <div>
              <span className="text-xs font-medium text-gray-600">Confusability Factors:</span>
              <ul className="text-xs text-gray-700 ml-2">
                {match.confusability_factors.map((factor, index) => (
                  <li key={index}>• {factor}</li>
                ))}
              </ul>
            </div>
          )}
          {match.recommendation && (
            <div>
              <span className="text-xs font-medium text-blue-600">Recommendation:</span>
              <p className="text-xs text-blue-700 mt-1">{match.recommendation}</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function SimilarityAnalysisResults({ data, isLoading = false }: SimilarityAnalysisResultsProps) {
  const [activeTab, setActiveTab] = useState<'overview' | 'visual' | 'phonetic' | 'script'>('overview')

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Eye className="w-5 h-5" />
            <span>Similarity Analysis</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="animate-pulse space-y-3">
            <div className="h-4 bg-gray-200 rounded w-1/3"></div>
            <div className="h-4 bg-gray-200 rounded w-2/3"></div>
            <div className="h-4 bg-gray-200 rounded w-1/2"></div>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Overall Status */}
      <Card className={`border-2 ${
        data.overall_risk_level === 'BLOCKED' ? 'border-red-200 bg-red-50' :
        data.overall_risk_level === 'HIGH_RISK' ? 'border-orange-200 bg-orange-50' :
        data.overall_risk_level === 'MEDIUM_RISK' ? 'border-yellow-200 bg-yellow-50' :
        'border-green-200 bg-green-50'
      }`}>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center space-x-2">
              <Eye className="w-5 h-5" />
              <span>Similarity Analysis: .{data.string}</span>
            </CardTitle>
            <Badge variant={getRiskBadgeVariant(data.overall_risk_level)} className="text-sm">
              {data.overall_risk_level.replace('_', ' ')}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className={`text-2xl font-bold ${getRiskColor(data.overall_risk_level)}`}>
                {data.overall_risk_level.replace('_', ' ')}
              </div>
              <div className="text-sm text-gray-600">Overall Risk</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">
                {data.iana_tlds_analyzed}
              </div>
              <div className="text-sm text-gray-600">TLDs Analyzed</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-600">
                {data.top_similarities.length}
              </div>
              <div className="text-sm text-gray-600">Similar TLDs</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">
                {data.confidence_score}%
              </div>
              <div className="text-sm text-gray-600">Confidence</div>
            </div>
          </div>

          {/* Data Source Warning */}
          {!data.data_fresh && (
            <div className="mt-4 p-3 bg-amber-100 border border-amber-200 rounded-md">
              <div className="flex items-center space-x-2">
                <AlertTriangle className="w-4 h-4 text-amber-600" />
                <span className="text-sm text-amber-800 font-medium">Data Integrity Warning</span>
              </div>
              <p className="text-xs text-amber-700 mt-1">
                Analysis used fallback IANA data. For production decisions, fresh data is recommended.
              </p>
            </div>
          )}

          {/* Expert Review Required */}
          {data.expert_review_required && (
            <div className="mt-4 p-3 bg-blue-100 border border-blue-200 rounded-md">
              <div className="flex items-center space-x-2">
                <Database className="w-4 h-4 text-blue-600" />
                <span className="text-sm text-blue-800 font-medium">Expert Review Required</span>
              </div>
              <p className="text-xs text-blue-700 mt-1">
                High similarity scores detected. Professional linguistic review recommended.
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Similarity Details */}
      <Card>
        <CardHeader>
          <CardTitle>Detailed Similarity Analysis</CardTitle>
          <div className="flex space-x-1 mt-4">
            {[
              { key: 'overview', label: 'Top Similarities', count: data.top_similarities.length },
              { key: 'visual', label: 'Visual', count: data.visual_similarity_results.length },
              { key: 'phonetic', label: 'Phonetic', count: data.phonetic_similarity_results.length },
              { key: 'script', label: 'Script Confusion', count: data.script_confusion_results.length }
            ].map(tab => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key as any)}
                className={`px-3 py-2 text-sm rounded-md transition-colors ${
                  activeTab === tab.key
                    ? 'bg-blue-100 text-blue-700 border border-blue-200'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                {tab.label} ({tab.count})
              </button>
            ))}
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {activeTab === 'overview' && (
              <div>
                {data.top_similarities.length > 0 ? (
                  data.top_similarities.map((match, index) => (
                    <SimilarityMatchCard key={index} match={match} />
                  ))
                ) : (
                  <p className="text-gray-500 text-center py-4">No significant similarities detected</p>
                )}
              </div>
            )}

            {activeTab === 'visual' && (
              <div>
                {data.visual_similarity_results.length > 0 ? (
                  data.visual_similarity_results.map((match, index) => (
                    <SimilarityMatchCard key={index} match={match} />
                  ))
                ) : (
                  <p className="text-gray-500 text-center py-4">No visual similarities detected</p>
                )}
              </div>
            )}

            {activeTab === 'phonetic' && (
              <div>
                {data.phonetic_similarity_results.length > 0 ? (
                  data.phonetic_similarity_results.map((match, index) => (
                    <SimilarityMatchCard key={index} match={match} />
                  ))
                ) : (
                  <p className="text-gray-500 text-center py-4">No phonetic similarities detected</p>
                )}
              </div>
            )}

            {activeTab === 'script' && (
              <div>
                {data.script_confusion_results.length > 0 ? (
                  data.script_confusion_results.map((match, index) => (
                    <SimilarityMatchCard key={index} match={match} />
                  ))
                ) : (
                  <p className="text-gray-500 text-center py-4">No script confusion risks detected</p>
                )}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Mitigation Recommendations */}
      {data.mitigation_recommendations.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Mitigation Recommendations</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {data.mitigation_recommendations.map((recommendation, index) => (
                <li key={index} className="flex items-start space-x-2">
                  <CheckCircle className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                  <span className="text-sm">{recommendation}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  )
} 