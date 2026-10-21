import { useState, useEffect, useMemo, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Progress } from '@/components/ui/progress'
import Navigation from '@/components/Navigation'
import ApplicationPreparationChecklist from '@/components/ApplicationPreparationChecklist'
import RAGAnswerGenerator from '@/components/RAGAnswerGenerator'
import {
  ArrowLeft,
  Save,
  FileText,
  AlertCircle,
  Search,
  Building2,
  Globe,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Loader2,
  Sparkles,
  Copy,
  CheckCircle2,
  ClipboardCopy,
  Upload,
  Info,
  ListChecks
} from 'lucide-react'
import {
  getTldApplication,
  getApplicationAnswers,
  getApplicationQuestionsAndAnswers,
  upsertApplicationAnswer,
  subscribeToAllApplicationUpdates,
  generateApplicationAnswers,
  type TldApplication,
  type ApplicationQuestion,
  type ApplicationAnswer
} from '@/lib/supabase-api'
import { copyToClipboard } from '@/lib/application-rag-api'
import { useApplicationProgress } from '@/hooks/useApplicationProgress'
import ApplicationTableOfContents from './ApplicationTableOfContents'
import { useActiveSection } from '@/hooks/useActiveSection'
import { sectionSlug, isSectionRelevant, type ApplicationType } from '@/lib/section-utils'
import { useRoutingQuestions } from '@/hooks/useRoutingQuestions'
import { ROUTING_QUESTION_NUMBERS } from '@/lib/routing-questions'


type FilterType = 'all' | 'completed' | 'draft' | 'needs_review' | 'ai_generated'
type GroupByType = 'question_set' | 'section' | 'status' | 'none'

// Entity form groups — groups Q1-48 into logical sections for compact display
const ENTITY_FORM_GROUPS: { label: string; questions: string[]; description?: string }[] = [
  { label: 'Legal Entity Information', questions: ['1', '2', '3', '4'], description: 'Identity and formation' },
  { label: 'Tax & Identifiers', questions: ['5', '6', '7'], description: 'Tax ID, LEI' },
  { label: 'Establishment Documents', questions: ['8', '9'], description: 'File uploads' },
  { label: 'Web & Registry Relationship', questions: ['10', '11', '12', '13', '14'] },
  { label: 'Stock Information', questions: ['15', '16'], description: 'If publicly traded' },
  { label: 'Contact Information', questions: ['17', '18', '19'] },
  { label: 'Primary Business Address', questions: ['20', '21', '22', '23', '24', '25'] },
  { label: 'Direct Parent Company', questions: ['26', '27', '28', '29'] },
  { label: 'Direct Parent Address', questions: ['30', '31', '32', '33', '34', '35'] },
  { label: 'Ultimate Parent Company', questions: ['36', '37', '38', '39'] },
  { label: 'Ultimate Parent Address', questions: ['40', '41', '42', '43', '44', '45'] },
  { label: 'Ownership & Legal', questions: ['46', '47', '48'] },
]

// Set of all question numbers that belong to entity form groups
const ENTITY_GROUP_QUESTION_NUMBERS = new Set(ENTITY_FORM_GROUPS.flatMap(g => g.questions))

