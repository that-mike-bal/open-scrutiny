/**
 * Routing question configuration for conditional question visibility.
 *
 * Routing questions are Yes/No gateway questions that show or hide
 * blocks of dependent questions based on the user's answer.
 */

export interface RoutingRule {
  routingQuestionNumber: string
  triggerValue: string        // The answer value that activates the dependent block
  dependentQuestions: string[] // Question numbers to show when triggered
  defaultVisible: boolean     // Whether dependents show before the routing Q is answered
}

export const ROUTING_RULES: RoutingRule[] = [
  {
    routingQuestionNumber: '131',
    triggerValue: 'yes',
    dependentQuestions: Array.from({ length: 26 }, (_, i) => String(132 + i)), // Q132-157
    defaultVisible: false,
  },
  {
    routingQuestionNumber: '158',
    triggerValue: 'yes',
    dependentQuestions: ['159', '160', '161'],
    defaultVisible: false,
  },
  {
    routingQuestionNumber: '162',
    triggerValue: 'yes',
    dependentQuestions: ['163'],
    defaultVisible: false,
  },
  {
    routingQuestionNumber: '172',
    triggerValue: 'yes',
    dependentQuestions: ['173', '174', '175'],
    defaultVisible: false,
  },
  {
    routingQuestionNumber: '179',
    triggerValue: 'yes',
    dependentQuestions: ['180', '181', '182', '183', '184'],
    defaultVisible: false,
  },
  {
    routingQuestionNumber: '185',
    triggerValue: 'yes',
    dependentQuestions: ['186', '187', '188'],
    defaultVisible: false,
  },
]

/** Set of all routing question numbers for quick lookup */
export const ROUTING_QUESTION_NUMBERS = new Set(
  ROUTING_RULES.map(r => r.routingQuestionNumber)
)

/** Set of all dependent question numbers (questions controlled by routing) */
export const ALL_DEPENDENT_QUESTIONS = new Set(
  ROUTING_RULES.flatMap(r => r.dependentQuestions)
)

// =========================================================================
// Financial Profile Routing (Q189-191 → mutually exclusive profile sets)
// =========================================================================

export type FinancialProfileType = 'government' | 'registry_operator' | 'top25' | 'standard'

export const FINANCIAL_PROFILE_QUESTIONS: Record<FinancialProfileType, string[]> = {
  government: Array.from({ length: 3 }, (_, i) => String(192 + i)),        // Q192-194
  registry_operator: Array.from({ length: 7 }, (_, i) => String(195 + i)), // Q195-201
  top25: Array.from({ length: 6 }, (_, i) => String(202 + i)),             // Q202-207
  standard: Array.from({ length: 12 }, (_, i) => String(208 + i)),         // Q208-219
}

/** All financial profile question numbers (for hiding non-matching profiles) */
export const ALL_FINANCIAL_PROFILE_QUESTIONS = new Set(
  Object.values(FINANCIAL_PROFILE_QUESTIONS).flat()
)

/** Determination questions that drive profile selection */
export const FINANCIAL_DETERMINATION_QUESTIONS = ['189', '190', '191']

/**
 * Determine which financial profile set to show based on Q189-191 answers.
 * Priority: Government > Registry Operator > Top 25 > Standard (default)
 */
export function getFinancialProfileType(
  getAnswerForQuestionNumber: (qNum: string) => string | undefined
): FinancialProfileType {
  if (getAnswerForQuestionNumber('189')?.toLowerCase() === 'yes') return 'government'
  if (getAnswerForQuestionNumber('190')?.toLowerCase() === 'yes') return 'registry_operator'
  if (getAnswerForQuestionNumber('191')?.toLowerCase() === 'yes') return 'top25'
  return 'standard'
}
