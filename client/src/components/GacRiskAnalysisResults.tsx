import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Badge } from './ui/badge'
import { ChevronDown, ChevronUp, Flag, Globe, AlertTriangle, CheckCircle, Users, FileText } from 'lucide-react'

interface GacPrecedent {
  case_name: string
  year: number
  string: string
  objection_type: 'Early Warning' | 'Formal Objection' | 'Community Objection'
  objecting_governments: string[]
  outcome: 'Withdrawn' | 'Rejected' | 'Approved with Conditions' | 'Denied'
  similarity_to_current: number
  relevance_score: number
  key_issues: string[]
  lessons_learned: string
}

interface GeographicSensitivity {
  region: string
  countries: string[]
  sensitivity_type: 'cultural' | 'religious' | 'political' | 'linguistic' | 'historical'
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  specific_concerns: string[]
  mitigation_strategies: string[]
}

interface GacRiskAnalysisData {
  string: string
  overall_risk_level: 'CLEAR' | 'LOW_RISK' | 'MEDIUM_RISK' | 'HIGH_RISK' | 'BLOCKED'
  objection_probability: number
  early_warning_probability: number
  historical_precedents: GacPrecedent[]
  geographic_sensitivities: GeographicSensitivity[]
  cultural_linguistic_concerns: string[]
  diplomatic_engagement_required: boolean
  proactive_strategies: string[]
  government_outreach_recommendations: string[]
  confidence_score: number
  analysis_date: string
}

interface GacRiskAnalysisResultsProps {
  data: GacRiskAnalysisData
  isLoading?: boolean
}

