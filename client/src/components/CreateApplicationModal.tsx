// ==========================================================================
// CUSTOMIZE: Defines the output/application types shown in the UI. Edit to match your domain's output types.
// This platform is a domain-agnostic evaluate-then-generate engine; the
// gTLD/ICANN ruleset is just the bundled example. Grep for 'CUSTOMIZE:'
// to find every retargeting point. See the README's Customize section.
// ==========================================================================

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from './ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from './ui/dialog'
import { Progress } from './ui/progress'
import {
  Building2,
  FileText,
  ArrowRight,
  AlertTriangle,
  CheckCircle2,
  Loader2,
  Globe,
  Users2,
  Shield,
  MapPin,
  Languages,
  ChevronRight,
  type LucideIcon
} from 'lucide-react'
import { createApplications, getAllApplicants, type CreateApplicationRequest, type ApplicantData } from '@/lib/supabase-api'
import { supabase } from '@/lib/supabase'
import { useApplicationCreationProgress } from '@/hooks/useApplicationProgress'

// Application type definitions
export type ApplicationType = 'standard' | 'community' | 'brand' | 'geographic' | 'idn_variant'

interface ApplicationTypeOption {
  id: ApplicationType
  name: string
  icon: LucideIcon
  description: string
  includedSections: string
  estimatedQuestions: number
  color: string
}

const APPLICATION_TYPES: ApplicationTypeOption[] = [
  {
    id: 'standard',
    name: 'Standard gTLD',
    icon: Globe,
    description: 'General-purpose top-level domain (e.g., .shop, .tech, .app)',
    includedSections: 'Entity, Background, String, Safeguard, Registry Services, Financial, Operational',
    estimatedQuestions: 155,
    color: 'blue'
  },
  {
    id: 'community',
    name: 'Community-Based gTLD',
    icon: Users2,
    description: 'Serves a defined community with specific eligibility criteria',
    includedSections: 'All standard sections + Community Questions (Q131-157)',
    estimatedQuestions: 182,
    color: 'purple'
  },
  {
    id: 'brand',
    name: 'Brand TLD',
    icon: Shield,
    description: 'Restricted to a single trademark holder (.brand domains)',
    includedSections: 'All standard sections + Brand & Code of Conduct (Q179-188)',
    estimatedQuestions: 165,
    color: 'orange'
  },
  {
    id: 'geographic',
    name: 'Geographic TLD',
    icon: MapPin,
    description: 'Based on a geographic place name requiring government support',
    includedSections: 'All standard sections + Geographic Names (Q158-161)',
    estimatedQuestions: 159,
    color: 'green'
  },
  {
    id: 'idn_variant',
    name: 'IDN with Variants',
    icon: Languages,
    description: 'Internationalized domain name with variant string applications',
    includedSections: 'All standard sections + Variant Strings (Q122-130)',
    estimatedQuestions: 164,
    color: 'teal'
  }
]

interface CreateApplicationModalProps {
  isOpen: boolean
  onClose: () => void
  tldString: string
  evaluationId?: string
  onApplicationCreated?: (applicationId: string) => void
}