export default function ApplicationDetail() {
  const { applicationId } = useParams<{ applicationId: string }>()
  const navigate = useNavigate()

  // State
  const [application, setApplication] = useState<TldApplication | null>(null)
  const [questions, setQuestions] = useState<ApplicationQuestion[]>([])
  const [answers, setAnswers] = useState<ApplicationAnswer[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [generatingAll, setGeneratingAll] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copiedQuestionId, setCopiedQuestionId] = useState<string | null>(null)
  const [copiedSection, setCopiedSection] = useState<string | null>(null)

  // Real-time progress tracking
  const {
    application: liveApplication,
    isGenerating,
    completionPercentage,
    answersGenerated,
    totalQuestions
  } = useApplicationProgress({
    applicationId: applicationId || '',
    questionsCount: questions.length || undefined,
    enabled: !!applicationId
  })

  const [searchTerm, setSearchTerm] = useState('')
  const [filterType, setFilterType] = useState<FilterType>('all')
  const [groupBy, setGroupBy] = useState<GroupByType>('question_set')
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
  const [viewMode, setViewMode] = useState<'list' | 'single'>('list')
  const [showPreparation, setShowPreparation] = useState(false)
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set())
  const sectionsInitialized = useRef(false)

  // Routing question visibility — computes hidden question numbers from routing answers
  const hiddenByRouting = useRoutingQuestions(questions, answers)

  // sectionIds and activeSectionId are defined after groupedQuestions below

  // Load application data
  useEffect(() => {
    if (!applicationId) return

    const loadApplicationData = async () => {
      try {
        setLoading(true)
        setError(null)

        // Load application and combined Q&A data
        const [appData, qaData] = await Promise.all([
          getTldApplication(applicationId),
          getApplicationQuestionsAndAnswers(applicationId)
        ])

        if (!appData) {
          throw new Error('Application not found')
        }

        // Use live data if available and fresher
        const finalApp = (liveApplication && liveApplication.updated_at > appData.updated_at) ? liveApplication : appData
        setApplication(finalApp)
        setQuestions(qaData.questions)
        setAnswers(qaData.answers)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load application data')
        console.error('Error loading application data:', err)
      } finally {
        setLoading(false)
      }
    }

    loadApplicationData()
  }, [applicationId])

  // Sync live application data with local state
  useEffect(() => {
    if (liveApplication && application) {
      // Only update if the live data is newer
      if (liveApplication.updated_at > application.updated_at) {
        setApplication(liveApplication)
      }
    }
  }, [liveApplication, application])

  // Real-time updates for application status
  useEffect(() => {
    if (!applicationId) return

    const subscription = subscribeToAllApplicationUpdates((payload) => {
      // Only update if this is our application
      if (payload.new?.id === applicationId && payload.eventType === 'UPDATE') {
        console.log('Application update received:', payload.new)
        setApplication(prev => prev ? { ...prev, ...payload.new } : null)
        
        // If status changed to completed or progress increased significantly, refresh answers
        if (payload.new.status === 'Completed' && payload.old?.status !== 'Completed') {
          getApplicationAnswers(applicationId).then(setAnswers)
        } else if (payload.new.completion_percentage > (payload.old?.completion_percentage || 0) + 10) {
          // Refresh answers when significant progress is made
          getApplicationAnswers(applicationId).then(setAnswers)
        }
      }
    })

    return () => {
      subscription?.unsubscribe()
    }
  }, [applicationId])

  // Memoized filtered and grouped questions
  const filteredQuestions = useMemo(() => {
    let filtered = questions

    // Apply routing question visibility — hide dependent questions when routing answer is No/empty
    filtered = filtered.filter(q => !hiddenByRouting.has(q.question_number))

    // Apply search filter
    if (searchTerm) {
      filtered = filtered.filter(q => 
        q.question_text.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (q.subsection ?? '').toLowerCase().includes(searchTerm.toLowerCase()) ||
        q.question_number.toString().includes(searchTerm)
      )
    }

    // Apply status filter
    if (filterType !== 'all') {
      filtered = filtered.filter(q => {
        const answer = answers.find(a => a.question_id === q.id)
        if (!answer) return filterType === 'draft'
        
        switch (filterType) {
          case 'completed': return answer.status === 'completed'
          case 'draft': return answer.status === 'draft'
          case 'needs_review': return answer.status === 'needs_review'
          case 'ai_generated': return answer.ai_generated
          default: return true
        }
      })
    }

    return filtered
  }, [questions, answers, searchTerm, filterType, hiddenByRouting])

  const groupedQuestions = useMemo(() => {
    if (groupBy === 'none') {
      return { 'All Questions': filteredQuestions }
    }

    return filteredQuestions.reduce((groups, question) => {
      let key: string
      if (groupBy === 'question_set') {
        key = question.question_set || 'Other'  // ICANN Question Set
      } else if (groupBy === 'section') {
        key = question.subsection || 'Unknown Section'
      } else if (groupBy === 'status') {
        key = answers.find(a => a.question_id === question.id)?.status || 'draft'
      } else {
        key = 'All Questions'
      }
      
      if (!groups[key]) {
        groups[key] = []
      }
      groups[key].push(question)
      return groups
    }, {} as Record<string, ApplicationQuestion[]>)
  }, [filteredQuestions, groupBy, answers])

  const sectionIds = useMemo(() => {
    if (viewMode !== 'list') return []
    return Object.keys(groupedQuestions).map(name => sectionSlug(name))
  }, [groupedQuestions, viewMode])

  const activeSectionId = useActiveSection(sectionIds)

  // Handler for updating answers
  const handleAnswerChange = (questionId: string, value: string) => {
    setAnswers(prev => {
      const existing = prev.find(a => a.question_id === questionId)
      if (existing) {
        return prev.map(a => 
          a.question_id === questionId 
            ? { ...a, answer_text: value, status: 'draft' as const, last_modified: new Date().toISOString() }
            : a
        )
      } else {
        return [...prev, {
          id: `ans-${questionId}`,
          question_id: questionId,
          application_id: applicationId || '',
          answer_text: value,
          status: 'draft' as const,
          ai_generated: false,
          last_modified: new Date().toISOString()
        }]
      }
    })
  }

  const handleSave = async () => {
    if (!applicationId) return
    
    setSaving(true)
    try {
      // Save all draft answers
      const draftAnswers = answers.filter(a => a.status === 'draft')
      
      for (const answer of draftAnswers) {
        await upsertApplicationAnswer({
          question_id: answer.question_id,
          application_id: applicationId,
          answer_text: answer.answer_text,
          answer_files: answer.answer_files,
          status: 'completed',
          ai_generated: answer.ai_generated
        })
      }
      
      // Update local state to mark as completed
      setAnswers(prev => prev.map(a => 
        a.status === 'draft' ? { ...a, status: 'completed' as const } : a
      ))
      
    } catch (err) {
      console.error('Failed to save answers:', err)
      setError('Failed to save changes')
    } finally {
      setSaving(false)
    }
  }

  // Generate all answers using RAG-based AI
  const handleGenerateAll = async () => {
    if (!applicationId) return
    
    setGeneratingAll(true)
    setError(null)
    
    try {
      console.log('🚀 Starting bulk answer generation for application:', applicationId)
      const result = await generateApplicationAnswers(applicationId)
      
      if (result.success) {
        console.log(`✅ Generated ${result.answers_generated} answers`)
        // Refresh the Q&A data to show new answers
        const qaData = await getApplicationQuestionsAndAnswers(applicationId)
        setQuestions(qaData.questions)
        setAnswers(qaData.answers)
      } else {
        console.error('Generation failed:', result.message)
        setError(result.message || 'Failed to generate answers')
      }
    } catch (err) {
      console.error('Error generating answers:', err)
      setError(err instanceof Error ? err.message : 'Failed to generate answers')
    } finally {
      setGeneratingAll(false)
    }
  }

  const renderQuestionField = (question: ApplicationQuestion) => {
    const answer = answers.find(a => a.question_id === question.id)
    const value = answer?.answer_text || ''

    switch (question.field_type) {
      case 'textarea':
        return (
          <Textarea
            value={value}
            onChange={(e) => handleAnswerChange(question.id, e.target.value)}
            placeholder="Enter your answer..."
            className="min-h-[100px]"
            maxLength={question.character_limit}
          />
        )
      case 'url':
        return (
          <Input
            type="url"
            value={value}
            onChange={(e) => handleAnswerChange(question.id, e.target.value)}
            placeholder="https://example.com"
            maxLength={question.character_limit}
          />
        )
      case 'file':
        return (
          <div className="space-y-2">
            <Input type="file" multiple accept=".pdf,.doc,.docx" />
            {answer?.answer_files && answer.answer_files.length > 0 && (
              <div className="text-sm text-gray-600">
                Uploaded files: {answer.answer_files.join(', ')}
              </div>
            )}
          </div>
        )
      default:
        return (
          <Input
            value={value}
            onChange={(e) => handleAnswerChange(question.id, e.target.value)}
            placeholder="Enter your answer..."
            maxLength={question.character_limit}
          />
        )
    }
  }

  const toggleSection = (sectionName: string) => {
    setExpandedSections(prev => {
      const next = new Set(prev)
      if (next.has(sectionName)) {
        next.delete(sectionName)
      } else {
        next.add(sectionName)
      }
      return next
    })
  }

  const expandAllSections = () => {
    setExpandedSections(new Set(Object.keys(groupedQuestions)))
  }

  const collapseAllSections = () => {
    setExpandedSections(new Set())
  }

  const handleSectionNavigation = (sectionId: string) => {
    const groupName = Object.keys(groupedQuestions).find(
      name => sectionSlug(name) === sectionId
    )
    if (groupName && !expandedSections.has(groupName)) {
      setExpandedSections(prev => new Set([...prev, groupName]))
    }
    requestAnimationFrame(() => {
      document.getElementById('section-' + sectionId)
        ?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    })
  }

  // Initialize sections as expanded when questions first load.
  // Smart entity collapse: if >70% of entity questions have answers, start that section collapsed.
  useEffect(() => {
    if (questions.length > 0 && !sectionsInitialized.current) {
      sectionsInitialized.current = true
      const allGroups = Object.keys(groupedQuestions)

      // Find the entity section and check its completion
      const entityGroup = allGroups.find(name => name.includes('Applying Entity Information'))
      let collapseEntity = false

      if (entityGroup) {
        const entityQuestions = groupedQuestions[entityGroup] || []
        const answeredCount = entityQuestions.filter(q => {
          const a = answers.find(a => a.question_id === q.id)
          return a?.answer_text && a.answer_text.trim().length > 0
        }).length
        if (entityQuestions.length > 0 && answeredCount / entityQuestions.length > 0.7) {
          collapseEntity = true
        }
      }

      const expanded = collapseEntity
        ? allGroups.filter(name => name !== entityGroup)
        : allGroups
      setExpandedSections(new Set(expanded))
    }
  }, [questions.length])

  const handleCopyAnswer = async (questionId: string) => {
    const answer = answers.find(a => a.question_id === questionId)
    if (!answer?.answer_text) return
    const success = await copyToClipboard(answer.answer_text)
    if (success) {
      setCopiedQuestionId(questionId)
      setTimeout(() => setCopiedQuestionId(null), 2000)
    }
  }

  const handleCopySection = async (groupName: string, groupQuestions: ApplicationQuestion[]) => {
    const lines = groupQuestions.map(q => {
      const answer = answers.find(a => a.question_id === q.id)
      const answerText = answer?.answer_text?.trim() || '(no answer)'
      return `Q${q.question_number}: ${q.question_text}\nA: ${answerText}`
    })
    const text = lines.join('\n\n')
    try {
      await navigator.clipboard.writeText(text)
      setCopiedSection(groupName)
      setTimeout(() => setCopiedSection(null), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  const getCategoryBadge = (category?: string) => {
    switch (category) {
      case 'entity_field':
        return (
          <Badge variant="outline" className="bg-blue-100 text-blue-700 border-blue-200 text-xs flex items-center gap-1">
            <Building2 className="w-3 h-3" /> Applicant
          </Badge>
        )
      case 'selection_field':
        return (
          <Badge variant="outline" className="bg-teal-100 text-teal-700 border-teal-200 text-xs flex items-center gap-1">
            <ListChecks className="w-3 h-3" /> Selection
          </Badge>
        )
      case 'file_upload':
        return (
          <Badge variant="outline" className="bg-gray-100 text-gray-700 border-gray-200 text-xs flex items-center gap-1">
            <Upload className="w-3 h-3" /> Upload Required
          </Badge>
        )
      case 'substantive_field':
        return (
          <Badge variant="outline" className="bg-purple-100 text-purple-700 border-purple-200 text-xs flex items-center gap-1">
            <FileText className="w-3 h-3" /> Narrative
          </Badge>
        )
      default:
        return null
    }
  }

  const getAnswerStatusBadge = (question: ApplicationQuestion, answer?: ApplicationAnswer) => {
    const category = question.question_category || 'substantive_field'

    if (category === 'file_upload') {
      return (
        <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200 text-xs">
          Action Needed
        </Badge>
      )
    }

    if (category === 'selection_field') {
      return (
        <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200 text-xs">
          Action Needed
        </Badge>
      )
    }

    if (!answer?.answer_text) {
      if (isGenerating) return null // Still generating, don't show badge yet
      return (
        <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200 text-xs">
          No Data
        </Badge>
      )
    }

    if (category === 'entity_field') {
      return (
        <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200 text-xs">
          From Profile
        </Badge>
      )
    }

    return (
      <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200 text-xs">
        Generated
      </Badge>
    )
  }

  // Extract a short label from question_text (first line or first N chars)
  const getShortLabel = (text: string) => {
    const firstLine = text.split(/[.\n]/)[0].trim()
    return firstLine.length > 60 ? firstLine.substring(0, 57) + '...' : firstLine
  }

  // Render a grouped entity form card
  const renderEntityFormGroup = (group: typeof ENTITY_FORM_GROUPS[number], groupQuestions: ApplicationQuestion[]) => {
    // Find the actual question objects for this group
    const matchedQuestions = group.questions
      .map(qn => groupQuestions.find(q => q.question_number === qn))
      .filter((q): q is ApplicationQuestion => !!q)

    if (matchedQuestions.length === 0) return null

    const filledCount = matchedQuestions.filter(q => {
      const answer = answers.find(a => a.question_id === q.id)
      return answer?.answer_text
    }).length

    return (
      <Card key={group.label} className="mb-4">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base flex items-center gap-2">
              <Building2 className="w-4 h-4 text-blue-600" />
              {group.label}
              {group.description && (
                <span className="text-sm text-gray-400 font-normal">— {group.description}</span>
              )}
            </CardTitle>
            <span className="text-xs text-gray-500">{filledCount}/{matchedQuestions.length} filled</span>
          </div>
        </CardHeader>
        <CardContent className="pt-0">
          <div className="grid gap-3">
            {matchedQuestions.map(q => {
              const answer = answers.find(a => a.question_id === q.id)
              const category = q.question_category || 'entity_field'
              const value = answer?.answer_text || ''

              // File upload questions get a simple label
              if (category === 'file_upload') {
                return (
                  <div key={q.id} className="flex items-center gap-3 py-2 border-b border-gray-100 last:border-0">
                    <span className="text-xs text-gray-400 w-8 shrink-0">Q{q.question_number}</span>
                    <span className="text-sm text-gray-700 flex-1">{getShortLabel(q.question_text)}</span>
                    <div className="flex items-center gap-1.5 text-gray-500">
                      <Upload className="w-3.5 h-3.5" />
                      <span className="text-xs">File Upload Required</span>
                    </div>
                  </div>
                )
              }

              // Selection fields
              if (category === 'selection_field') {
                return (
                  <div key={q.id} className="flex items-center gap-3 py-2 border-b border-gray-100 last:border-0">
                    <span className="text-xs text-gray-400 w-8 shrink-0">Q{q.question_number}</span>
                    <span className="text-sm text-gray-700 flex-1">{getShortLabel(q.question_text)}</span>
                    <div className="flex items-center gap-1.5 text-teal-600">
                      <ListChecks className="w-3.5 h-3.5" />
                      <span className="text-xs">Selection Required</span>
                    </div>
                  </div>
                )
              }

              // Substantive field (e.g. Q48 narrative)
              if (category === 'substantive_field') {
                return (
                  <div key={q.id} className="py-2 border-b border-gray-100 last:border-0">
                    <div className="flex items-center gap-3 mb-1">
                      <span className="text-xs text-gray-400 w-8 shrink-0">Q{q.question_number}</span>
                      <span className="text-sm text-gray-700 flex-1">{getShortLabel(q.question_text)}</span>
                      {getCategoryBadge(category)}
                    </div>
                    <div className="ml-11 flex items-start gap-2">
                      <Textarea
                        value={value}
                        onChange={(e) => handleAnswerChange(q.id, e.target.value)}
                        placeholder="Enter your answer..."
                        className="min-h-[80px] text-sm flex-1"
                        maxLength={q.character_limit}
                      />
                      {value && (
                        <button
                          onClick={() => handleCopyAnswer(q.id)}
                          className="text-gray-400 hover:text-gray-600 shrink-0 mt-1"
                          title="Copy to clipboard"
                        >
                          {copiedQuestionId === q.id ? (
                            <CheckCircle2 className="w-4 h-4 text-green-500" />
                          ) : (
                            <Copy className="w-4 h-4" />
                          )}
                        </button>
                      )}
                    </div>
                  </div>
                )
              }

              // Entity field (default) — compact inline display
              return (
                <div key={q.id} className="flex items-center gap-3 py-2 border-b border-gray-100 last:border-0">
                  <span className="text-xs text-gray-400 w-8 shrink-0">Q{q.question_number}</span>
                  <span className="text-sm text-gray-700 w-48 shrink-0">{getShortLabel(q.question_text)}</span>
                  <div className="flex-1 flex items-center gap-1.5">
                    {value ? (
                      <>
                        <span className="text-sm text-blue-900 bg-blue-50 px-2 py-1 rounded">{value}</span>
                        <button
                          onClick={() => handleCopyAnswer(q.id)}
                          className="text-gray-400 hover:text-gray-600 shrink-0"
                          title="Copy to clipboard"
                        >
                          {copiedQuestionId === q.id ? (
                            <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />
                          ) : (
                            <Copy className="w-3.5 h-3.5" />
                          )}
                        </button>
                      </>
                    ) : (
                      <span className="text-xs text-amber-600 flex items-center gap-1">
                        <AlertCircle className="w-3 h-3" />
                        Missing — update applicant profile
                        {q.applicant_field_mapping && <span className="text-gray-400">({q.applicant_field_mapping})</span>}
                      </span>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>
    )
  }

  // Check if a question is a routing question (Yes/No gateway)
  const isRoutingQuestion = (questionNumber: string) => ROUTING_QUESTION_NUMBERS.has(questionNumber)

  const renderSingleQuestion = (question: ApplicationQuestion) => {
    const answer = answers.find(a => a.question_id === question.id)
    const category = question.question_category || 'substantive_field'
    const isCopied = copiedQuestionId === question.id
    const isRouting = isRoutingQuestion(question.question_number)

    // Determine if this is an "insufficient data" substantive question
    const isSubstantiveNoData = category === 'substantive_field' && !answer?.answer_text && !isGenerating

    return (
      <div key={question.id} className="space-y-4 mb-6">
        <Card className={isRouting ? 'border-indigo-200 bg-indigo-50/30' : ''}>
          <CardHeader>
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <CardTitle className="text-lg flex items-center space-x-2 flex-wrap gap-y-1">
                  <span>Question {question.question_number}</span>
                  {question.required && <span className="text-red-500">*</span>}
                  {isRouting && (
                    <Badge variant="outline" className="bg-indigo-100 text-indigo-700 border-indigo-200 text-xs">
                      Routing
                    </Badge>
                  )}
                  {!isRouting && getCategoryBadge(category)}
                  {!isRouting && getAnswerStatusBadge(question, answer)}
                </CardTitle>
                <div className="text-sm text-gray-600 mt-1">
                  {question.subsection}
                  {question.public_posting && (
                    <Badge variant="outline" className="ml-2">Public</Badge>
                  )}
                </div>
              </div>
            </div>
            <p className="text-gray-700 mt-2">{question.question_text}</p>
            {question.notes_instructions && (
              <div className="text-sm text-gray-600 bg-gray-50 p-3 rounded-md mt-2">
                <strong>Instructions:</strong> {question.notes_instructions}
              </div>
            )}
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {/* Routing questions: Yes/No toggle buttons */}
              {isRouting && (
                <div className="flex items-center gap-3">
                  <span className="text-sm font-medium text-gray-700">Select:</span>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant={answer?.answer_text?.toLowerCase() === 'yes' ? 'default' : 'outline'}
                      className={answer?.answer_text?.toLowerCase() === 'yes' ? 'bg-indigo-600 hover:bg-indigo-700' : ''}
                      onClick={() => handleAnswerChange(question.id, 'Yes')}
                    >
                      Yes
                    </Button>
                    <Button
                      size="sm"
                      variant={answer?.answer_text?.toLowerCase() === 'no' ? 'default' : 'outline'}
                      className={answer?.answer_text?.toLowerCase() === 'no' ? 'bg-gray-600 hover:bg-gray-700' : ''}
                      onClick={() => handleAnswerChange(question.id, 'No')}
                    >
                      No
                    </Button>
                  </div>
                  {answer?.answer_text && (
                    <span className="text-xs text-gray-500">
                      Current: <span className="font-medium">{answer.answer_text}</span>
                    </span>
                  )}
                </div>
              )}

              {/* Entity fields: read-only display with applicant value */}
              {category === 'entity_field' && answer?.answer_text && (
                <div className="flex items-center gap-2 p-3 bg-blue-50 border border-blue-200 rounded-md">
                  <Building2 className="w-4 h-4 text-blue-600 shrink-0" />
                  <span className="text-sm text-blue-900 flex-1">{answer.answer_text}</span>
                  <button
                    onClick={() => handleCopyAnswer(question.id)}
                    className="text-blue-400 hover:text-blue-600 shrink-0"
                    title="Copy to clipboard"
                  >
                    {isCopied ? (
                      <CheckCircle2 className="w-4 h-4 text-green-500" />
                    ) : (
                      <Copy className="w-4 h-4" />
                    )}
                  </button>
                </div>
              )}

              {/* Entity fields: missing data — update profile message */}
              {category === 'entity_field' && !answer?.answer_text && (
                <div className="flex items-center gap-2 p-3 bg-amber-50 border border-amber-200 rounded-md">
                  <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />
                  <span className="text-sm text-amber-700">
                    Missing data — update applicant profile
                    {question.applicant_field_mapping && ` (${question.applicant_field_mapping})`}
                  </span>
                </div>
              )}

              {/* File upload: show requirements */}
              {category === 'file_upload' && (
                <div className="flex items-start gap-2 p-3 bg-gray-50 border border-gray-200 rounded-md">
                  <Upload className="w-4 h-4 text-gray-500 shrink-0 mt-0.5" />
                  <div className="text-sm text-gray-700">
                    <p className="font-medium">File upload required</p>
                    {question.input_field_requirements && (
                      <p className="text-gray-500 mt-1">{question.input_field_requirements}</p>
                    )}
                  </div>
                </div>
              )}

              {/* Selection fields: show tip */}
              {category === 'selection_field' && (
                <div className="flex items-start gap-2 p-3 bg-teal-50 border border-teal-200 rounded-md">
                  <Info className="w-4 h-4 text-teal-600 shrink-0 mt-0.5" />
                  <span className="text-sm text-teal-700">
                    Review the options and select the appropriate value.
                  </span>
                </div>
              )}

              {/* Substantive fields: insufficient data — prompt-driven generation */}
              {isSubstantiveNoData && (
                <div className="space-y-3">
                  <div className="flex items-start gap-2 p-3 bg-amber-50 border border-amber-200 rounded-md">
                    <AlertCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                    <span className="text-sm text-amber-700">
                      Not enough evaluation data to auto-generate this answer. Provide direction below to generate.
                    </span>
                  </div>
                  <RAGAnswerGenerator
                    question={{
                      id: question.id,
                      question_number: question.question_number,
                      question_text: question.question_text,
                      subsection: question.subsection || '',
                      character_limit: question.character_limit,
                      question_category: question.question_category
                    }}
                    application={application ? {
                      id: application.id,
                      tld_string: application.tld_string,
                      applicant_id: application.applicant_id
                    } : undefined}
                    onAnswerGenerated={(generatedAnswer) => {
                      handleAnswerChange(question.id, generatedAnswer)
                    }}
                    requirePrompt={true}
                  />
                </div>
              )}

              {/* Editable field for all categories (skip for routing questions — they have the toggle above) */}
              {!isRouting && <div className="flex items-start gap-2">
                <div className="flex-1">
                  {renderQuestionField(question)}
                </div>
                {answer?.answer_text && (
                  <Button
                    size="icon"
                    variant="outline"
                    onClick={() => handleCopyAnswer(question.id)}
                    className="shrink-0 mt-0.5"
                    title="Copy to clipboard"
                  >
                    {isCopied ? (
                      <CheckCircle2 className="w-4 h-4 text-green-600" />
                    ) : (
                      <Copy className="w-4 h-4" />
                    )}
                  </Button>
                )}
              </div>}

              {!isRouting && question.character_limit && (
                <div className="text-xs text-gray-500">
                  {(answer?.answer_text || '').length} / {question.character_limit} characters
                  {answer?.answer_text && question.character_limit && answer.answer_text.length > question.character_limit && (
                    <span className="text-red-500 ml-1 font-medium">Over limit</span>
                  )}
                </div>
              )}

              {!isRouting && question.input_field_requirements && category !== 'file_upload' && (
                <div className="text-xs text-gray-600">
                  <strong>Requirements:</strong> {question.input_field_requirements}
                </div>
              )}

              {answer?.last_modified && (
                <div className="text-xs text-gray-500">
                  Last modified: {new Date(answer.last_modified).toLocaleString()}
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navigation />
        <div className="container mx-auto px-4 py-6">
          <div className="flex items-center justify-center h-64">
            <Loader2 className="w-8 h-8 animate-spin" />
          </div>
        </div>
      </div>
    )
  }

  if (error || !application) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navigation />
        <div className="container mx-auto px-4 py-6">
          <div className="flex items-center space-x-4 mb-6">
            <Button
              variant="outline"
              onClick={() => navigate('/applications')}
              className="flex items-center space-x-2"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Back to Applications</span>
            </Button>
          </div>
          <div className="text-center py-12">
            <AlertCircle className="w-16 h-16 mx-auto mb-4 text-red-400" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              {error || 'Application not found'}
            </h3>
            <p className="text-gray-600">
              The application you're looking for doesn't exist or couldn't be loaded.
            </p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navigation />
      
      <div className="container mx-auto px-4 py-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-4">
            <Button
              variant="outline"
              onClick={() => navigate('/applications')}
              className="flex items-center space-x-2"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Back to Applications</span>
            </Button>
            
            <div>
              <h1 className="text-2xl font-bold">.{application.tld_string} Application</h1>
              {application.secondary_tld_string && (
                <p className="text-sm text-amber-700">
                  Secondary string: <span className="font-medium">.{application.secondary_tld_string}</span>
                </p>
              )}
              <p className="text-gray-600">{application.applicant_name}</p>
            </div>
          </div>
          
          <div className="flex items-center space-x-2">
            <Badge variant={application.status === 'Completed' || application.status === 'Ready_For_Review' ? 'success' : 'secondary'}>
              {application.status?.replace(/_/g, ' ')}
            </Badge>
            <Button
              onClick={handleGenerateAll}
              disabled={generatingAll || isGenerating}
              variant="outline"
              className="flex items-center space-x-2 bg-purple-50 hover:bg-purple-100 border-purple-200"
            >
              {generatingAll || isGenerating ? (
                <Loader2 className="w-4 h-4 animate-spin text-purple-600" />
              ) : (
                <Sparkles className="w-4 h-4 text-purple-600" />
              )}
              <span className="text-purple-700">
                {generatingAll || isGenerating ? 'Generating...' : 'Regenerate All'}
              </span>
            </Button>
            <Button
              onClick={handleSave}
              disabled={saving}
              className="flex items-center space-x-2"
            >
              {saving ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Save className="w-4 h-4" />
              )}
              <span>{saving ? 'Saving...' : 'Save Changes'}</span>
            </Button>
          </div>
        </div>

        {/* Progress */}
        <Card className="mb-6">
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center space-x-2">
                <span className="font-medium">Completion Progress</span>
                {isGenerating && (
                  <div className="flex items-center space-x-1 text-sm text-blue-600">
                    <Loader2 className="w-3 h-3 animate-spin" />
                    <span>Generating answers...</span>
                  </div>
                )}
              </div>
              <span className="text-sm text-gray-600">{completionPercentage}%</span>
            </div>
            <Progress value={completionPercentage} className="w-full" />
            
            <div className="flex justify-between items-center text-xs text-gray-500 mt-2">
              <div className="flex space-x-4 flex-wrap gap-y-1">
                <span className="flex items-center gap-1">
                  <Building2 className="w-3 h-3 text-blue-600" />
                  {answers.filter(a => {
                    const q = questions.find(q => q.id === a.question_id)
                    return q?.question_category === 'entity_field' && a.answer_text
                  }).length} applicant fields
                </span>
                <span className="flex items-center gap-1">
                  <Globe className="w-3 h-3 text-purple-600" />
                  {answers.filter(a => {
                    const q = questions.find(q => q.id === a.question_id)
                    return q?.question_category === 'substantive_field' && a.answer_text
                  }).length}/{questions.filter(q => q.question_category === 'substantive_field').length} generated
                </span>
                <span>
                  {questions.filter(q => {
                    const a = answers.find(a => a.question_id === q.id)
                    return q.question_category === 'substantive_field' && !a?.answer_text
                  }).length} need input
                </span>
              </div>

              {isGenerating && (
                <div className="text-blue-600 font-medium">
                  {answersGenerated} / {totalQuestions} answers generated
                </div>
              )}
            </div>
            
            {/* Generation status message */}
            {isGenerating && (
              <div className="mt-3 p-2 bg-blue-50 border border-blue-200 rounded text-sm text-blue-700">
                Generating answers: entity fields filled instantly, then AI-generating substantive responses.
                This page updates automatically.
              </div>
            )}
          </CardContent>
        </Card>

        {/* Controls */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-4">
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
              <Input
                placeholder="Search questions..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 w-64"
              />
            </div>
            
            <Select value={filterType} onValueChange={(value: FilterType) => setFilterType(value)}>
              <SelectTrigger className="w-40">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Questions</SelectItem>
                <SelectItem value="completed">Completed</SelectItem>
                <SelectItem value="needs_review">Needs Review</SelectItem>
                <SelectItem value="draft">Drafts</SelectItem>
                <SelectItem value="ai_generated">AI Generated</SelectItem>
              </SelectContent>
            </Select>

            <Select value={groupBy} onValueChange={(value: GroupByType) => setGroupBy(value)}>
              <SelectTrigger className="w-48">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="question_set">By Question Set</SelectItem>
                <SelectItem value="section">By Section</SelectItem>
                <SelectItem value="status">By Status</SelectItem>
                <SelectItem value="none">No Grouping</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center space-x-2">
            <Button
              variant={showPreparation ? 'default' : 'outline'}
              size="sm"
              onClick={() => setShowPreparation(!showPreparation)}
            >
              {showPreparation ? 'Hide' : 'Show'} Preparation
            </Button>
            <Button
              variant={viewMode === 'list' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setViewMode('list')}
            >
              All Questions
            </Button>
            <Button
              variant={viewMode === 'single' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setViewMode('single')}
            >
              One by One
            </Button>
          </div>
        </div>

        {/* Preparation Checklist */}
        {showPreparation && (
          <ApplicationPreparationChecklist
            applicationId={applicationId || ''}
            onStartPreparation={(sectionName) => {
              // Navigate to first question in section
              const sectionQuestions = filteredQuestions.filter(q => q.subsection === sectionName)
              if (sectionQuestions.length > 0) {
                const questionIndex = filteredQuestions.findIndex(q => q.id === sectionQuestions[0].id)
                if (questionIndex >= 0) {
                  setCurrentQuestionIndex(questionIndex)
                  setViewMode('single')
                }
              }
            }}
          />
        )}

        {/* Content */}
        {viewMode === 'list' ? (
          <div className="flex gap-6">
            {/* TOC Sidebar -- desktop only */}
            <div className="hidden lg:block w-60 shrink-0">
              <div className="sticky top-20">
                <ApplicationTableOfContents
                  groupedQuestions={groupedQuestions}
                  answers={answers}
                  activeSectionId={activeSectionId}
                  expandedSections={expandedSections}
                  onSectionClick={handleSectionNavigation}
                  onExpandAll={expandAllSections}
                  onCollapseAll={collapseAllSections}
                  applicationType={application?.application_type}
                />
              </div>
            </div>
            {/* Main content */}
            <div className="flex-1 min-w-0">
              {Object.entries(groupedQuestions)
                .filter(([groupName]) => isSectionRelevant(groupName, (application?.application_type || 'standard') as ApplicationType))
                .sort(([a], [b]) => {
                  const numA = parseInt(a.match(/^(\d+)/)?.[1] || '999')
                  const numB = parseInt(b.match(/^(\d+)/)?.[1] || '999')
                  return numA - numB
                })
                .map(([groupName, groupQuestions]) => {
                  const isExpanded = expandedSections.has(groupName)
                  const completedCount = groupQuestions.filter(q => {
                    const a = answers.find(a => a.question_id === q.id)
                    return a?.answer_text
                  }).length
                  const isEntitySection = groupName.includes('Applying Entity Information')

                  return (
                    <div key={groupName} id={`section-${sectionSlug(groupName)}`} className="mb-8 scroll-mt-20">
                      <div className="flex items-center justify-between mb-4">
                        <button
                          onClick={() => toggleSection(groupName)}
                          className="text-left flex items-center flex-1 group"
                        >
                          <h2 className="text-lg font-semibold flex items-center space-x-2">
                            <ChevronDown className={`w-5 h-5 text-gray-400 transition-transform ${isExpanded ? '' : '-rotate-90'}`} />
                            <span>{groupName}</span>
                            <Badge variant="outline">{groupQuestions.length}</Badge>
                            <span className="text-sm font-normal text-gray-400">
                              {completedCount}/{groupQuestions.length} answered
                            </span>
                          </h2>
                        </button>
                        <button
                          onClick={(e) => { e.stopPropagation(); handleCopySection(groupName, groupQuestions) }}
                          className="text-xs text-gray-400 hover:text-gray-600 flex items-center gap-1 ml-2 shrink-0"
                          title="Copy all Q&A in this section"
                        >
                          {copiedSection === groupName ? (
                            <><CheckCircle2 className="w-3.5 h-3.5 text-green-500" /> Copied</>
                          ) : (
                            <><ClipboardCopy className="w-3.5 h-3.5" /> Copy</>
                          )}
                        </button>
                      </div>

                      {isExpanded && (
                        <div className="space-y-4">
                          {isEntitySection ? (
                            // Render entity questions using grouped form cards
                            <>
                              {ENTITY_FORM_GROUPS.map(group => renderEntityFormGroup(group, groupQuestions))}
                              {/* Render any entity questions not in a form group as individual cards */}
                              {groupQuestions
                                .filter(q => !ENTITY_GROUP_QUESTION_NUMBERS.has(q.question_number))
                                .map(question => renderSingleQuestion(question))}
                            </>
                          ) : (
                            // Render non-entity questions as individual cards
                            groupQuestions.map(question => renderSingleQuestion(question))
                          )}
                        </div>
                      )}
                    </div>
                  )
                })}

              {Object.keys(groupedQuestions).length === 0 && (
                <div className="text-center py-12">
                  <FileText className="w-16 h-16 mx-auto mb-4 text-gray-300" />
                  <p className="text-gray-600">No questions match your filters</p>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div>
            {filteredQuestions.length > 0 ? (
              <>
                <div className="flex items-center justify-between mb-4">
                  <span className="text-sm text-gray-600">
                    Question {currentQuestionIndex + 1} of {filteredQuestions.length}
                  </span>
                  <div className="flex items-center space-x-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setCurrentQuestionIndex(Math.max(0, currentQuestionIndex - 1))}
                      disabled={currentQuestionIndex === 0}
                    >
                      <ChevronLeft className="w-4 h-4" />
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setCurrentQuestionIndex(Math.min(filteredQuestions.length - 1, currentQuestionIndex + 1))}
                      disabled={currentQuestionIndex === filteredQuestions.length - 1}
                    >
                      Next
                      <ChevronRight className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
                {renderSingleQuestion(filteredQuestions[currentQuestionIndex])}
              </>
            ) : (
              <div className="text-center py-12">
                <FileText className="w-16 h-16 mx-auto mb-4 text-gray-300" />
                <p className="text-gray-600">No questions match your filters</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}