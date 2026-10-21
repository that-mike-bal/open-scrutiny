import { useState, useEffect } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Card, CardContent } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { 
  Search, 
  CheckCircle, 
  AlertTriangle, 
  Clock, 
  FileText,
  Loader2,
  Plus,
  X
} from 'lucide-react'
import { useTldEvaluations } from '@/hooks/useTldEvaluations'
import { formatDistanceToNow } from 'date-fns'
import type { TldEvaluationWithAnalysis } from '@/types'

interface StringSelectionModalProps {
  isOpen: boolean
  onClose: () => void
  onCreateApplication: (selectedStrings: TldEvaluationWithAnalysis[]) => void
  mode?: 'single' | 'multi'
}

type StatusFilter = 'all' | 'completed' | 'running' | 'failed'
type RiskFilter = 'all' | 'low' | 'medium' | 'high' | 'critical'

export default function StringSelectionModal({ 
  isOpen, 
  onClose, 
  onCreateApplication,
  mode = 'multi'
}: StringSelectionModalProps) {
  const { evaluations: tldEvaluations, loading } = useTldEvaluations()
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [riskFilter, setRiskFilter] = useState<RiskFilter>('all')
  const [selectedStrings, setSelectedStrings] = useState<Set<string>>(new Set())

  // Reset selection when modal opens/closes
  useEffect(() => {
    if (!isOpen) {
      setSelectedStrings(new Set())
      setSearchTerm('')
      setStatusFilter('all')
      setRiskFilter('all')
    }
  }, [isOpen])

  const getStatusIcon = (status: string | undefined) => {
    switch (status?.toLowerCase()) {
      case 'completed': return <CheckCircle className="w-4 h-4 text-green-500" />
      case 'running': return <Clock className="w-4 h-4 text-blue-500 animate-pulse" />
      case 'failed': return <AlertTriangle className="w-4 h-4 text-red-500" />
      default: return <Clock className="w-4 h-4 text-gray-500" />
    }
  }

  const getRiskBadgeVariant = (riskLevel: string) => {
    switch (riskLevel?.toLowerCase()) {
      case 'low': return 'success'
      case 'medium': return 'warning' 
      case 'high': return 'destructive'
      case 'critical': return 'destructive'
      default: return 'secondary'
    }
  }

  // Filter evaluations based on search and filters
  const filteredEvaluations = tldEvaluations?.filter(evaluation => {
    // Search filter
    if (searchTerm && !evaluation.tld_string.toLowerCase().includes(searchTerm.toLowerCase())) {
      return false
    }

    // Status filter
    if (statusFilter !== 'all') {
      const status = evaluation.overall_status?.toLowerCase() || evaluation.status?.toLowerCase()
      if (statusFilter === 'completed' && status !== 'completed') return false
      if (statusFilter === 'running' && status !== 'running') return false
      if (statusFilter === 'failed' && status !== 'failed') return false
    }

    // Risk filter
    if (riskFilter !== 'all') {
      const risk = evaluation.overall_risk_level?.toLowerCase()
      if (riskFilter !== risk) return false
    }

    return true
  }) || []

  // Only show completed evaluations for application creation
  const applicableEvaluations = filteredEvaluations.filter(evaluation => {
    const status = evaluation.overall_status?.toLowerCase() || evaluation.status?.toLowerCase()
    return status === 'completed'
  })

  const toggleStringSelection = (stringId: string) => {
    if (mode === 'single') {
      setSelectedStrings(new Set([stringId]))
    } else {
      const newSelected = new Set(selectedStrings)
      if (newSelected.has(stringId)) {
        newSelected.delete(stringId)
      } else {
        newSelected.add(stringId)
      }
      setSelectedStrings(newSelected)
    }
  }

  const handleCreateApplications = () => {
    const selectedEvaluations = applicableEvaluations.filter(evaluation => 
      selectedStrings.has(evaluation.id)
    )
    onCreateApplication(selectedEvaluations)
    onClose()
  }

  const selectedCount = selectedStrings.size

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <FileText className="w-5 h-5 text-blue-600" />
              <span>Select Evaluated Strings</span>
            </div>
            <div className="flex items-center space-x-2">
              {selectedCount > 0 && (
                <Badge variant="secondary">{selectedCount} selected</Badge>
              )}
              <Button variant="ghost" size="sm" onClick={onClose}>
                <X className="w-4 h-4" />
              </Button>
            </div>
          </DialogTitle>
          <p className="text-sm text-gray-600">
            Choose evaluated TLD strings to create applications for. Only completed evaluations can be used.
          </p>
        </DialogHeader>

        <div className="flex-1 flex flex-col space-y-4 overflow-hidden">
          {/* Filters */}
          <div className="flex flex-col space-y-4 md:flex-row md:space-y-0 md:space-x-4">
            <div className="relative flex-1">
              <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
              <Input
                placeholder="Search TLD strings..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
            
            <Select value={statusFilter} onValueChange={(value: StatusFilter) => setStatusFilter(value)}>
              <SelectTrigger className="w-48">
                <SelectValue placeholder="Filter by status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem>
                <SelectItem value="completed">Completed</SelectItem>
                <SelectItem value="running">Running</SelectItem>
                <SelectItem value="failed">Failed</SelectItem>
              </SelectContent>
            </Select>

            <Select value={riskFilter} onValueChange={(value: RiskFilter) => setRiskFilter(value)}>
              <SelectTrigger className="w-48">
                <SelectValue placeholder="Filter by risk" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Risk Levels</SelectItem>
                <SelectItem value="low">Low Risk</SelectItem>
                <SelectItem value="medium">Medium Risk</SelectItem>
                <SelectItem value="high">High Risk</SelectItem>
                <SelectItem value="critical">Critical Risk</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Loading State */}
          {loading && (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <Loader2 className="w-8 h-8 animate-spin mx-auto mb-2" />
                <p className="text-gray-600">Loading evaluated strings...</p>
              </div>
            </div>
          )}

          {/* Results */}
          {!loading && (
            <div className="flex-1 overflow-y-auto">
              {applicableEvaluations.length === 0 ? (
                <div className="text-center py-12">
                  <FileText className="w-16 h-16 mx-auto mb-4 text-gray-300" />
                  <h3 className="text-lg font-medium text-gray-900 mb-2">
                    {filteredEvaluations.length === 0 ? 'No Matching Strings' : 'No Completed Evaluations'}
                  </h3>
                  <p className="text-gray-600">
                    {filteredEvaluations.length === 0 
                      ? 'Try adjusting your search or filter criteria.'
                      : 'Only completed evaluations can be used to create applications. Complete some evaluations first.'
                    }
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {applicableEvaluations.map((evaluation) => {
                    const isSelected = selectedStrings.has(evaluation.id)
                    const status = evaluation.overall_status?.toLowerCase() || evaluation.status?.toLowerCase()
                    
                    return (
                      <Card 
                        key={evaluation.id}
                        className={`cursor-pointer transition-all hover:shadow-md ${
                          isSelected ? 'ring-2 ring-blue-500 bg-blue-50' : ''
                        }`}
                        onClick={() => toggleStringSelection(evaluation.id)}
                      >
                        <CardContent className="p-4">
                          <div className="flex items-center space-x-4">
                            <div className="flex-shrink-0">
                              {mode === 'multi' && (
                                <Checkbox 
                                  checked={isSelected}
                                />
                              )}
                              {mode === 'single' && (
                                <div className={`w-4 h-4 rounded-full border-2 ${
                                  isSelected ? 'bg-blue-500 border-blue-500' : 'border-gray-300'
                                }`} />
                              )}
                            </div>
                            
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center space-x-3 mb-2">
                                <div className="font-bold text-lg text-blue-900">
                                  .{evaluation.tld_string}
                                </div>
                                {getStatusIcon(status)}
                                {evaluation.overall_risk_level && (
                                  <Badge variant={getRiskBadgeVariant(evaluation.overall_risk_level)}>
                                    {evaluation.overall_risk_level} Risk
                                  </Badge>
                                )}
                                {evaluation.overall_business_score && (
                                  <Badge variant="outline">
                                    Score: {evaluation.overall_business_score}
                                  </Badge>
                                )}
                              </div>
                              
                              <div className="flex items-center space-x-4 text-sm text-gray-600">
                                <span>{evaluation.use_case}</span>
                                <span>•</span>
                                <span>
                                  Completed {formatDistanceToNow(new Date(evaluation.updated_at))} ago
                                </span>
                              </div>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    )
                  })}
                </div>
              )}
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex items-center justify-between pt-4 border-t">
            <div className="text-sm text-gray-600">
              {selectedCount === 0 ? (
                `${applicableEvaluations.length} available strings`
              ) : (
                `${selectedCount} string${selectedCount === 1 ? '' : 's'} selected`
              )}
            </div>
            
            <div className="flex space-x-2">
              <Button variant="outline" onClick={onClose}>
                Cancel
              </Button>
              <Button
                onClick={handleCreateApplications}
                disabled={selectedCount === 0}
                className="flex items-center space-x-2"
              >
                <Plus className="w-4 h-4" />
                <span>
                  Create Application{selectedCount === 1 ? '' : 's'} ({selectedCount})
                </span>
              </Button>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}