import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Textarea } from '@/components/ui/textarea'
import {
  Sparkles,
  Copy,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Info,
  AlertTriangle,
  MessageSquarePlus
} from 'lucide-react'
import {
  generateRAGAnswer,
  copyToClipboard,
  formatConfidence,
  getDataSourceInfo,
  type RAGAnswerRequest,
  type RAGAnswerResponse,
  type QuestionCategory
} from '@/lib/application-rag-api'

interface RAGAnswerGeneratorProps {
  question: {
    id: string;
    question_number: string;
    question_text: string;
    subsection: string;
    character_limit?: number;
    question_category?: QuestionCategory;
  };
  application?: {
    id: string;
    tld_string: string;
    applicant_id?: string;
  };
  onAnswerGenerated?: (answer: string) => void;
  compact?: boolean;
  /** When true, requires a user prompt before generating (for insufficient-data questions) */
  requirePrompt?: boolean;
}

export default function RAGAnswerGenerator({
  question,
  application,
  onAnswerGenerated,
  compact = false,
  requirePrompt = false
}: RAGAnswerGeneratorProps) {
  const [generating, setGenerating] = useState(false)
  const [result, setResult] = useState<RAGAnswerResponse | null>(null)
  const [copySuccess, setCopySuccess] = useState(false)
  const [userPrompt, setUserPrompt] = useState('')

  const handleGenerate = async () => {
    setGenerating(true)

    const request: RAGAnswerRequest = {
      question_id: question.question_number,
      question_text: question.question_text,
      tld_string: application?.tld_string,
      applicant_id: application?.applicant_id,
      application_id: application?.id,
      question_category: question.question_category,
      user_prompt: userPrompt || undefined,
    }

    try {
      const response = await generateRAGAnswer(request)
      setResult(response)

      if (response.success && onAnswerGenerated) {
        const cleanAnswer = response.response
          .replace(/<!--.*?-->/g, '')
          .trim()
        onAnswerGenerated(cleanAnswer)
      }
    } catch (error) {
      console.error('Error generating answer:', error)
    } finally {
      setGenerating(false)
    }
  }

  const handleCopy = async () => {
    if (!result?.response) return

    const success = await copyToClipboard(result.response)
    if (success) {
      setCopySuccess(true)
      setTimeout(() => setCopySuccess(false), 2000)
    }
  }

  const isOverLimit = result?.success && question.character_limit &&
    result.response.length > question.character_limit

  const dataSourceInfo = result ? getDataSourceInfo(result.data_source) : null

  // Prompt-required mode: textarea + generate button
  if (requirePrompt) {
    return (
      <div className="space-y-3">
        <div className="space-y-2">
          <Textarea
            value={userPrompt}
            onChange={(e) => setUserPrompt(e.target.value)}
            placeholder="Provide direction for this answer (e.g., describe the applicant's approach, relevant experience, or key points to cover)..."
            className="min-h-[80px] text-sm"
          />
          <Button
            size="sm"
            onClick={handleGenerate}
            disabled={generating || !userPrompt.trim()}
            className="flex items-center gap-1"
          >
            {generating ? (
              <Loader2 className="w-3 h-3 animate-spin" />
            ) : (
              <MessageSquarePlus className="w-3 h-3" />
            )}
            {generating ? 'Generating...' : 'Generate with Prompt'}
          </Button>
        </div>

        {result?.success && (
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-3 h-3 text-green-600" />
              <span className="text-xs font-medium text-green-700">Generated</span>
              {dataSourceInfo && (
                <Badge variant="secondary" className="text-xs">
                  {dataSourceInfo.icon} {dataSourceInfo.name}
                </Badge>
              )}
              <Button size="sm" variant="ghost" onClick={handleCopy} className="h-6 px-2">
                {copySuccess ? (
                  <CheckCircle2 className="w-3 h-3 text-green-600" />
                ) : (
                  <Copy className="w-3 h-3" />
                )}
              </Button>
            </div>
            {isOverLimit && (
              <span className="flex items-center gap-1 text-xs text-red-600 font-medium">
                <AlertTriangle className="w-3 h-3" />
                Over character limit — edit before copying
              </span>
            )}
          </div>
        )}

        {result && !result.success && result.error && (
          <div className="text-xs text-red-600 flex items-start gap-1">
            <AlertCircle className="w-3 h-3 mt-0.5 shrink-0" />
            {result.error}
          </div>
        )}

        {result?.tip && !result.response && (
          <div className="text-xs text-amber-600 flex items-start gap-1">
            <Info className="w-3 h-3 mt-0.5 shrink-0" />
            {result.tip}
          </div>
        )}
      </div>
    )
  }

  // Compact mode: single row of buttons
  if (compact) {
    return (
      <div className="space-y-2">
        <div className="flex gap-2 items-center">
          <Button
            size="sm"
            variant="outline"
            onClick={handleGenerate}
            disabled={generating}
            className="flex items-center gap-1"
          >
            {generating ? (
              <Loader2 className="w-3 h-3 animate-spin" />
            ) : (
              <Sparkles className="w-3 h-3" />
            )}
            {generating ? 'Generating...' : 'Generate Answer'}
          </Button>

          {result?.success && (
            <Button
              size="sm"
              variant="ghost"
              onClick={handleCopy}
              className="flex items-center gap-1 h-8"
            >
              {copySuccess ? (
                <CheckCircle2 className="w-3 h-3 text-green-600" />
              ) : (
                <Copy className="w-3 h-3" />
              )}
              {copySuccess ? 'Copied!' : 'Copy'}
            </Button>
          )}
        </div>

        {/* Tip from entity/selection handler */}
        {result?.tip && !result.response && (
          <div className="text-xs text-amber-600 flex items-start gap-1">
            <Info className="w-3 h-3 mt-0.5 shrink-0" />
            {result.tip}
          </div>
        )}
      </div>
    )
  }

  // Full mode: card with result display
  return (
    <Card className="mb-4">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm font-medium">
            <Sparkles className="w-4 h-4" />
            AI Answer Generation
          </div>
          <div className="flex gap-1">
            <Button
              onClick={handleGenerate}
              disabled={generating}
              size="sm"
              className="flex items-center gap-1"
            >
              {generating ? (
                <Loader2 className="w-3 h-3 animate-spin" />
              ) : (
                <Sparkles className="w-3 h-3" />
              )}
              {generating ? 'Generating...' : result ? 'Regenerate' : 'Generate Answer'}
            </Button>
          </div>
        </div>
      </CardHeader>

      {result && (
        <CardContent className="pt-0 space-y-3">
          {/* Result header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {result.success ? (
                <CheckCircle2 className="w-4 h-4 text-green-600" />
              ) : (
                <AlertCircle className="w-4 h-4 text-red-600" />
              )}
              <span className="text-sm font-medium">
                {result.success ? 'Generated' : 'Generation Failed'}
              </span>
              {dataSourceInfo && (
                <Badge variant="secondary" className="text-xs">
                  {dataSourceInfo.icon} {dataSourceInfo.name}
                </Badge>
              )}
              {result.success && (
                <Badge variant="outline" className="text-xs">
                  {formatConfidence(result.confidence)}
                </Badge>
              )}
            </div>

            {result.success && (
              <div className="flex gap-1">
                <Button size="sm" variant="ghost" onClick={handleGenerate} className="h-7 px-2">
                  <RefreshCw className="w-3 h-3" />
                </Button>
                <Button size="sm" variant="ghost" onClick={handleCopy} className="h-7 px-2">
                  {copySuccess ? (
                    <CheckCircle2 className="w-3 h-3 text-green-600" />
                  ) : (
                    <Copy className="w-3 h-3" />
                  )}
                </Button>
              </div>
            )}
          </div>

          {/* Answer text */}
          {result.success && (
            <div className="text-sm bg-gray-50 p-3 rounded-md whitespace-pre-wrap">
              {result.response}
            </div>
          )}

          {/* Error message */}
          {!result.success && result.error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription className="text-sm">{result.error}</AlertDescription>
            </Alert>
          )}

          {/* Tip */}
          {result.tip && (
            <Alert>
              <Info className="h-4 w-4" />
              <AlertDescription className="text-sm">{result.tip}</AlertDescription>
            </Alert>
          )}

          {/* Character count + over-limit warning */}
          {result.success && question.character_limit && (
            <div className="flex items-center gap-2 text-xs">
              <span className={isOverLimit ? 'text-red-600 font-medium' : 'text-gray-500'}>
                {result.response.length} / {question.character_limit} characters
              </span>
              {isOverLimit && (
                <span className="flex items-center gap-1 text-red-600 font-medium bg-red-50 px-2 py-0.5 rounded">
                  <AlertTriangle className="w-3 h-3" />
                  Over limit — edit before copying
                </span>
              )}
            </div>
          )}
        </CardContent>
      )}
    </Card>
  )
}
