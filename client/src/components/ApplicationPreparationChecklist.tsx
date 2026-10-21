import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  CheckCircle,
  AlertCircle,
  Clock,
  FileText,
  Timer,
  DollarSign,
  Building,
  TrendingUp,
  Download,
  ExternalLink,
  Info,
  ChevronDown,
  ChevronRight
} from 'lucide-react'

// Types for preparation checklist data
interface SectionPreparation {
  section_name: string
  total_questions: number
  questions_with_guidance: number
  estimated_total_time: number
  required_documents_count: number
  uploaded_documents_count: number
  preparation_complete_percentage: number
}

interface PreparationSummary {
  total_questions: number
  total_estimated_time: number
  total_required_documents: number
  total_uploaded_documents: number
  overall_preparation_percentage: number
  sections: SectionPreparation[]
}

interface CriticalDocument {
  document_type: string
  display_name: string
  description: string
  urgency: 'high' | 'medium' | 'low'
  typical_cost_range: string
  processing_time: string
  where_to_obtain: string
  questions_requiring: string[]
}

interface ApplicationPreparationChecklistProps {
  applicationId: string
  onStartPreparation?: (sectionName: string) => void
}

// Mock data - in real implementation, this would come from API
const mockPreparationData: PreparationSummary = {
  total_questions: 48,
  total_estimated_time: 720, // 12 hours
  total_required_documents: 12,
  total_uploaded_documents: 3,
  overall_preparation_percentage: 25,
  sections: [
    {
      section_name: "Applicant Entity Information",
      total_questions: 16,
      questions_with_guidance: 16,
      estimated_total_time: 180,
      required_documents_count: 4,
      uploaded_documents_count: 1,
      preparation_complete_percentage: 25
    },
    {
      section_name: "Users",
      total_questions: 8,
      questions_with_guidance: 8,
      estimated_total_time: 120,
      required_documents_count: 2,
      uploaded_documents_count: 0,
      preparation_complete_percentage: 0
    },
    {
      section_name: "Payments",
      total_questions: 12,
      questions_with_guidance: 10,
      estimated_total_time: 90,
      required_documents_count: 2,
      uploaded_documents_count: 1,
      preparation_complete_percentage: 50
    },
    {
      section_name: "Applicant Background and Organization",
      total_questions: 12,
      questions_with_guidance: 12,
      estimated_total_time: 330,
      required_documents_count: 4,
      uploaded_documents_count: 1,
      preparation_complete_percentage: 25
    }
  ]
}

const criticalDocuments: CriticalDocument[] = [
  {
    document_type: "lei_certificate",
    display_name: "Legal Entity Identifier (LEI)",
    description: "20-character alphanumeric identifier required for legal entities",
    urgency: "high",
    typical_cost_range: "$50-200 annually",
    processing_time: "1-2 business days",
    where_to_obtain: "LEI issuing organization (LOU)",
    questions_requiring: ["7"]
  },
  {
    document_type: "articles_of_incorporation",
    display_name: "Articles of Incorporation",
    description: "Official document establishing company existence",
    urgency: "high",
    typical_cost_range: "$10-100",
    processing_time: "1-5 business days",
    where_to_obtain: "Company registry office",
    questions_requiring: ["8"]
  },
  {
    document_type: "good_standing_certificate",
    display_name: "Certificate of Good Standing",
    description: "Certificate confirming company compliance status",
    urgency: "high",
    typical_cost_range: "$25-150",
    processing_time: "1-3 business days",
    where_to_obtain: "Company registry office",
    questions_requiring: ["9"]
  },
  {
    document_type: "financial_statements",
    display_name: "Audited Financial Statements",
    description: "Independently audited financial statements",
    urgency: "medium",
    typical_cost_range: "$2,000-15,000",
    processing_time: "2-6 weeks",
    where_to_obtain: "Certified public accountant",
    questions_requiring: ["35", "36", "37"]
  }
]

