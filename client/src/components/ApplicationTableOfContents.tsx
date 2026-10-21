import { useEffect, useRef } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { CheckCircle2, ChevronsUpDown, ChevronsDownUp } from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  classifySectionType,
  isSectionRelevant,
  getSectionCompletion,
  sectionSlug,
  type ApplicationType
} from '@/lib/section-utils'

interface ApplicationTableOfContentsProps {
  groupedQuestions: Record<string, Array<{ id: string }>>
  answers: Array<{ question_id: string; answer_text?: string }>
  activeSectionId: string | null
  expandedSections: Set<string>
  onSectionClick: (sectionId: string) => void
  onExpandAll: () => void
  onCollapseAll: () => void
  applicationType?: string
}

const SECTION_TYPE_COLORS: Record<string, string> = {
  entity: 'bg-blue-500',
  conditional: 'bg-amber-500',
  financial: 'bg-green-500',
  standard: 'bg-gray-400',
}

export default function ApplicationTableOfContents({
  groupedQuestions,
  answers,
  activeSectionId,
  onSectionClick,
  onExpandAll,
  onCollapseAll,
  applicationType,
}: ApplicationTableOfContentsProps) {
  const activeRef = useRef<HTMLButtonElement | null>(null)

  // Auto-scroll active item into view
  useEffect(() => {
    if (activeRef.current) {
      activeRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
  }, [activeSectionId])

  const appType = (applicationType as ApplicationType) || 'standard'

  const sortedEntries = Object.entries(groupedQuestions).sort(([a], [b]) => {
    const numA = parseInt(a.match(/^(\d+)/)?.[1] || '999')
    const numB = parseInt(b.match(/^(\d+)/)?.[1] || '999')
    return numA - numB
  })

  return (
    <Card className="max-h-[calc(100vh-6rem)] flex flex-col">
      <CardHeader className="pb-2 px-4 pt-4">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-semibold">Sections</CardTitle>
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="sm"
              onClick={onExpandAll}
              className="h-7 w-7 p-0"
              title="Expand all sections"
            >
              <ChevronsUpDown className="w-3.5 h-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={onCollapseAll}
              className="h-7 w-7 p-0"
              title="Collapse all sections"
            >
              <ChevronsDownUp className="w-3.5 h-3.5" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="px-2 pb-3 overflow-y-auto flex-1">
        <nav className="space-y-0.5">
          {sortedEntries.map(([groupName, questions]) => {
            const slug = sectionSlug(groupName)
            const isActive = activeSectionId === slug
            const sectionType = classifySectionType(groupName)
            const dotColor = SECTION_TYPE_COLORS[sectionType] || SECTION_TYPE_COLORS.standard
            const relevant = isSectionRelevant(groupName, appType)
            const completion = getSectionCompletion(questions, answers)
            const isComplete = completion.status === 'complete'

            return (
              <button
                key={groupName}
                ref={isActive ? activeRef : null}
                onClick={() => onSectionClick(slug)}
                className={cn(
                  'w-full text-left px-3 py-2 rounded-md text-xs flex items-center gap-2 transition-colors',
                  isActive
                    ? 'bg-blue-50 border-l-2 border-blue-600 font-medium'
                    : 'hover:bg-gray-50 border-l-2 border-transparent',
                  !relevant && 'opacity-40'
                )}
              >
                <span className={cn('w-2 h-2 rounded-full shrink-0', dotColor)} />
                <span className="truncate flex-1">{groupName}</span>
                {!relevant && (
                  <span className="text-[10px] text-gray-400 shrink-0">(N/A)</span>
                )}
                {relevant && isComplete ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-green-500 shrink-0" />
                ) : relevant ? (
                  <span className="text-[10px] text-gray-400 shrink-0 tabular-nums">
                    {completion.completed}/{completion.total}
                  </span>
                ) : null}
              </button>
            )
          })}
        </nav>
      </CardContent>
    </Card>
  )
}
