import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Badge } from './ui/badge'
import { ChevronDown, ChevronUp, Shield, Globe, AlertTriangle, CheckCircle, Scale, Building } from 'lucide-react'

interface TrademarkConflict {
  trademark: string
  jurisdiction: 'USPTO' | 'EUIPO' | 'WIPO' | 'Other'
  registration_number: string
  owner: string
  class_description: string
  similarity_score: number
  conflict_type: 'exact_match' | 'similar' | 'phonetic' | 'conceptual'
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  legal_recommendation: string
  status: 'active' | 'pending' | 'expired' | 'abandoned'
}

interface TrademarkAssessmentData {
  string: string
  overall_risk_level: 'CLEAR' | 'LOW_RISK' | 'MEDIUM_RISK' | 'HIGH_RISK' | 'BLOCKED'
  total_conflicts_found: number
  jurisdictions_searched: string[]
  search_threshold: number
  conflicts_by_jurisdiction: {
    USPTO: TrademarkConflict[]
    EUIPO: TrademarkConflict[]
    WIPO: TrademarkConflict[]
    Other: TrademarkConflict[]
  }
  brand_protection_recommendations: string[]
  defensive_strategies: string[]
  legal_review_required: boolean
  confidence_score: number
  search_date: string
}

interface TrademarkAssessmentResultsProps {
  data: TrademarkAssessmentData
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
    case 'LOW': return 'outline'
    case 'MEDIUM': return 'warning'
    case 'HIGH': return 'destructive'
    case 'CRITICAL': return 'destructive'
    default: return 'secondary'
  }
}

const getJurisdictionIcon = (jurisdiction: string) => {
  switch (jurisdiction) {
    case 'USPTO': return <Building className="w-4 h-4 text-blue-600" />
    case 'EUIPO': return <Globe className="w-4 h-4 text-green-600" />
    case 'WIPO': return <Scale className="w-4 h-4 text-purple-600" />
    default: return <Shield className="w-4 h-4 text-gray-600" />
  }
}

const getConflictTypeColor = (type: string) => {
  switch (type) {
    case 'exact_match': return 'text-red-600'
    case 'similar': return 'text-orange-600'
    case 'phonetic': return 'text-yellow-600'
    case 'conceptual': return 'text-blue-600'
    default: return 'text-gray-600'
  }
}

