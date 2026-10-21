import React, { useState, useCallback } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  FileText,
  Upload,
  CheckCircle,
  AlertCircle,
  Clock,
  DollarSign,
  ExternalLink,
  Download,
  Trash2,
  Eye,
  Info,
  Timer,
  Users,
  Building,
  Globe,
  FileCheck,
  Loader2
} from 'lucide-react'
// Fallback type definition in case of import issues
interface ApplicationQuestion {
  id: string;
  question_number: string;
  section: string;
  question_text: string;
  input_type: 'text' | 'textarea' | 'select' | 'checkbox' | 'file_upload';
  required: boolean;
}

// Types for the enhanced question data
interface DocumentRequirement {
  document_type: string
  display_name: string
  description: string
  where_to_obtain: string
  typical_cost_range: string
  processing_time: string
  validity_period: string
  accepted_formats: string[]
  max_file_size_mb: number
  max_pages?: number
  template_url?: string
  example_url?: string
  instructions_url?: string
}

interface UploadedFile {
  id: string
  original_filename: string
  file_size_bytes: number
  file_type: string
  validation_status: 'pending' | 'valid' | 'invalid' | 'needs_review'
  validation_errors: string[]
  uploaded_at: string
  processing_status: 'uploaded' | 'processing' | 'processed' | 'failed'
}

interface PreparationRequirements {
  documents: string[]
  data_needed: string[]
  contacts: string[]
  external_services: string[]
}

interface EnhancedApplicationQuestion extends ApplicationQuestion {
  preparation_requirements?: PreparationRequirements
  required_documents?: string[]
  data_sources?: string[]
  preparation_guidance?: string
  estimated_time_minutes?: number
  difficulty_level?: 'easy' | 'medium' | 'hard' | 'expert'
  document_details?: DocumentRequirement[]
  uploaded_files?: UploadedFile[]
  documents_complete?: boolean
}

interface QuestionPreparationGuideProps {
  question: EnhancedApplicationQuestion
  applicationId: string
  onFileUpload?: (questionId: string, files: File[]) => Promise<void>
  onFileDelete?: (fileId: string) => Promise<void>
  compact?: boolean
}

const difficultyColors = {
  easy: 'bg-green-100 text-green-800',
  medium: 'bg-yellow-100 text-yellow-800', 
  hard: 'bg-orange-100 text-orange-800',
  expert: 'bg-red-100 text-red-800'
}

const difficultyIcons = {
  easy: '●',
  medium: '●●',
  hard: '●●●',
  expert: '●●●●'
}