export default function CreateApplicationModal({ 
  isOpen, 
  onClose, 
  tldString, 
  evaluationId,
  onApplicationCreated 
}: CreateApplicationModalProps) {
  const navigate = useNavigate()
  const [step, setStep] = useState<'type' | 'confirm'>('type')
  const [selectedType, setSelectedType] = useState<ApplicationType>('standard')
  const [creating, setCreating] = useState(false)
  const [hasRisk, setHasRisk] = useState(false)
  const [createdApplicationId, setCreatedApplicationId] = useState<string | null>(null)
  const [showProgress, setShowProgress] = useState(false)
  const [applicants, setApplicants] = useState<ApplicantData[]>([])
  const [selectedApplicantId, setSelectedApplicantId] = useState<string>('')
  const [loadingApplicants, setLoadingApplicants] = useState(false)
  const [secondaryStrings, setSecondaryStrings] = useState<{ id: string; tld_string: string }[]>([])
  const [selectedSecondaryId, setSelectedSecondaryId] = useState<string>('')
  
  // Track progress during creation
  const { application, completionPercentage } =
    useApplicationCreationProgress(createdApplicationId)

  // Reset step and load applicants when modal opens
  useEffect(() => {
    if (isOpen) {
      setStep('type')
      setSelectedType('standard')
      setShowProgress(false)
      setCreatedApplicationId(null)
      setSelectedSecondaryId('')

      // Load secondary strings
      supabase
        .from('tld_strings')
        .select('id, tld_string')
        .eq('string_type', 'secondary')
        .order('tld_string')
        .then(
          ({ data }) => setSecondaryStrings(data || []),
          (err: unknown) => console.error('Failed to load secondary strings:', err)
        )

      // Load applicants
      setLoadingApplicants(true)
      getAllApplicants()
        .then((data) => {
          setApplicants(data)
          // Auto-select the first applicant
          if (data.length > 0 && !selectedApplicantId) {
            setSelectedApplicantId(data[0].id || '')
          }
        })
        .catch((err) => console.error('Failed to load applicants:', err))
        .finally(() => setLoadingApplicants(false))
    }
  }, [isOpen])

  useEffect(() => {
    // Check if this string has high risk (you could fetch this from the evaluation data)
    // For now, just show the confirmation
    setHasRisk(false)
  }, [evaluationId])

  const handleCreateApplication = async () => {
    if (!evaluationId) {
      console.error('No evaluation ID provided')
      return
    }

    try {
      setCreating(true)
      
      // Create the application with the selected applicant
      const selectedSecondary = secondaryStrings.find(s => s.id === selectedSecondaryId)
      const request: CreateApplicationRequest = {
        tld_string_id: evaluationId,
        applicant_id: selectedApplicantId,
        tld_string: tldString,
        application_type: selectedType,
        secondary_string_id: selectedSecondaryId || undefined,
        secondary_tld_string: selectedSecondary?.tld_string || undefined
      }
      
      const results = await createApplications([request])
      
      if (results.length > 0 && results[0].application_id) {
        const applicationId = results[0].application_id
        setCreatedApplicationId(applicationId)
        setShowProgress(true)
        onApplicationCreated?.(applicationId)
        
        // Auto-navigate to the specific application after a brief delay
        setTimeout(() => {
          navigate(`/applications/${applicationId}`)
          onClose()
        }, 2000)
      } else {
        throw new Error(results[0]?.message || 'Failed to create application')
      }
      
    } catch (error) {
      console.error('Failed to create application:', error)
      alert('Failed to create application. Please try again.')
      setShowProgress(false)
      setCreatedApplicationId(null)
    } finally {
      setCreating(false)
    }
  }

  const handleGoToApplications = () => {
    onClose()
    navigate('/applications')
  }

  const selectedTypeInfo = APPLICATION_TYPES.find(t => t.id === selectedType)

  if (!isOpen) return null

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-lg w-full mx-4">
        <DialogHeader>
          <DialogTitle>
            {step === 'type' ? 'Select Application Type' : 'Create Application'}
          </DialogTitle>
          <DialogDescription>
            {step === 'type' 
              ? `Choose the type of gTLD application for .${tldString}`
              : `Create a ${selectedTypeInfo?.name} application for .${tldString}`
            }
          </DialogDescription>
        </DialogHeader>

        {step === 'type' ? (
          // Step 1: Application Type Selection
          <div className="space-y-3">
            {APPLICATION_TYPES.map((type) => {
              const Icon = type.icon
              const isSelected = selectedType === type.id
              return (
                <button
                  key={type.id}
                  onClick={() => setSelectedType(type.id)}
                  className={`w-full p-4 rounded-lg border-2 text-left transition-all ${
                    isSelected
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <div className={`p-2 rounded-lg ${
                      isSelected ? 'bg-blue-100 text-blue-600' : 'bg-gray-100 text-gray-600'
                    }`}>
                      <Icon className="w-5 h-5" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="font-medium flex items-center gap-2">
                        {type.name}
                        {isSelected && (
                          <CheckCircle2 className="w-4 h-4 text-blue-500" />
                        )}
                      </div>
                      <div className="text-sm text-gray-600 mt-0.5">{type.description}</div>
                      <div className="text-xs text-muted-foreground mt-1.5">
                        <span className="font-medium text-gray-500">Included sections:</span>{' '}
                        {type.includedSections}
                      </div>
                      <div className="mt-1.5">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                          isSelected
                            ? 'bg-blue-100 text-blue-700'
                            : 'bg-gray-100 text-gray-600'
                        }`}>
                          ~{type.estimatedQuestions} questions
                        </span>
                      </div>
                    </div>
                  </div>
                </button>
              )
            })}

            <div className="pt-4 border-t flex gap-2">
              <Button variant="outline" onClick={onClose} className="flex-1">
                Cancel
              </Button>
              <Button
                onClick={() => setStep('confirm')}
                className="flex-1 bg-blue-600 hover:bg-blue-700"
              >
                Continue
                <ChevronRight className="w-4 h-4 ml-1" />
              </Button>
            </div>
          </div>
        ) : (
          // Step 2: Confirmation
          <div className="space-y-4">
            {/* Selected type summary */}
            <div className="flex items-start gap-3 p-3 rounded-lg border bg-blue-50 border-blue-200">
              <div className="p-2 rounded-lg bg-blue-100 text-blue-600">
                {selectedTypeInfo && <selectedTypeInfo.icon className="w-5 h-5" />}
              </div>
              <div>
                <div className="font-medium">{selectedTypeInfo?.name}</div>
                <div className="text-sm text-gray-600">{selectedTypeInfo?.description}</div>
                <div className="text-xs text-muted-foreground mt-1">
                  <span className="font-medium text-gray-500">Sections:</span>{' '}
                  {selectedTypeInfo?.includedSections}
                </div>
                <div className="text-xs text-blue-600 mt-1">
                  ~{selectedTypeInfo?.estimatedQuestions} questions will be loaded
                </div>
              </div>
            </div>

            {/* Applicant selector */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-700">Applicant</label>
              {loadingApplicants ? (
                <div className="flex items-center gap-2 p-3 border rounded-lg bg-gray-50">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span className="text-sm text-gray-500">Loading applicants...</span>
                </div>
              ) : applicants.length > 0 ? (
                <div className="space-y-2">
                  {applicants.map((applicant) => (
                    <button
                      key={applicant.id}
                      onClick={() => setSelectedApplicantId(applicant.id || '')}
                      className={`w-full flex items-center space-x-3 p-3 border rounded-lg text-left transition-all ${
                        selectedApplicantId === applicant.id
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                      }`}
                    >
                      <Building2 className={`w-5 h-5 ${selectedApplicantId === applicant.id ? 'text-blue-600' : 'text-gray-600'}`} />
                      <div>
                        <div className="font-medium">{applicant.legal_name || applicant.business_name}</div>
                        <div className="text-xs text-gray-500">{applicant.entity_type} &mdash; {applicant.jurisdiction}</div>
                      </div>
                      {selectedApplicantId === applicant.id && (
                        <CheckCircle2 className="w-4 h-4 text-blue-500 ml-auto" />
                      )}
                    </button>
                  ))}
                </div>
              ) : (
                <div className="p-3 border rounded-lg bg-amber-50 border-amber-200 text-sm text-amber-700">
                  No applicants found. Create an applicant first.
                </div>
              )}
            </div>

            {/* Secondary string selector */}
            {secondaryStrings.length > 0 && (
              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700">Secondary (Alternate) String</label>
                <select
                  value={selectedSecondaryId}
                  onChange={(e) => setSelectedSecondaryId(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white text-sm"
                >
                  <option value="">None</option>
                  {secondaryStrings.map((s) => (
                    <option key={s.id} value={s.id}>.{s.tld_string}</option>
                  ))}
                </select>
                <p className="text-xs text-gray-500">
                  Optionally link a secondary string to this application.
                </p>
              </div>
            )}

            <div className="text-sm text-gray-600">
              This will create your <strong>{selectedTypeInfo?.name}</strong> application and
              automatically generate answers using your evaluation data and the selected
              applicant's information.
            </div>

            {showProgress && (
              <div className="space-y-3 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="flex items-center space-x-2">
                  <Loader2 className="w-4 h-4 text-blue-600 animate-spin" />
                  <span className="font-medium text-blue-900">Creating Application & Generating Answers</span>
                </div>
                
                {application && (
                  <>
                    <Progress value={completionPercentage} className="w-full" />
                    <div className="text-sm text-blue-700">
                      Generating answers... {completionPercentage}% complete
                    </div>
                    
                    {completionPercentage >= 10 && (
                      <div className="text-xs text-blue-600">
                        Redirecting to application page in a moment...
                      </div>
                    )}
                  </>
                )}
              </div>
            )}

            {hasRisk && (
              <div className="flex items-start space-x-2 p-3 bg-amber-50 border border-amber-200 rounded-lg">
                <AlertTriangle className="w-4 h-4 text-amber-600 mt-0.5" />
                <div className="text-sm text-amber-700">
                  This string has high risk factors. Review the evaluation carefully before proceeding.
                </div>
              </div>
            )}

            <div className="pt-4 border-t space-y-3">
              {/* Primary action button - full width */}
              <Button
                onClick={handleCreateApplication}
                disabled={creating || showProgress || !selectedApplicantId}
                className="w-full bg-green-600 hover:bg-green-700"
              >
                {creating ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Creating...
                  </>
                ) : showProgress ? (
                  <>
                    <CheckCircle2 className="w-4 h-4 mr-2 text-green-600" />
                    Application Created
                  </>
                ) : (
                  <>
                    <ArrowRight className="w-4 h-4 mr-2" />
                    Create & Generate Application
                  </>
                )}
              </Button>
              
              {/* Secondary actions - side by side */}
              <div className="flex gap-2">
                <Button variant="outline" onClick={() => setStep('type')} className="flex-1">
                  Back
                </Button>
                <Button variant="outline" onClick={handleGoToApplications} className="flex-1">
                  <FileText className="w-4 h-4 mr-2" />
                  Manage Applications
                </Button>
              </div>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
