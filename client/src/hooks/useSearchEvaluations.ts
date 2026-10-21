import { useState, useCallback } from 'react'
import { getApiBase } from '@/lib/api-config'
import { type TldEvaluationWithAnalysis } from '@/types'

export function useSearchEvaluations() {
  const [searchResults, setSearchResults] = useState<TldEvaluationWithAnalysis[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [searchError, setSearchError] = useState<string | null>(null)

  const searchEvaluations = useCallback(async (query: string) => {
    if (!query.trim()) {
      setSearchResults([])
      return
    }

    setIsSearching(true)
    setSearchError(null)

    try {
      const response = await fetch(
        `${getApiBase()}/api/evaluations/search?q=${encodeURIComponent(query)}&limit=100`
      )

      if (!response.ok) {
        throw new Error(`Search failed: ${response.status}`)
      }

      const results = await response.json()
      setSearchResults(results || [])
    } catch (error) {
      console.warn('Server search failed, falling back to client-side:', error)
      setSearchError('Server search unavailable')
      // Don't set empty results - let the component handle fallback
      setSearchResults([])
    } finally {
      setIsSearching(false)
    }
  }, [])

  return {
    searchResults,
    isSearching,
    searchError,
    searchEvaluations
  }
}