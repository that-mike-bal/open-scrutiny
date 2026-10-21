import React, { useState, useMemo } from 'react'
import { formatDistanceToNow } from 'date-fns'
import Navigation from '@/components/Navigation'
import { useNavigate } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog'
import { Checkbox } from '@/components/ui/checkbox'
import { AlertTriangle, Plus, Grid3X3, List, Filter, FileText, Users, Building2, Calendar, Search, Globe, Users2, Shield, MapPin, Languages, CheckCircle2 } from 'lucide-react'
import { useTldEvaluations } from '@/hooks/useTldEvaluations'
import { useTldApplications } from '@/hooks/useTldApplications'
import { type TldEvaluationWithAnalysis } from '@/types'
import { createApplications, type CreateApplicationRequest } from '@/lib/supabase-api'

// Types
type ViewMode = 'grid' | 'list'
type SortOption = 'name-asc' | 'name-desc' | 'date-asc' | 'date-desc' | 'risk-asc' | 'risk-desc'
type RiskFilter = 'all' | 'low' | 'medium' | 'high' | 'critical'
type ApplicationType = 'standard' | 'community' | 'brand' | 'geographic' | 'idn_variant'

const APPLICATION_TYPES: { id: ApplicationType; name: string; icon: React.ElementType; description: string }[] = [
  { id: 'standard', name: 'Standard gTLD', icon: Globe, description: 'General-purpose top-level domain' },
  { id: 'community', name: 'Community-Based gTLD', icon: Users2, description: 'Serves a defined community' },
  { id: 'brand', name: 'Brand TLD', icon: Shield, description: 'Restricted to a single trademark holder' },
  { id: 'geographic', name: 'Geographic TLD', icon: MapPin, description: 'Based on a geographic place name' },
  { id: 'idn_variant', name: 'IDN with Variants', icon: Languages, description: 'Internationalized domain name with variants' },
]

interface StringSelectionModalProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: (selectedStrings: string[], applicantId: string, applicationType: ApplicationType) => void
  availableStrings: TldEvaluationWithAnalysis[]
}

