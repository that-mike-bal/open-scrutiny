// ==========================================================================
// CUSTOMIZE: Section classification/relevance logic for the UI. Adjust to your domain's sections.
// This platform is a domain-agnostic evaluate-then-generate engine; the
// gTLD/ICANN ruleset is just the bundled example. Grep for 'CUSTOMIZE:'
// to find every retargeting point. See the README's Customize section.
// ==========================================================================

/**
 * Shared utilities for section navigation and classification
 */

export type SectionType = 'entity' | 'conditional' | 'financial' | 'standard'
export type ApplicationType = 'standard' | 'community' | 'brand' | 'geographic' | 'idn_variant'

export function sectionSlug(groupName: string): string {
  return groupName
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
}

export function classifySectionType(groupName: string): SectionType {
  const lower = groupName.toLowerCase()
  if (lower.includes('applying entity') || lower.includes('entity information')) return 'entity'
  if (/community|geographic|reserved|brand|code of conduct|voluntary/i.test(lower)) return 'conditional'
  if (/financial|profile|government|registry operator|top 25|standard financial/i.test(lower)) return 'financial'
  return 'standard'
}

// Maps conditional section keywords to the application types that should see them
const CONDITIONAL_SECTIONS: Record<string, ApplicationType[]> = {
  'community': ['community'],
  'geographic': ['geographic'],
  'reserved': [],                    // Flag-based (is_reserved_name), not type-based. Routing Q162 controls visibility.
  'brand tld': ['brand'],
  'code of conduct': ['brand'],
  'variant': ['standard', 'community', 'brand', 'geographic', 'idn_variant'],  // Any type can have variants
  'voluntary commitment': ['standard', 'community', 'geographic', 'brand'],     // Brand TLDs can make voluntary commitments
}

export function isSectionRelevant(groupName: string, applicationType: ApplicationType): boolean {
  const lowerName = groupName.toLowerCase()
  for (const [keyword, types] of Object.entries(CONDITIONAL_SECTIONS)) {
    if (lowerName.includes(keyword)) {
      return types.includes(applicationType)
    }
  }
  return true // non-conditional sections are always relevant
}

export interface SectionCompletionInfo {
  total: number
  completed: number
  percentage: number
  status: 'complete' | 'in-progress' | 'not-started'
}

export function getSectionCompletion(
  questions: Array<{ id: string }>,
  answers: Array<{ question_id: string; answer_text?: string }>
): SectionCompletionInfo {
  const total = questions.length
  const completed = questions.filter(q => {
    const answer = answers.find(a => a.question_id === q.id)
    return answer?.answer_text && answer.answer_text.trim().length > 0
  }).length
  const percentage = total > 0 ? Math.round((completed / total) * 100) : 0
  return {
    total,
    completed,
    percentage,
    status: percentage === 100 ? 'complete' : percentage > 0 ? 'in-progress' : 'not-started'
  }
}