function TrademarkConflictCard({ conflict }: { conflict: TrademarkConflict }) {
  const [isExpanded, setIsExpanded] = useState(false)

  return (
    <div className="border rounded-lg p-3 hover:bg-gray-50 transition-colors">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-2">
            {getJurisdictionIcon(conflict.jurisdiction)}
            <span className="font-medium">{conflict.trademark}</span>
          </div>
          <Badge variant={getRiskBadgeVariant(conflict.risk_level)} className="text-xs">
            {conflict.risk_level} RISK
          </Badge>
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-sm font-medium">
            {(conflict.similarity_score * 100).toFixed(0)}%
          </span>
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
        </div>
      </div>

      {isExpanded && (
        <div className="mt-3 space-y-3 border-t pt-3">
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div>
              <span className="font-medium text-gray-600">Owner:</span>
              <p className="text-gray-800">{conflict.owner}</p>
            </div>
            <div>
              <span className="font-medium text-gray-600">Registration:</span>
              <p className="text-gray-800">{conflict.registration_number}</p>
            </div>
            <div>
              <span className="font-medium text-gray-600">Status:</span>
              <Badge variant={conflict.status === 'active' ? 'success' : 'secondary'} className="text-xs">
                {conflict.status}
              </Badge>
            </div>
            <div>
              <span className="font-medium text-gray-600">Conflict Type:</span>
              <span className={`text-xs font-medium ${getConflictTypeColor(conflict.conflict_type)}`}>
                {conflict.conflict_type.replace('_', ' ')}
              </span>
            </div>
          </div>
          
          <div>
            <span className="text-xs font-medium text-gray-600">Class Description:</span>
            <p className="text-xs text-gray-700 mt-1">{conflict.class_description}</p>
          </div>

          {conflict.legal_recommendation && (
            <div>
              <span className="text-xs font-medium text-blue-600">Legal Recommendation:</span>
              <p className="text-xs text-blue-700 mt-1 bg-blue-50 p-2 rounded">
                {conflict.legal_recommendation}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function TrademarkAssessmentResults({ data, isLoading = false }: TrademarkAssessmentResultsProps) {
  const [activeJurisdiction, setActiveJurisdiction] = useState<'all' | 'USPTO' | 'EUIPO' | 'WIPO' | 'Other'>('all')

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Scale className="w-5 h-5" />
            <span>Trademark Assessment</span>
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

  const getAllConflicts = () => {
    return [
      ...data.conflicts_by_jurisdiction.USPTO,
      ...data.conflicts_by_jurisdiction.EUIPO,
      ...data.conflicts_by_jurisdiction.WIPO,
      ...data.conflicts_by_jurisdiction.Other
    ]
  }

  const getFilteredConflicts = () => {
    if (activeJurisdiction === 'all') {
      return getAllConflicts()
    }
    return data.conflicts_by_jurisdiction[activeJurisdiction] || []
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
              <Scale className="w-5 h-5" />
              <span>Trademark Assessment: .{data.string}</span>
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
              <div className="text-2xl font-bold text-red-600">
                {data.total_conflicts_found}
              </div>
              <div className="text-sm text-gray-600">Conflicts Found</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">
                {data.jurisdictions_searched.length}
              </div>
              <div className="text-sm text-gray-600">Jurisdictions</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">
                {data.confidence_score}%
              </div>
              <div className="text-sm text-gray-600">Confidence</div>
            </div>
          </div>

          {/* Legal Review Required */}
          {data.legal_review_required && (
            <div className="mt-4 p-3 bg-red-100 border border-red-200 rounded-md">
              <div className="flex items-center space-x-2">
                <AlertTriangle className="w-4 h-4 text-red-600" />
                <span className="text-sm text-red-800 font-medium">Legal Review Required</span>
              </div>
              <p className="text-xs text-red-700 mt-1">
                Trademark conflicts detected. Professional legal consultation recommended before proceeding.
              </p>
            </div>
          )}

          {/* Search Details */}
          <div className="mt-4 text-xs text-gray-600">
            <p>Search threshold: {(data.search_threshold * 100).toFixed(0)}% similarity</p>
            <p>Search completed: {new Date(data.search_date).toLocaleDateString()}</p>
            <p>Jurisdictions: {data.jurisdictions_searched.join(', ')}</p>
          </div>
        </CardContent>
      </Card>

      {/* Trademark Conflicts */}
      {data.total_conflicts_found > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Trademark Conflicts</CardTitle>
            <div className="flex space-x-1 mt-4">
              {[
                { key: 'all', label: 'All Conflicts', count: getAllConflicts().length },
                { key: 'USPTO', label: 'USPTO', count: data.conflicts_by_jurisdiction.USPTO.length },
                { key: 'EUIPO', label: 'EUIPO', count: data.conflicts_by_jurisdiction.EUIPO.length },
                { key: 'WIPO', label: 'WIPO', count: data.conflicts_by_jurisdiction.WIPO.length },
                { key: 'Other', label: 'Other', count: data.conflicts_by_jurisdiction.Other.length }
              ].map(tab => (
                <button
                  key={tab.key}
                  onClick={() => setActiveJurisdiction(tab.key as any)}
                  className={`px-3 py-2 text-sm rounded-md transition-colors ${
                    activeJurisdiction === tab.key
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
              {getFilteredConflicts().length > 0 ? (
                getFilteredConflicts().map((conflict, index) => (
                  <TrademarkConflictCard key={index} conflict={conflict} />
                ))
              ) : (
                <p className="text-gray-500 text-center py-4">No conflicts found in selected jurisdiction</p>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Brand Protection Recommendations */}
      {data.brand_protection_recommendations.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Brand Protection Recommendations</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {data.brand_protection_recommendations.map((recommendation, index) => (
                <li key={index} className="flex items-start space-x-2">
                  <Shield className="w-4 h-4 text-blue-600 mt-0.5 flex-shrink-0" />
                  <span className="text-sm">{recommendation}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Defensive Strategies */}
      {data.defensive_strategies.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Defensive Strategies</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {data.defensive_strategies.map((strategy, index) => (
                <li key={index} className="flex items-start space-x-2">
                  <CheckCircle className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                  <span className="text-sm">{strategy}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  )
} 