export default function QuestionPreparationGuide({ 
  question, 
  onFileUpload, 
  onFileDelete,
  compact = false 
}: QuestionPreparationGuideProps) {
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [expandedDocs, setExpandedDocs] = useState<Set<string>>(new Set())

  // Calculate completion status
  const totalRequiredDocs = question.required_documents?.length || 0
  const uploadedValidDocs = question.uploaded_files?.filter(f => f.validation_status === 'valid').length || 0
  const completionPercentage = totalRequiredDocs > 0 ? Math.round((uploadedValidDocs / totalRequiredDocs) * 100) : 100

  const handleFileUpload = useCallback(async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || [])
    if (files.length === 0) return

    setUploading(true)
    setUploadError(null)

    try {
      if (onFileUpload) {
        await onFileUpload(question.id, files)
      }
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : 'Upload failed')
    } finally {
      setUploading(false)
      // Reset input
      event.target.value = ''
    }
  }, [question.id, onFileUpload])

  const toggleDocumentExpansion = (docType: string) => {
    setExpandedDocs(prev => {
      const newSet = new Set(prev)
      if (newSet.has(docType)) {
        newSet.delete(docType)
      } else {
        newSet.add(docType)
      }
      return newSet
    })
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const getValidationStatusIcon = (status: string) => {
    switch (status) {
      case 'valid': return <CheckCircle className="w-4 h-4 text-green-600" />
      case 'invalid': return <AlertCircle className="w-4 h-4 text-red-600" />
      case 'needs_review': return <Clock className="w-4 h-4 text-yellow-600" />
      default: return <Clock className="w-4 h-4 text-gray-400" />
    }
  }

  const getValidationStatusColor = (status: string) => {
    switch (status) {
      case 'valid': return 'text-green-600 bg-green-50'
      case 'invalid': return 'text-red-600 bg-red-50'
      case 'needs_review': return 'text-yellow-600 bg-yellow-50'
      default: return 'text-gray-600 bg-gray-50'
    }
  }

  if (compact && (!question.preparation_guidance && !question.required_documents?.length)) {
    return null
  }

  return (
    <Card className="border-l-4 border-l-blue-500">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <CardTitle className="text-lg flex items-center space-x-2">
            <Info className="w-5 h-5 text-blue-600" />
            <span>Preparation Guide</span>
            {question.difficulty_level && (
              <Badge className={`text-xs ${difficultyColors[question.difficulty_level]}`}>
                {difficultyIcons[question.difficulty_level]} {question.difficulty_level}
              </Badge>
            )}
          </CardTitle>
          <div className="flex items-center space-x-2">
            {question.estimated_time_minutes && (
              <Badge variant="outline" className="flex items-center space-x-1">
                <Timer className="w-3 h-3" />
                <span>{question.estimated_time_minutes}m</span>
              </Badge>
            )}
            {totalRequiredDocs > 0 && (
              <Badge 
                variant={completionPercentage === 100 ? "success" : "secondary"}
                className="flex items-center space-x-1"
              >
                <FileCheck className="w-3 h-3" />
                <span>{uploadedValidDocs}/{totalRequiredDocs}</span>
              </Badge>
            )}
          </div>
        </div>
        
        {totalRequiredDocs > 0 && (
          <div className="mt-3">
            <div className="flex justify-between text-sm text-gray-600 mb-1">
              <span>Document Preparation</span>
              <span>{completionPercentage}% Complete</span>
            </div>
            <Progress value={completionPercentage} className="h-2" />
          </div>
        )}
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Preparation Guidance */}
        {question.preparation_guidance && (
          <Alert>
            <Info className="w-4 h-4" />
            <AlertDescription className="text-sm">
              {question.preparation_guidance}
            </AlertDescription>
          </Alert>
        )}

        {/* Data Sources */}
        {question.data_sources && question.data_sources.length > 0 && (
          <div>
            <h4 className="font-medium text-sm text-gray-700 mb-2 flex items-center space-x-1">
              <Building className="w-4 h-4" />
              <span>Data Sources</span>
            </h4>
            <div className="flex flex-wrap gap-2">
              {question.data_sources.map((source, index) => (
                <Badge key={index} variant="outline" className="text-xs">
                  {source}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* Required Documents */}
        {question.document_details && question.document_details.length > 0 && (
          <div>
            <h4 className="font-medium text-sm text-gray-700 mb-3 flex items-center space-x-1">
              <FileText className="w-4 h-4" />
              <span>Required Documents</span>
            </h4>
            
            <div className="space-y-3">
              {question.document_details.map((doc, index) => {
                const isExpanded = expandedDocs.has(doc.document_type)
                const uploadedFile = question.uploaded_files?.find(f => 
                  f.original_filename.toLowerCase().includes(doc.document_type.toLowerCase())
                )
                
                return (
                  <div key={index} className="border rounded-lg p-4 bg-gray-50">
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex-1">
                        <div className="flex items-center space-x-2 mb-1">
                          <h5 className="font-medium text-sm">{doc.display_name}</h5>
                          {uploadedFile && getValidationStatusIcon(uploadedFile.validation_status)}
                        </div>
                        <p className="text-xs text-gray-600 mb-2">{doc.description}</p>
                        
                        {!isExpanded && (
                          <div className="flex items-center space-x-4 text-xs text-gray-500">
                            <span className="flex items-center space-x-1">
                              <DollarSign className="w-3 h-3" />
                              <span>{doc.typical_cost_range}</span>
                            </span>
                            <span className="flex items-center space-x-1">
                              <Clock className="w-3 h-3" />
                              <span>{doc.processing_time}</span>
                            </span>
                          </div>
                        )}
                      </div>
                      
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => toggleDocumentExpansion(doc.document_type)}
                        className="text-xs"
                      >
                        {isExpanded ? 'Less' : 'More'}
                      </Button>
                    </div>

                    {isExpanded && (
                      <div className="space-y-3 pt-2 border-t border-gray-200">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                          <div>
                            <span className="font-medium text-gray-700">Where to obtain:</span>
                            <p className="text-gray-600">{doc.where_to_obtain}</p>
                          </div>
                          <div>
                            <span className="font-medium text-gray-700">Processing time:</span>
                            <p className="text-gray-600">{doc.processing_time}</p>
                          </div>
                          <div>
                            <span className="font-medium text-gray-700">Typical cost:</span>
                            <p className="text-gray-600">{doc.typical_cost_range}</p>
                          </div>
                          <div>
                            <span className="font-medium text-gray-700">Validity:</span>
                            <p className="text-gray-600">{doc.validity_period}</p>
                          </div>
                        </div>
                        
                        <div>
                          <span className="font-medium text-gray-700 text-xs">Accepted formats:</span>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {doc.accepted_formats.map((format, i) => (
                              <Badge key={i} variant="outline" className="text-xs">
                                {format}
                              </Badge>
                            ))}
                          </div>
                          <p className="text-xs text-gray-500 mt-1">
                            Max size: {doc.max_file_size_mb}MB
                            {doc.max_pages && ` • Max pages: ${doc.max_pages}`}
                          </p>
                        </div>

                        {(doc.template_url || doc.example_url || doc.instructions_url) && (
                          <div className="flex flex-wrap gap-2">
                            {doc.template_url && (
                              <Button variant="outline" size="sm" className="text-xs" asChild>
                                <a href={doc.template_url} target="_blank" rel="noopener noreferrer">
                                  <Download className="w-3 h-3 mr-1" />
                                  Template
                                </a>
                              </Button>
                            )}
                            {doc.example_url && (
                              <Button variant="outline" size="sm" className="text-xs" asChild>
                                <a href={doc.example_url} target="_blank" rel="noopener noreferrer">
                                  <Eye className="w-3 h-3 mr-1" />
                                  Example
                                </a>
                              </Button>
                            )}
                            {doc.instructions_url && (
                              <Button variant="outline" size="sm" className="text-xs" asChild>
                                <a href={doc.instructions_url} target="_blank" rel="noopener noreferrer">
                                  <ExternalLink className="w-3 h-3 mr-1" />
                                  Instructions
                                </a>
                              </Button>
                            )}
                          </div>
                        )}
                      </div>
                    )}

                    {/* File Upload Section */}
                    <div className="mt-3 pt-3 border-t border-gray-200">
                      {uploadedFile ? (
                        <div className={`p-3 rounded-md ${getValidationStatusColor(uploadedFile.validation_status)}`}>
                          <div className="flex items-center justify-between">
                            <div className="flex items-center space-x-2">
                              {getValidationStatusIcon(uploadedFile.validation_status)}
                              <div>
                                <p className="text-sm font-medium">{uploadedFile.original_filename}</p>
                                <p className="text-xs opacity-75">
                                  {formatFileSize(uploadedFile.file_size_bytes)} • 
                                  Uploaded {new Date(uploadedFile.uploaded_at).toLocaleDateString()}
                                </p>
                              </div>
                            </div>
                            <div className="flex items-center space-x-1">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => onFileDelete?.(uploadedFile.id)}
                                className="text-xs p-1"
                              >
                                <Trash2 className="w-3 h-3" />
                              </Button>
                            </div>
                          </div>
                          
                          {uploadedFile.validation_errors.length > 0 && (
                            <div className="mt-2 text-xs">
                              <p className="font-medium">Issues found:</p>
                              <ul className="list-disc list-inside space-y-1">
                                {uploadedFile.validation_errors.map((error, i) => (
                                  <li key={i}>{error}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                      ) : (
                        <div className="border-2 border-dashed border-gray-300 rounded-lg p-4">
                          <div className="text-center">
                            <Upload className="w-8 h-8 mx-auto mb-2 text-gray-400" />
                            <div className="text-sm text-gray-600 mb-2">
                              Upload {doc.display_name}
                            </div>
                            <input
                              type="file"
                              accept={doc.accepted_formats.map(f => `.${f.toLowerCase()}`).join(',')}
                              onChange={handleFileUpload}
                              disabled={uploading}
                              className="hidden"
                              id={`upload-${doc.document_type}`}
                            />
                            <Button
                              variant="outline"
                              size="sm"
                              disabled={uploading}
                              className="text-xs"
                              onClick={() => document.getElementById(`upload-${doc.document_type}`)?.click()}
                            >
                              {uploading ? (
                                <>
                                  <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                                  Uploading...
                                </>
                              ) : (
                                <>
                                  <Upload className="w-3 h-3 mr-1" />
                                  Choose File
                                </>
                              )}
                            </Button>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Upload Error */}
        {uploadError && (
          <Alert variant="destructive">
            <AlertCircle className="w-4 h-4" />
            <AlertDescription className="text-sm">
              {uploadError}
            </AlertDescription>
          </Alert>
        )}

        {/* Preparation Requirements Summary */}
        {question.preparation_requirements && !compact && (
          <div className="bg-blue-50 p-3 rounded-lg">
            <h4 className="font-medium text-sm text-blue-900 mb-2">What You'll Need</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
              {question.preparation_requirements.contacts && question.preparation_requirements.contacts.length > 0 && (
                <div>
                  <span className="font-medium text-blue-800 flex items-center space-x-1 mb-1">
                    <Users className="w-3 h-3" />
                    <span>Contacts</span>
                  </span>
                  <ul className="space-y-1 text-blue-700">
                    {question.preparation_requirements.contacts.map((contact, i) => (
                      <li key={i}>• {contact}</li>
                    ))}
                  </ul>
                </div>
              )}
              
              {question.preparation_requirements.external_services && question.preparation_requirements.external_services.length > 0 && (
                <div>
                  <span className="font-medium text-blue-800 flex items-center space-x-1 mb-1">
                    <Globe className="w-3 h-3" />
                    <span>External Services</span>
                  </span>
                  <ul className="space-y-1 text-blue-700">
                    {question.preparation_requirements.external_services.map((service, i) => (
                      <li key={i}>• {service}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