const getRiskColor = (risk: string) => {
  switch (risk) {
    case 'CLEAR': return 'text-green-600'
    case 'LOW_RISK': return 'text-green-500'
    case 'MEDIUM_RISK': return 'text-yellow-600'
    case 'HIGH_RISK': return 'text-orange-600'
    case 'BLOCKED': return 'text-red-600'
    case 'LOW': return 'text-green-500'
    case 'MEDIUM': return 'text-yellow-600'
    case 'HIGH': return 'text-orange-600'
    case 'CRITICAL': return 'text-red-600'
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

const getSensitivityIcon = (type: string) => {
  switch (type) {
    case 'cultural': return <Users className="w-4 h-4 text-purple-600" />
    case 'religious': return <Flag className="w-4 h-4 text-blue-600" />
    case 'political': return <Flag className="w-4 h-4 text-red-600" />
    case 'linguistic': return <Globe className="w-4 h-4 text-green-600" />
    case 'historical': return <FileText className="w-4 h-4 text-orange-600" />
    default: return <AlertTriangle className="w-4 h-4 text-gray-600" />
  }
}

function GacPrecedentCard({ precedent }: { precedent: GacPrecedent }) {
  const [isExpanded, setIsExpanded] = useState(false)

  return (
    <div className="border rounded-lg p-3 hover:bg-gray-50 transition-colors">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-2">
            <Flag className="w-4 h-4 text-blue-600" />
            <span className="font-medium">{precedent.case_name}</span>
            <span className="text-sm text-gray-500">({precedent.year})</span>
          </div>
          <Badge variant={precedent.outcome === 'Approved with Conditions' ? 'success' : 'destructive'} className="text-xs">
            {precedent.outcome}
          </Badge>
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-sm font-medium">
            {(precedent.similarity_to_current * 100).toFixed(0)}% similar
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
              <span className="font-medium text-gray-600">String:</span>
              <p className="text-gray-800">.{precedent.string}</p>
            </div>
            <div>
              <span className="font-medium text-gray-600">Objection Type:</span>
              <p className="text-gray-800">{precedent.objection_type}</p>
            </div>
            <div className="col-span-2">
              <span className="font-medium text-gray-600">Objecting Governments:</span>
              <p className="text-gray-800">{precedent.objecting_governments.join(', ')}</p>
            </div>
          </div>
          
          {precedent.key_issues.length > 0 && (
            <div>
              <span className="text-xs font-medium text-gray-600">Key Issues:</span>
              <ul className="text-xs text-gray-700 ml-2 mt-1">
                {precedent.key_issues.map((issue, index) => (
                  <li key={index}>• {issue}</li>
                ))}
              </ul>
            </div>
          )}

          {precedent.lessons_learned && (
            <div>
              <span className="text-xs font-medium text-blue-600">Lessons Learned:</span>
              <p className="text-xs text-blue-700 mt-1 bg-blue-50 p-2 rounded">
                {precedent.lessons_learned}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function GeographicSensitivityCard({ sensitivity }: { sensitivity: GeographicSensitivity }) {
  const [isExpanded, setIsExpanded] = useState(false)

  return (
    <div className="border rounded-lg p-3 hover:bg-gray-50 transition-colors">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-2">
            {getSensitivityIcon(sensitivity.sensitivity_type)}
            <span className="font-medium">{sensitivity.region}</span>
          </div>
          <Badge variant={getRiskBadgeVariant(sensitivity.risk_level)} className="text-xs">
            {sensitivity.risk_level} RISK
          </Badge>
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-sm text-gray-500">
            {sensitivity.countries.length} countries
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
              <span className="font-medium text-gray-600">Sensitivity Type:</span>
              <p className="text-gray-800 capitalize">{sensitivity.sensitivity_type}</p>
            </div>
            <div>
              <span className="font-medium text-gray-600">Countries:</span>
              <p className="text-gray-800">{sensitivity.countries.join(', ')}</p>
            </div>
          </div>
          
          {sensitivity.specific_concerns.length > 0 && (
            <div>
              <span className="text-xs font-medium text-red-600">Specific Concerns:</span>
              <ul className="text-xs text-red-700 ml-2 mt-1">
                {sensitivity.specific_concerns.map((concern, index) => (
                  <li key={index}>• {concern}</li>
                ))}
              </ul>
            </div>
          )}

          {sensitivity.mitigation_strategies.length > 0 && (
            <div>
              <span className="text-xs font-medium text-green-600">Mitigation Strategies:</span>
              <ul className="text-xs text-green-700 ml-2 mt-1">
                {sensitivity.mitigation_strategies.map((strategy, index) => (
                  <li key={index}>• {strategy}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function GacRiskAnalysisResults({ data, isLoading = false }: GacRiskAnalysisResultsProps) {
  const [activeTab, setActiveTab] = useState<'overview' | 'precedents' | 'geographic' | 'strategies'>('overview')

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Flag className="w-5 h-5" />
            <span>GAC Risk Analysis</span>
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
              <Flag className="w-5 h-5" />
              <span>GAC Risk Analysis: .{data.string}</span>
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
                {data.objection_probability.toFixed(0)}%
              </div>
              <div className="text-sm text-gray-600">Objection Risk</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-orange-600">
                {data.early_warning_probability.toFixed(0)}%
              </div>
              <div className="text-sm text-gray-600">Early Warning Risk</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">
                {data.confidence_score}%
              </div>
              <div className="text-sm text-gray-600">Confidence</div>
            </div>
          </div>

          {/* Diplomatic Engagement Required */}
          {data.diplomatic_engagement_required && (
            <div className="mt-4 p-3 bg-blue-100 border border-blue-200 rounded-md">
              <div className="flex items-center space-x-2">
                <Users className="w-4 h-4 text-blue-600" />
                <span className="text-sm text-blue-800 font-medium">Diplomatic Engagement Required</span>
              </div>
              <p className="text-xs text-blue-700 mt-1">
                Proactive government outreach recommended to address potential concerns before application.
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Detailed Analysis */}
      <Card>
        <CardHeader>
          <CardTitle>Detailed GAC Analysis</CardTitle>
          <div className="flex space-x-1 mt-4">
            {[
              { key: 'overview', label: 'Overview', count: data.cultural_linguistic_concerns.length },
              { key: 'precedents', label: 'Precedents', count: data.historical_precedents.length },
              { key: 'geographic', label: 'Geographic', count: data.geographic_sensitivities.length },
              { key: 'strategies', label: 'Strategies', count: data.proactive_strategies.length }
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
          {activeTab === 'overview' && (
            <div className="space-y-4">
              <div>
                <h4 className="font-medium text-gray-900 mb-2">Cultural & Linguistic Concerns</h4>
                {data.cultural_linguistic_concerns.length > 0 ? (
                  <ul className="space-y-2">
                    {data.cultural_linguistic_concerns.map((concern, index) => (
                      <li key={index} className="flex items-start space-x-2">
                        <AlertTriangle className="w-4 h-4 text-yellow-600 mt-0.5 flex-shrink-0" />
                        <span className="text-sm">{concern}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-gray-500 text-sm">No significant cultural or linguistic concerns identified</p>
                )}
              </div>
            </div>
          )}

          {activeTab === 'precedents' && (
            <div className="space-y-3">
              {data.historical_precedents.length > 0 ? (
                data.historical_precedents.map((precedent, index) => (
                  <GacPrecedentCard key={index} precedent={precedent} />
                ))
              ) : (
                <p className="text-gray-500 text-center py-4">No relevant historical precedents found</p>
              )}
            </div>
          )}

          {activeTab === 'geographic' && (
            <div className="space-y-3">
              {data.geographic_sensitivities.length > 0 ? (
                data.geographic_sensitivities.map((sensitivity, index) => (
                  <GeographicSensitivityCard key={index} sensitivity={sensitivity} />
                ))
              ) : (
                <p className="text-gray-500 text-center py-4">No geographic sensitivities identified</p>
              )}
            </div>
          )}

          {activeTab === 'strategies' && (
            <div className="space-y-4">
              <div>
                <h4 className="font-medium text-gray-900 mb-2">Proactive Strategies</h4>
                <ul className="space-y-2">
                  {data.proactive_strategies.map((strategy, index) => (
                    <li key={index} className="flex items-start space-x-2">
                      <CheckCircle className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                      <span className="text-sm">{strategy}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div>
                <h4 className="font-medium text-gray-900 mb-2">Government Outreach Recommendations</h4>
                <ul className="space-y-2">
                  {data.government_outreach_recommendations.map((recommendation, index) => (
                    <li key={index} className="flex items-start space-x-2">
                      <Users className="w-4 h-4 text-blue-600 mt-0.5 flex-shrink-0" />
                      <span className="text-sm">{recommendation}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
} 