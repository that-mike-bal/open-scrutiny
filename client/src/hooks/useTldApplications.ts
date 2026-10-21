import { useState, useEffect, useCallback } from 'react'
import { getTldApplications, subscribeToAllApplicationUpdates, mapApplicationStatus, type TldApplication } from '@/lib/supabase-api'

export function useTldApplications() {
  const [applications, setApplications] = useState<TldApplication[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchApplications = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await getTldApplications()
      setApplications(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch applications')
      console.error('Error fetching applications:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  const refetch = useCallback(() => {
    return fetchApplications()
  }, [fetchApplications])

  useEffect(() => {
    fetchApplications()
  }, [fetchApplications])

  useEffect(() => {
    // Subscribe to real-time updates
    const subscription = subscribeToAllApplicationUpdates((payload) => {
      console.log('Application update received:', payload)
      
      if (payload.eventType === 'INSERT') {
        // New application created
        fetchApplications() // Refetch to get complete data with joins
      } else if (payload.eventType === 'UPDATE') {
        // Application updated — map raw DB status to frontend status
        const updated = payload.new
        setApplications(prev =>
          prev.map(app =>
            app.id === updated.id
              ? { ...app, ...updated, status: mapApplicationStatus(updated.status) }
              : app
          )
        )
      } else if (payload.eventType === 'DELETE') {
        // Application deleted
        setApplications(prev => 
          prev.filter(app => app.id !== payload.old.id)
        )
      }
    })

    return () => {
      subscription?.unsubscribe()
    }
  }, [fetchApplications])

  return {
    applications,
    loading,
    error,
    refetch
  }
}