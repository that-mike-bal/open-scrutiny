import { useMemo } from 'react'
import {
  ROUTING_RULES,
  ALL_FINANCIAL_PROFILE_QUESTIONS,
  FINANCIAL_PROFILE_QUESTIONS,
  getFinancialProfileType,
} from '@/lib/routing-questions'
import type { ApplicationQuestion, ApplicationAnswer } from '@/lib/supabase-api'

/**
 * Hook that computes which question numbers should be HIDDEN
 * based on routing question answers and financial profile determination.
 *
 * Returns a Set<string> of question numbers that should not be displayed.
 */
export function useRoutingQuestions(
  questions: ApplicationQuestion[],
  answers: ApplicationAnswer[]
): Set<string> {
  return useMemo(() => {
    const hidden = new Set<string>()

    // Helper: get the current answer text for a question number
    const getAnswerForQuestionNumber = (qNum: string): string | undefined => {
      const question = questions.find(q => q.question_number === qNum)
      if (!question) return undefined
      const answer = answers.find(a => a.question_id === question.id)
      return answer?.answer_text?.trim() || undefined
    }

    // 1. Apply Yes/No routing rules
    for (const rule of ROUTING_RULES) {
      const answerText = getAnswerForQuestionNumber(rule.routingQuestionNumber)
      const isTriggered = answerText?.toLowerCase() === rule.triggerValue

      if (!isTriggered) {
        // Not triggered — hide all dependent questions
        for (const qNum of rule.dependentQuestions) {
          hidden.add(qNum)
        }
      }
      // If triggered, dependents stay visible (not added to hidden set)
    }

    // 2. Apply financial profile routing (Q189-191)
    const profileType = getFinancialProfileType(getAnswerForQuestionNumber)
    const activeProfileQuestions = new Set(FINANCIAL_PROFILE_QUESTIONS[profileType])

    // Hide all financial profile questions except the active set
    for (const qNum of ALL_FINANCIAL_PROFILE_QUESTIONS) {
      if (!activeProfileQuestions.has(qNum)) {
        hidden.add(qNum)
      }
    }

    return hidden
  }, [questions, answers])
}
