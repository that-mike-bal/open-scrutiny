/**
 * Custom hook for tracking application generation progress in real-time.
 *
 * Only polls while the application is in an active generation state
 * ('Generating' or 'In_Progress'). Includes a safety timeout so polling
 * never runs indefinitely.
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { getTldApplication, type TldApplication } from '@/lib/supabase-api'

/** Maximum time (ms) to keep polling before giving up (5 minutes). */
const MAX_POLL_DURATION = 5 * 60 * 1000

interface ApplicationProgressHook {
  application: TldApplication | null
  isGenerating: boolean
  completionPercentage: number
  answersGenerated: number
  totalQuestions: number
  error: string | null
  refreshProgress: () => void
}

interface UseApplicationProgressOptions {
  applicationId: string
  /** Total question count — pass from the loaded questions array. */
  questionsCount?: number
  /** Polling interval in milliseconds (default: 3000ms). */
  pollInterval?: number
  /** Auto-stop polling when completion reaches this percentage (default: 100). */
  stopPollingAt?: number
  /** Enable the hook (default: true). */
  enabled?: boolean
}

/** Statuses that mean generation is actively running. */
const ACTIVE_STATUSES = new Set(['Generating', 'In_Progress'])
/** Statuses that mean we should definitely stop polling. */
const TERMINAL_STATUSES = new Set(['Completed', 'Failed', 'Ready_For_Review', 'Draft'])

export function useApplicationProgress(
  options: UseApplicationProgressOptions
): ApplicationProgressHook {
  const {
    applicationId,
    questionsCount,
    pollInterval = 3000,
    stopPollingAt = 100,
    enabled = true,
  } = options

  const [application, setApplication] = useState<TldApplication | null>(null)
  const [error, setError] = useState<string | null>(null)
  const intervalRef = useRef<NodeJS.Timeout | null>(null)
  const pollStartRef = useRef<number | null>(null)

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
    pollStartRef.current = null
  }, [])

  const refreshProgress = useCallback(async () => {
    if (!applicationId || !enabled) return

    try {
      const updatedApp = await getTldApplication(applicationId)
      setApplication(updatedApp)
      setError(null)

      // Determine whether we should stop
      const timedOut =
        pollStartRef.current != null &&
        Date.now() - pollStartRef.current > MAX_POLL_DURATION

      const shouldStop =
        !updatedApp ||
        updatedApp.completion_percentage >= stopPollingAt ||
        TERMINAL_STATUSES.has(updatedApp.status) ||
        timedOut

      if (shouldStop) {
        stopPolling()
      }
    } catch (err) {
      console.error('Error fetching application progress:', err)
      setError(err instanceof Error ? err.message : 'Failed to fetch progress')
    }
  }, [applicationId, enabled, stopPollingAt, stopPolling])

  // Initial load (one-time fetch)
  useEffect(() => {
    if (applicationId && enabled) {
      refreshProgress()
    }
  }, [applicationId, enabled]) // eslint-disable-line react-hooks/exhaustive-deps

  // Set up / tear down polling based on application status
  useEffect(() => {
    if (!enabled || !applicationId) return

    // Clear any existing interval first
    stopPolling()

    // Only start polling when the app is actively generating
    const isActive =
      application != null &&
      ACTIVE_STATUSES.has(application.status) &&
      application.completion_percentage < stopPollingAt

    if (isActive) {
      if (pollStartRef.current == null) {
        pollStartRef.current = Date.now()
      }
      intervalRef.current = setInterval(refreshProgress, pollInterval)
    }

    return () => {
      stopPolling()
    }
  }, [
    applicationId,
    pollInterval,
    stopPollingAt,
    enabled,
    application?.completion_percentage,
    application?.status,
    refreshProgress,
    stopPolling,
  ])

  // Derived state
  const isGenerating = application != null && ACTIVE_STATUSES.has(application.status)

  const completionPercentage = application?.completion_percentage ?? 0

  const totalQuestions = questionsCount ?? 0
  const answersGenerated =
    questionsCount && questionsCount > 0
      ? Math.round((completionPercentage / 100) * questionsCount)
      : 0

  return {
    application,
    isGenerating,
    completionPercentage,
    answersGenerated,
    totalQuestions,
    error,
    refreshProgress,
  }
}

/**
 * Hook for tracking progress during initial application creation.
 * Uses more aggressive polling for better UX during the creation phase.
 */
export function useApplicationCreationProgress(applicationId: string | null) {
  return useApplicationProgress({
    applicationId: applicationId || '',
    pollInterval: 1500,
    enabled: !!applicationId,
  })
}