function StringSelectionModal({ isOpen, onClose, onConfirm, availableStrings }: StringSelectionModalProps) {
  const [selectedStrings, setSelectedStrings] = useState<string[]>([])
  const [applicantId] = useState('88943d0f-3ac5-4733-88e5-592257c8e339') // Default applicant (replace with your own)
  const [applicationType, setApplicationType] = useState<ApplicationType>('standard')
  const [showRiskWarning, setShowRiskWarning] = useState(false)

  // Check if any selected strings have high risk
  const selectedStringData = availableStrings.filter(s => selectedStrings.includes(s.id))
  const hasHighRiskStrings = selectedStringData.some(s => 
    s.overall_risk_level === 'HIGH' || s.overall_risk_level === 'CRITICAL'
  )

  const handleConfirm = () => {
    if (hasHighRiskStrings && !showRiskWarning) {
      setShowRiskWarning(true)
      return
    }
    onConfirm(selectedStrings, applicantId, applicationType)
    onClose()
    setSelectedStrings([])
    setShowRiskWarning(false)
  }

  const getRiskBadgeVariant = (riskLevel: string) => {
    switch (riskLevel) {
      case 'LOW': return 'success'
      case 'MEDIUM': return 'warning' 
      case 'HIGH': return 'destructive'
      case 'CRITICAL': return 'destructive'
      default: return 'secondary'
    }
  }

  const getBusinessScoreBadge = (score: number) => {
    if (score >= 80) return { variant: 'success' as const, label: 'Excellent' }
    if (score >= 60) return { variant: 'info' as const, label: 'Good' }
    if (score >= 40) return { variant: 'warning' as const, label: 'Fair' }
    return { variant: 'destructive' as const, label: 'Poor' }
  }

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Start New Applications</DialogTitle>
          <DialogDescription>
            Select evaluated TLD strings to generate applications for. Each string will create a separate application.
          </DialogDescription>
        </DialogHeader>

        {showRiskWarning && (
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-4">
            <div className="flex items-start space-x-3">
              <AlertTriangle className="w-5 h-5 text-amber-600 mt-0.5" />
              <div>
                <h4 className="font-medium text-amber-800">High Risk Strings Selected</h4>
                <p className="text-sm text-amber-700 mt-1">
                  Some selected strings have high or critical risk levels. Review the evaluation reports carefully before proceeding with applications.
                </p>
                <div className="mt-2 space-y-1">
                  {selectedStringData
                    .filter(s => s.overall_risk_level === 'HIGH' || s.overall_risk_level === 'CRITICAL')
                    .map(string => (
                      <div key={string.id} className="text-sm text-amber-700">
                        • <strong>.{string.tld_string}</strong> - {string.overall_risk_level} risk
                      </div>
                    ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Applicant Selection */}
        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium">Applicant</label>
            <div className="mt-1">
              <div className="flex items-center space-x-2 p-3 border rounded-lg bg-blue-50">
                <Building2 className="w-4 h-4 text-blue-600" />
                <span className="font-medium">Example Registry (Default)</span>
                <Badge variant="secondary">Current Operator</Badge>
              </div>
              <p className="text-xs text-gray-500 mt-1">
                Example Registry LLC will be used as the applicant for all selected strings
              </p>
            </div>
          </div>

          {/* Application Type Selection */}
          <div>
            <label className="text-sm font-medium">Application Type</label>
            <div className="mt-2 space-y-2">
              {APPLICATION_TYPES.map((type) => {
                const Icon = type.icon
                const isSelected = applicationType === type.id
                return (
                  <button
                    key={type.id}
                    onClick={() => setApplicationType(type.id)}
                    className={`w-full flex items-center space-x-3 p-3 border rounded-lg text-left transition-all ${
                      isSelected
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                    }`}
                  >
                    <Icon className={`w-5 h-5 ${isSelected ? 'text-blue-600' : 'text-gray-500'}`} />
                    <div className="flex-1">
                      <div className="font-medium text-sm">{type.name}</div>
                      <div className="text-xs text-gray-500">{type.description}</div>
                    </div>
                    {isSelected && <CheckCircle2 className="w-4 h-4 text-blue-500" />}
                  </button>
                )
              })}
            </div>
          </div>

          {/* String Selection */}
          <div>
            <label className="text-sm font-medium">
              Select Strings ({selectedStrings.length} selected)
            </label>
            <div className="mt-2 space-y-2 max-h-64 overflow-y-auto border rounded-lg p-2">
              {availableStrings.map((string) => (
                <div key={string.id} className="flex items-center space-x-3 p-3 border rounded-lg hover:bg-gray-50">
                  <Checkbox
                    checked={selectedStrings.includes(string.id)}
                    onCheckedChange={(checked) => {
                      if (checked) {
                        setSelectedStrings([...selectedStrings, string.id])
                      } else {
                        setSelectedStrings(selectedStrings.filter(id => id !== string.id))
                      }
                    }}
                  />
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <span className="font-medium">.{string.tld_string}</span>
                      <div className="flex items-center space-x-2">
                        {string.overall_business_score && (
                          <Badge variant={getBusinessScoreBadge(string.overall_business_score).variant}>
                            {string.overall_business_score}% {getBusinessScoreBadge(string.overall_business_score).label}
                          </Badge>
                        )}
                        {string.overall_risk_level && (
                          <Badge variant={getRiskBadgeVariant(string.overall_risk_level)}>
                            {string.overall_risk_level} Risk
                          </Badge>
                        )}
                      </div>
                    </div>
                    <div className="text-sm text-gray-500 mt-1">
                      Evaluated {formatDistanceToNow(new Date(string.created_at))} ago
                    </div>
                  </div>
                </div>
              ))}
              
              {availableStrings.length === 0 && (
                <div className="text-center py-8 text-gray-500">
                  <FileText className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p>No completed evaluations available</p>
                  <p className="text-sm">Complete some string evaluations first</p>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="flex justify-end space-x-2 pt-4 border-t">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button 
            onClick={handleConfirm}
            disabled={selectedStrings.length === 0}
            className={hasHighRiskStrings && !showRiskWarning ? 'bg-amber-600 hover:bg-amber-700' : ''}
          >
            {hasHighRiskStrings && !showRiskWarning ? (
              <>
                <AlertTriangle className="w-4 h-4 mr-2" />
                Review Risk & Continue
              </>
            ) : (
              <>
                Generate {selectedStrings.length} Application{selectedStrings.length !== 1 ? 's' : ''}
              </>
            )}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}

export default function ApplicationManagement() {
  const navigate = useNavigate()
  const { evaluations: tldEvaluations } = useTldEvaluations()
  const { applications, loading: applicationsLoading, refetch: refetchApplications } = useTldApplications()
  
  // UI State
  const [viewMode, setViewMode] = useState<ViewMode>('grid')
  const [sortBy, setSortBy] = useState<SortOption>('date-desc')
  const [riskFilter, setRiskFilter] = useState<RiskFilter>('all')
  const [searchTerm, setSearchTerm] = useState<string>('')
  const [showStringSelection, setShowStringSelection] = useState(false)

  // Get available strings for new applications (completed evaluations only)
  const availableStrings = useMemo(() => {
    if (!tldEvaluations || !applications) {
      return []
    }
    return tldEvaluations
      .filter(tld => tld.status === 'COMPLETED' || tld.status === 'Evaluated')
      .filter(tld => !applications.some(app => app.tld_string_id === tld.id))
  }, [tldEvaluations, applications])

  // Filtered and sorted applications
  const filteredAndSortedApplications = useMemo(() => {
    if (!applications) return []

    let filtered = applications.filter(application => {
      try {
        // Search filter
        if (searchTerm.trim()) {
          const term = searchTerm.toLowerCase().trim()
          const tldString = (application.tld_string || '').toLowerCase()
          const applicantName = (application.applicant_name || '').toLowerCase()
          const matchesTld = tldString.includes(term)
          const matchesApplicant = applicantName.includes(term)
          if (!matchesTld && !matchesApplicant) return false
        }

        // Risk filter
        if (riskFilter !== 'all') {
          const riskLevel = application.risk_level?.toLowerCase() || 'low'
          switch (riskFilter) {
            case 'low':
              if (riskLevel !== 'low') return false
              break
            case 'medium':
              if (riskLevel !== 'medium') return false
              break
            case 'high':
              if (riskLevel !== 'high') return false
              break
            case 'critical':
              if (riskLevel !== 'critical') return false
              break
          }
        }

        return true
      } catch (error) {
        console.warn('Error filtering application:', application, error)
        return false
      }
    })

    // Apply sorting
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'name-asc':
          return (a.tld_string || '').localeCompare(b.tld_string || '')
        case 'name-desc':
          return (b.tld_string || '').localeCompare(a.tld_string || '')
        case 'date-asc':
          return new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
        case 'date-desc':
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        case 'risk-asc':
          const riskOrderA = a.risk_level === 'LOW' ? 1 : a.risk_level === 'MEDIUM' ? 2 : a.risk_level === 'HIGH' ? 3 : 4
          const riskOrderB = b.risk_level === 'LOW' ? 1 : b.risk_level === 'MEDIUM' ? 2 : b.risk_level === 'HIGH' ? 3 : 4
          return riskOrderA - riskOrderB
        case 'risk-desc':
          const riskOrderA2 = a.risk_level === 'LOW' ? 1 : a.risk_level === 'MEDIUM' ? 2 : a.risk_level === 'HIGH' ? 3 : 4
          const riskOrderB2 = b.risk_level === 'LOW' ? 1 : b.risk_level === 'MEDIUM' ? 2 : b.risk_level === 'HIGH' ? 3 : 4
          return riskOrderB2 - riskOrderA2
        default:
          return 0
      }
    })

    return filtered
  }, [applications, searchTerm, riskFilter, sortBy])

  const handleStartApplications = async (selectedStringIds: string[], applicantId: string, applicationType: ApplicationType) => {
    try {
      const requests: CreateApplicationRequest[] = selectedStringIds.map(stringId => {
        const string = tldEvaluations?.find(s => s.id === stringId)
        return {
          tld_string_id: stringId,
          applicant_id: applicantId,
          tld_string: string?.tld_string || 'unknown',
          application_type: applicationType
        }
      })
      
      // Start application generation
      const results = await createApplications(requests)
      
      // Show results and provide feedback
      const successful = results.filter(r => r.status !== 'Failed' && r.application_id)
      const failed = results.filter(r => r.status === 'Failed' || !r.application_id)
      
      console.log(`Started ${successful.length} applications, ${failed.length} failed`)
      
      // Refresh applications list first
      await refetchApplications()
      
      // Navigate to the first successful application's detail page
      if (successful.length > 0) {
        const firstApp = successful[0]
        // Show success message briefly then navigate
        alert(`✅ Started generating ${successful.length} application${successful.length > 1 ? 's' : ''}!\n\nTaking you to .${requests[0].tld_string} application...`)
        navigate(`/applications/${firstApp.application_id}`)
      } else if (failed.length > 0) {
        // Show error for failed applications
        alert(`❌ Failed to start ${failed.length} application${failed.length > 1 ? 's' : ''}.\n\nCheck console for details.`)
      }
      
    } catch (error) {
      console.error('Failed to start applications:', error)
      alert('❌ Failed to start applications. Please try again.')
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navigation />
      
      <div className="container mx-auto px-4 py-6">
        <div className="flex flex-col space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold">Applications</h1>
              <p className="text-gray-600">Manage ICANN gTLD applications</p>
            </div>
            
            <div className="flex items-center space-x-2">
              <Button
                onClick={() => setShowStringSelection(true)}
                disabled={availableStrings.length === 0 || applicationsLoading}
                className="flex items-center space-x-2"
              >
                <Plus className="w-4 h-4" />
                <span>New Application</span>
              </Button>
            </div>
          </div>

          {/* Stats Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center space-x-2">
                  <FileText className="w-5 h-5 text-blue-600" />
                  <div>
                    <p className="text-2xl font-bold">{applications?.length || 0}</p>
                    <p className="text-sm text-gray-600">Total Applications</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4">
                <div className="flex items-center space-x-2">
                  <Users className="w-5 h-5 text-purple-600" />
                  <div>
                    <p className="text-2xl font-bold">{availableStrings.length}</p>
                    <p className="text-sm text-gray-600">Ready for Applications</p>
                    <p className="text-xs text-gray-500 mt-1">Evaluated strings without applications</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Controls */}
          <div className="flex flex-wrap items-center justify-between gap-4 p-4 bg-muted/30 rounded-lg">
            {/* Search and Filters */}
            <div className="flex flex-wrap items-center gap-4">
              {/* Search Input */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input
                  placeholder="Search applications..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-9 w-64"
                />
              </div>

              <Select value={riskFilter} onValueChange={(value: RiskFilter) => setRiskFilter(value)}>
                <SelectTrigger className="w-32">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Risk</SelectItem>
                  <SelectItem value="low">Low Risk</SelectItem>
                  <SelectItem value="medium">Medium Risk</SelectItem>
                  <SelectItem value="high">High Risk</SelectItem>
                  <SelectItem value="critical">Critical Risk</SelectItem>
                </SelectContent>
              </Select>

              <Select value={sortBy} onValueChange={(value: SortOption) => setSortBy(value)}>
                <SelectTrigger className="w-48">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="date-desc">Newest First</SelectItem>
                  <SelectItem value="date-asc">Oldest First</SelectItem>
                  <SelectItem value="name-asc">Name A-Z</SelectItem>
                  <SelectItem value="name-desc">Name Z-A</SelectItem>
                  <SelectItem value="risk-asc">Lowest Risk</SelectItem>
                  <SelectItem value="risk-desc">Highest Risk</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* View Mode and Results Count */}
            <div className="flex items-center gap-4">
              <div className="text-sm text-muted-foreground">
                {filteredAndSortedApplications.length} of {applications?.length || 0} applications
              </div>

              <div className="flex items-center space-x-1">
                <Button
                  variant={viewMode === 'grid' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setViewMode('grid')}
                >
                  <Grid3X3 className="w-4 h-4" />
                </Button>
                <Button
                  variant={viewMode === 'list' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setViewMode('list')}
                >
                  <List className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </div>

          {/* Applications Grid/List */}
          {(!applications || applications.length === 0) && !applicationsLoading ? (
            <Card>
              <CardContent className="p-12 text-center">
                <FileText className="w-16 h-16 mx-auto mb-4 text-gray-300" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">No Applications Yet</h3>
                <p className="text-gray-600 mb-4">Start by creating applications for your evaluated TLD strings</p>
                <Button 
                  onClick={() => setShowStringSelection(true)}
                  disabled={availableStrings.length === 0}
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Create First Application
                </Button>
                {availableStrings.length === 0 && (
                  <p className="text-sm text-gray-500 mt-2">
                    Complete some string evaluations first
                  </p>
                )}
              </CardContent>
            </Card>
          ) : filteredAndSortedApplications.length === 0 ? (
            <Card>
              <CardContent className="p-12 text-center">
                <Filter className="w-16 h-16 mx-auto mb-4 text-gray-300" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">No Applications Match Filters</h3>
                <p className="text-gray-600 mb-4">Try adjusting your search or filters</p>
                <Button
                  onClick={() => {
                    setSearchTerm('')
                    setRiskFilter('all')
                  }}
                  variant="outline"
                >
                  Clear Filters
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className={viewMode === 'grid' ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4' : 'space-y-3'}>
              {filteredAndSortedApplications.map((application) => {
                // Click handlers for navigation
                const handleCardClick = (e: React.MouseEvent) => {
                  // Check for Cmd/Ctrl + click to open in new tab
                  if (e.metaKey || e.ctrlKey) {
                    e.preventDefault()
                    e.stopPropagation()
                    const applicationUrl = `/applications/${application.id}`
                    const fullUrl = window.location.origin + applicationUrl
                    window.open(fullUrl, '_blank')
                  } else {
                    e.preventDefault()
                    navigate(`/applications/${application.id}`, { state: { application } })
                  }
                }

                const handleCardRightClick = (e: React.MouseEvent) => {
                  e.preventDefault()
                  e.stopPropagation()
                  
                  // Open application in new tab
                  const applicationUrl = `/applications/${application.id}`
                  const fullUrl = window.location.origin + applicationUrl
                  window.open(fullUrl, '_blank')
                }

                return (
                <Card 
                  key={application.id} 
                  className="cursor-pointer hover:shadow-md transition-shadow"
                  onClick={handleCardClick}
                  onContextMenu={handleCardRightClick}
                  title="Left click to open, right-click or Cmd+click to open in new tab"
                >
                  <CardHeader className="pb-3">
                    <CardTitle className="text-lg">.{application.tld_string}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      <div className="flex items-center space-x-2">
                        <Building2 className="w-4 h-4 text-gray-500" />
                        <span className="text-sm">{application.applicant_name}</span>
                      </div>

                      <div className="flex items-center space-x-2">
                        <Calendar className="w-4 h-4 text-gray-500" />
                        <span className="text-sm">
                          Created {formatDistanceToNow(new Date(application.created_at))} ago
                        </span>
                      </div>

                      {application.risk_level && (
                        <Badge variant={application.risk_level === 'HIGH' || application.risk_level === 'CRITICAL' ? 'destructive' : 'secondary'}>
                          {application.risk_level} Risk String
                        </Badge>
                      )}
                    </div>
                  </CardContent>
                </Card>
                )
              })}
            </div>
          )}
        </div>
      </div>

      {/* String Selection Modal */}
      <StringSelectionModal
        isOpen={showStringSelection}
        onClose={() => setShowStringSelection(false)}
        onConfirm={handleStartApplications}
        availableStrings={availableStrings}
      />
    </div>
  )
}