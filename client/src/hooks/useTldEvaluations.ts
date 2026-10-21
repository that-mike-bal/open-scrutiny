// Reads via the anon client; relies on Row Level Security policies on tld_strings
// to return the rows the dashboard needs (previously used a service-role client).
import { supabase } from '@/lib/supabase'
import { useState, useEffect, useCallback, useRef } from 'react'
import { type TldEvaluationWithAnalysis } from '@/types'

const PAGE_SIZE = 50

export function useTldEvaluations(statusFilter?: string) {
  const [evaluations, setEvaluations] = useState<TldEvaluationWithAnalysis[]>([])
  const [loading, setLoading] = useState(true) // Start with true for initial load
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [hasMore, setHasMore] = useState(true)
  const [page, setPage] = useState(0)
  const [refetchTrigger, setRefetchTrigger] = useState(0)
  const isInitialMount = useRef(true)

  const fetchEvaluations = useCallback(async (pageNum: number, append: boolean = false) => {
    // Prevent duplicate calls
    if (append && loadingMore) return
    if (!append && loading && !isInitialMount.current) return
    
    if (append) {
      setLoadingMore(true)
    } else {
      setLoading(true)
    }
    setError(null)
    
    try {
      const offset = pageNum * PAGE_SIZE
      console.log(`🔄 Fetching evaluations from database... page: ${pageNum}, offset: ${offset}, status filter: ${statusFilter || 'none'}`)
      
      let query = supabase
        .from('tld_strings')
        .select('*')
        .order('updated_at', { ascending: false })
        .range(offset, offset + PAGE_SIZE - 1)
      
      // Apply status filter if provided
      if (statusFilter && statusFilter !== 'ALL') {
        query = query.eq('overall_status', statusFilter)
      }
      
      const { data, error: queryError } = await query
        
      if (queryError) {
        console.error('❌ Error fetching evaluations:', queryError)
        setError(queryError.message)
      } else {
        // Simplified data transformation - no expensive joins
        const transformedData = data?.map(item => {
          const actualStatus = (item.overall_status || 'PENDING').toString().toUpperCase()
          
          return {
            ...item,
            task_executions: [], // Will be loaded separately if needed
            workflow_executions: [], // Will be loaded separately if needed
            status: actualStatus,
            overall_status: actualStatus
          }
        }) || []
        
        console.log(`✅ Successfully fetched ${transformedData.length} evaluations (page ${pageNum})`)
        
        // Check if there are more results
        setHasMore(transformedData.length === PAGE_SIZE)
        
        if (append) {
          setEvaluations(prev => [...prev, ...transformedData])
        } else {
          setEvaluations(transformedData)
        }
      }
    } catch (err) {
      console.error('❌ Error fetching evaluations:', err)
      setError(err instanceof Error ? err.message : 'An unknown error occurred')
    } finally {
      setLoading(false)
      setLoadingMore(false)
      isInitialMount.current = false
    }
  }, [statusFilter, loading, loadingMore])

  const loadMore = useCallback(() => {
    if (!loadingMore && hasMore) {
      const nextPage = page + 1
      setPage(nextPage)
      fetchEvaluations(nextPage, true)
    }
  }, [page, loadingMore, hasMore, fetchEvaluations])

  const refetch = useCallback(() => {
    console.log('🔄 Manual refetch triggered')
    setPage(0)
    setHasMore(true)
    setRefetchTrigger(prev => prev + 1)
  }, [])

  // Initial fetch and refetch when filter changes
  useEffect(() => {
    setPage(0)
    setHasMore(true)
    fetchEvaluations(0, false)
  }, [refetchTrigger, statusFilter]) // eslint-disable-line react-hooks/exhaustive-deps

  return { evaluations, loading, loadingMore, error, refetch, loadMore, hasMore }
} 