export default function ApplicationPreparationChecklist({ 
  applicationId, 
  onStartPreparation 
}: ApplicationPreparationChecklistProps) {
  const [preparationData] = useState<PreparationSummary>(mockPreparationData)
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set())
  const [, setLoading] = useState(false)

  // In real implementation, fetch preparation data from API
  useEffect(() => {
    const fetchPreparationData = async () => {
      setLoading(true)
      try {
        // API call would go here
        // const data = await getApplicationPreparationChecklist(applicationId)
        // setPreparationData(data)
      } catch (error) {
        console.error('Failed to fetch preparation data:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchPreparationData()
  }, [applicationId])

  const toggleSectionExpansion = (sectionName: string) => {
    setExpandedSections(prev => {
      const newSet = new Set(prev)
      if (newSet.has(sectionName)) {
        newSet.delete(sectionName)
      } else {
        newSet.add(sectionName)
      }
      return newSet
    })
  }

  const formatTime = (minutes: number) => {
    if (minutes < 60) return `${minutes}m`
    const hours = Math.floor(minutes / 60)
    const remainingMinutes = minutes % 60
    return remainingMinutes > 0 ? `${hours}h ${remainingMinutes}m` : `${hours}h`
  }

  const getUrgencyColor = (urgency: string) => {
    switch (urgency) {
      case 'high': return 'bg-red-100 text-red-800 border-red-200'
      case 'medium': return 'bg-yellow-100 text-yellow-800 border-yellow-200'
      case 'low': return 'bg-green-100 text-green-800 border-green-200'
      default: return 'bg-gray-100 text-gray-800 border-gray-200'
    }
  }

  const getCompletionIcon = (percentage: number) => {
    if (percentage === 100) return <CheckCircle className="w-5 h-5 text-green-600" />
    if (percentage > 0) return <Clock className="w-5 h-5 text-yellow-600" />
    return <AlertCircle className="w-5 h-5 text-gray-400" />
  }

  const getCompletionColor = (percentage: number) => {
    if (percentage === 100) return 'text-green-600'
    if (percentage > 50) return 'text-yellow-600'
    if (percentage > 0) return 'text-orange-600'
    return 'text-gray-400'
  }

  return (
    <div className="space-y-6">
      {/* Overall Progress */}
      <Card className="border-l-4 border-l-blue-500">
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <TrendingUp className="w-5 h-5 text-blue-600" />
              <span>Application Preparation Status</span>
            </div>
            <Badge 
              variant={preparationData.overall_preparation_percentage === 100 ? "success" : "secondary"}
              className="text-sm"
            >
              {Math.round(preparationData.overall_preparation_percentage)}% Ready
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Progress 
            value={preparationData.overall_preparation_percentage} 
            className="h-3"
          />
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
            <div className="p-3 bg-gray-50 rounded-lg">
              <div className="text-2xl font-bold text-gray-900">
                {preparationData.total_questions}
              </div>
              <div className="text-sm text-gray-600">Total Questions</div>
            </div>
            <div className="p-3 bg-blue-50 rounded-lg">
              <div className="text-2xl font-bold text-blue-900">
                {formatTime(preparationData.total_estimated_time)}
              </div>
              <div className="text-sm text-blue-600">Est. Time</div>
            </div>
            <div className="p-3 bg-green-50 rounded-lg">
              <div className="text-2xl font-bold text-green-900">
                {preparationData.total_uploaded_documents}
              </div>
              <div className="text-sm text-green-600">Docs Ready</div>
            </div>
            <div className="p-3 bg-orange-50 rounded-lg">
              <div className="text-2xl font-bold text-orange-900">
                {preparationData.total_required_documents - preparationData.total_uploaded_documents}
              </div>
              <div className="text-sm text-orange-600">Docs Needed</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Detailed Tabs */}
      <Tabs defaultValue="sections" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="sections">By Section</TabsTrigger>
          <TabsTrigger value="documents">Critical Documents</TabsTrigger>
          <TabsTrigger value="timeline">Preparation Timeline</TabsTrigger>
        </TabsList>

        {/* Section-by-Section Progress */}
        <TabsContent value="sections" className="space-y-4">
          {preparationData.sections.map((section, index) => {
            const isExpanded = expandedSections.has(section.section_name)
            const completionIcon = getCompletionIcon(section.preparation_complete_percentage)
            const completionColor = getCompletionColor(section.preparation_complete_percentage)
            
            return (
              <Card key={index} className="overflow-hidden">
                <CardHeader 
                  className="cursor-pointer hover:bg-gray-50 transition-colors"
                  onClick={() => toggleSectionExpansion(section.section_name)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      {isExpanded ? (
                        <ChevronDown className="w-5 h-5 text-gray-400" />
                      ) : (
                        <ChevronRight className="w-5 h-5 text-gray-400" />
                      )}
                      {completionIcon}
                      <div>
                        <CardTitle className="text-lg">{section.section_name}</CardTitle>
                        <div className="text-sm text-gray-600 mt-1">
                          {section.total_questions} questions • {formatTime(section.estimated_total_time)} estimated
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-4">
                      <div className="text-right">
                        <div className={`text-lg font-semibold ${completionColor}`}>
                          {Math.round(section.preparation_complete_percentage)}%
                        </div>
                        <div className="text-xs text-gray-500">
                          {section.uploaded_documents_count}/{section.required_documents_count} docs
                        </div>
                      </div>
                      <Progress 
                        value={section.preparation_complete_percentage} 
                        className="w-20 h-2"
                      />
                    </div>
                  </div>
                </CardHeader>
                
                {isExpanded && (
                  <CardContent className="pt-0 border-t bg-gray-50">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 py-4">
                      <div className="flex items-center space-x-2">
                        <FileText className="w-4 h-4 text-gray-500" />
                        <div>
                          <div className="font-medium text-sm">Questions</div>
                          <div className="text-xs text-gray-600">
                            {section.questions_with_guidance}/{section.total_questions} with guidance
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Timer className="w-4 h-4 text-gray-500" />
                        <div>
                          <div className="font-medium text-sm">Time Required</div>
                          <div className="text-xs text-gray-600">
                            {formatTime(section.estimated_total_time)}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Building className="w-4 h-4 text-gray-500" />
                        <div>
                          <div className="font-medium text-sm">Documents</div>
                          <div className="text-xs text-gray-600">
                            {section.uploaded_documents_count} ready, {section.required_documents_count - section.uploaded_documents_count} needed
                          </div>
                        </div>
                      </div>
                    </div>
                    
                    <div className="flex justify-end pt-2 border-t">
                      <Button 
                        variant="outline" 
                        size="sm"
                        onClick={() => onStartPreparation?.(section.section_name)}
                      >
                        Start Preparation
                      </Button>
                    </div>
                  </CardContent>
                )}
              </Card>
            )
          })}
        </TabsContent>

        {/* Critical Documents */}
        <TabsContent value="documents" className="space-y-4">
          <Alert>
            <Info className="w-4 h-4" />
            <AlertDescription>
              These documents are required for multiple questions and may take time to obtain. 
              Start gathering these early in your preparation process.
            </AlertDescription>
          </Alert>
          
          {criticalDocuments.map((doc, index) => (
            <Card key={index} className={`border-l-4 ${doc.urgency === 'high' ? 'border-l-red-500' : doc.urgency === 'medium' ? 'border-l-yellow-500' : 'border-l-green-500'}`}>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="text-lg flex items-center space-x-2">
                      <span>{doc.display_name}</span>
                      <Badge className={getUrgencyColor(doc.urgency)}>
                        {doc.urgency} priority
                      </Badge>
                    </CardTitle>
                    <p className="text-sm text-gray-600 mt-1">{doc.description}</p>
                    <div className="text-xs text-gray-500 mt-2">
                      Required for questions: {doc.questions_requiring.join(', ')}
                    </div>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                  <div className="flex items-center space-x-2">
                    <DollarSign className="w-4 h-4 text-gray-500" />
                    <div>
                      <div className="font-medium">Cost</div>
                      <div className="text-gray-600">{doc.typical_cost_range}</div>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Clock className="w-4 h-4 text-gray-500" />
                    <div>
                      <div className="font-medium">Processing Time</div>
                      <div className="text-gray-600">{doc.processing_time}</div>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Building className="w-4 h-4 text-gray-500" />
                    <div>
                      <div className="font-medium">Where to Obtain</div>
                      <div className="text-gray-600">{doc.where_to_obtain}</div>
                    </div>
                  </div>
                </div>
                
                <div className="flex justify-end space-x-2 mt-4">
                  <Button variant="outline" size="sm">
                    <ExternalLink className="w-3 h-3 mr-1" />
                    Instructions
                  </Button>
                  <Button variant="outline" size="sm">
                    <Download className="w-3 h-3 mr-1" />
                    Template
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </TabsContent>

        {/* Preparation Timeline */}
        <TabsContent value="timeline" className="space-y-4">
          <Alert>
            <Timer className="w-4 h-4" />
            <AlertDescription>
              Recommended preparation timeline to ensure all documents and information are ready before application submission.
            </AlertDescription>
          </Alert>
          
          <div className="space-y-4">
            <Card className="border-l-4 border-l-red-500">
              <CardContent className="p-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold text-red-900">6-8 Weeks Before Application</h3>
                  <Badge className="bg-red-100 text-red-800">Critical</Badge>
                </div>
                <ul className="text-sm text-gray-700 space-y-1">
                  <li>• Start LEI registration process</li>
                  <li>• Begin financial statement audit (if required)</li>
                  <li>• Initiate background checks for key personnel</li>
                  <li>• Gather corporate formation documents</li>
                </ul>
              </CardContent>
            </Card>
            
            <Card className="border-l-4 border-l-yellow-500">
              <CardContent className="p-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold text-yellow-900">3-4 Weeks Before Application</h3>
                  <Badge className="bg-yellow-100 text-yellow-800">Important</Badge>
                </div>
                <ul className="text-sm text-gray-700 space-y-1">
                  <li>• Obtain good standing certificates</li>
                  <li>• Complete personnel information gathering</li>
                  <li>• Finalize technical service provider agreements</li>
                  <li>• Review and update corporate policies</li>
                </ul>
              </CardContent>
            </Card>
            
            <Card className="border-l-4 border-l-green-500">
              <CardContent className="p-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold text-green-900">1-2 Weeks Before Application</h3>
                  <Badge className="bg-green-100 text-green-800">Final Steps</Badge>
                </div>
                <ul className="text-sm text-gray-700 space-y-1">
                  <li>• Final document review and validation</li>
                  <li>• Complete application form drafts</li>
                  <li>• Prepare payment information</li>
                  <li>• Schedule final review meeting</li>
                </ul>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}

