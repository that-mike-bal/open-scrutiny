/**
 * Critical Tests for UI Data Fetching and State Management
 * 
 * Tests the core hooks and state management that pull data from the API
 * and display it in the UI, ensuring data consistency and proper updates.
 */

import { renderHook, waitFor } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { useTldEvaluations } from '@/hooks/useTldEvaluations'

// Mock the supabase client
vi.mock('@/lib/supabase', () => ({
  supabase: {
    from: vi.fn(() => ({
      select: vi.fn(() => ({
        order: vi.fn(() => ({
          limit: vi.fn(() => ({
            eq: vi.fn(() => Promise.resolve({ data: [], error: null }))
          }))
        }))
      }))
    }))
  }
}))

describe('useTldEvaluations Hook', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Data Fetching', () => {
    it('should fetch evaluations on mount', async () => {
      const mockData = [
        {
          id: 'eval-1',
          tld_string: 'test1',
          overall_status: 'COMPLETED',
          generated_report: {
            risk_assessment: { risk_level: 'LOW' }
          },
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T01:00:00Z'
        },
        {
          id: 'eval-2',
          tld_string: 'test2',
          overall_status: 'RUNNING',
          generated_report: null,
          created_at: '2024-01-01T00:30:00Z',
          updated_at: '2024-01-01T00:30:00Z'
        }
      ]

      // Mock successful API response
      const { supabase } = await import('@/lib/supabase')
      vi.mocked(supabase.from).mockReturnValue({
        select: vi.fn(() => ({
          order: vi.fn(() => ({
            limit: vi.fn(() => Promise.resolve({ data: mockData, error: null }))
          }))
        }))
      } as any)

      const { result } = renderHook(() => useTldEvaluations())

      // Initial state
      expect(result.current.loading).toBe(true)
      expect(result.current.evaluations).toEqual([])

      // Wait for data to load
      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      expect(result.current.evaluations).toHaveLength(2)
      expect(result.current.evaluations[0].tld_string).toBe('test1')
      expect(result.current.evaluations[1].tld_string).toBe('test2')
      expect(result.current.error).toBe(null)
    })

    it('should handle API errors gracefully', async () => {
      // Mock API error
      const { supabase } = await import('@/lib/supabase')
      vi.mocked(supabase.from).mockReturnValue({
        select: vi.fn(() => ({
          order: vi.fn(() => ({
            limit: vi.fn(() => Promise.resolve({ 
              data: null, 
              error: { message: 'Database connection failed' }
            }))
          }))
        }))
      } as any)

      const { result } = renderHook(() => useTldEvaluations())

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      expect(result.current.evaluations).toEqual([])
      expect(result.current.error).toBe('Database connection failed')
    })

    it('should apply status filter correctly', async () => {
      const { supabase } = await import('@/lib/supabase')
      const mockEq = vi.fn(() => Promise.resolve({ data: [], error: null }))
      
      vi.mocked(supabase.from).mockReturnValue({
        select: vi.fn(() => ({
          order: vi.fn(() => ({
            limit: vi.fn(() => ({
              eq: mockEq
            }))
          }))
        }))
      } as any)

      renderHook(() => useTldEvaluations('COMPLETED'))

      await waitFor(() => {
        expect(mockEq).toHaveBeenCalledWith('overall_status', 'COMPLETED')
      })
    })

    it('should not apply filter when status is ALL', async () => {
      const { supabase } = await import('@/lib/supabase')
      const mockLimit = vi.fn(() => Promise.resolve({ data: [], error: null }))
      
      vi.mocked(supabase.from).mockReturnValue({
        select: vi.fn(() => ({
          order: vi.fn(() => ({
            limit: mockLimit
          }))
        }))
      } as any)

      renderHook(() => useTldEvaluations('ALL'))

      await waitFor(() => {
        expect(mockLimit).toHaveBeenCalled()
      })
    })
  })

  describe('State Management', () => {
    it('should handle loading states correctly', async () => {
      const { supabase } = await import('@/lib/supabase')
      
      // Create a promise that we can resolve manually
      let resolvePromise: (value: any) => void
      const dataPromise = new Promise(resolve => {
        resolvePromise = resolve
      })

      vi.mocked(supabase.from).mockReturnValue({
        select: vi.fn(() => ({
          order: vi.fn(() => ({
            limit: vi.fn(() => dataPromise)
          }))
        }))
      } as any)

      const { result } = renderHook(() => useTldEvaluations())

      // Should start loading
      expect(result.current.loading).toBe(true)
      expect(result.current.evaluations).toEqual([])

      // Resolve the promise
      resolvePromise!({ data: [], error: null })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })
    })

    it('should prevent duplicate calls while loading', async () => {
      const { supabase } = await import('@/lib/supabase')
      const mockLimit = vi.fn(() => Promise.resolve({ data: [], error: null }))
      
      vi.mocked(supabase.from).mockReturnValue({
        select: vi.fn(() => ({
          order: vi.fn(() => ({
            limit: mockLimit
          }))
        }))
      } as any)

      const { result, rerender } = renderHook(() => useTldEvaluations())

      // Trigger multiple rerenders while loading
      rerender()
      rerender()
      rerender()

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      // Should only call the API once despite multiple rerenders
      expect(mockLimit).toHaveBeenCalledTimes(1)
    })

    it('should support manual refetch', async () => {
      const { supabase } = await import('@/lib/supabase')
      const mockLimit = vi.fn(() => Promise.resolve({ data: [], error: null }))
      
      vi.mocked(supabase.from).mockReturnValue({
        select: vi.fn(() => ({
          order: vi.fn(() => ({
            limit: mockLimit
          }))
        }))
      } as any)

      const { result } = renderHook(() => useTldEvaluations())

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      // Verify initial call
      expect(mockLimit).toHaveBeenCalledTimes(1)

      // Trigger manual refetch
      result.current.refetch()

      await waitFor(() => {
        expect(mockLimit).toHaveBeenCalledTimes(2)
      })
    })
  })

  describe('Data Transformation', () => {
    it('should transform status to uppercase', async () => {
      const mockData = [
        {
          id: 'eval-1',
          tld_string: 'test',
          overall_status: 'completed', // lowercase
          created_at: '2024-01-01T00:00:00Z'
        }
      ]

      const { supabase } = await import('@/lib/supabase')
      vi.mocked(supabase.from).mockReturnValue({
        select: vi.fn(() => ({
          order: vi.fn(() => ({
            limit: vi.fn(() => Promise.resolve({ data: mockData, error: null }))
          }))
        }))
      } as any)

      const { result } = renderHook(() => useTldEvaluations())

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      expect(result.current.evaluations[0].status).toBe('COMPLETED')
      expect(result.current.evaluations[0].overall_status).toBe('COMPLETED')
    })

    it('should handle missing status gracefully', async () => {
      const mockData = [
        {
          id: 'eval-1',
          tld_string: 'test',
          overall_status: null, // missing status
          created_at: '2024-01-01T00:00:00Z'
        }
      ]

      const { supabase } = await import('@/lib/supabase')
      vi.mocked(supabase.from).mockReturnValue({
        select: vi.fn(() => ({
          order: vi.fn(() => ({
            limit: vi.fn(() => Promise.resolve({ data: mockData, error: null }))
          }))
        }))
      } as any)

      const { result } = renderHook(() => useTldEvaluations())

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      expect(result.current.evaluations[0].status).toBe('PENDING')
      expect(result.current.evaluations[0].overall_status).toBe('PENDING')
    })

    it('should initialize empty arrays for task and workflow executions', async () => {
      const mockData = [
        {
          id: 'eval-1',
          tld_string: 'test',
          overall_status: 'COMPLETED',
          created_at: '2024-01-01T00:00:00Z'
        }
      ]

      const { supabase } = await import('@/lib/supabase')
      vi.mocked(supabase.from).mockReturnValue({
        select: vi.fn(() => ({
          order: vi.fn(() => ({
            limit: vi.fn(() => Promise.resolve({ data: mockData, error: null }))
          }))
        }))
      } as any)

      const { result } = renderHook(() => useTldEvaluations())

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      expect(result.current.evaluations[0].task_executions).toEqual([])
      expect(result.current.evaluations[0].workflow_executions).toEqual([])
    })
  })

  describe('Performance Optimizations', () => {
    it('should limit results to prevent timeouts', async () => {
      const { supabase } = await import('@/lib/supabase')
      const mockLimit = vi.fn(() => Promise.resolve({ data: [], error: null }))
      
      vi.mocked(supabase.from).mockReturnValue({
        select: vi.fn(() => ({
          order: vi.fn(() => ({
            limit: mockLimit
          }))
        }))
      } as any)

      renderHook(() => useTldEvaluations())

      await waitFor(() => {
        expect(mockLimit).toHaveBeenCalledWith(200)
      })
    })

    it('should order results by updated_at descending', async () => {
      const { supabase } = await import('@/lib/supabase')
      const mockOrder = vi.fn(() => ({
        limit: vi.fn(() => Promise.resolve({ data: [], error: null }))
      }))
      
      vi.mocked(supabase.from).mockReturnValue({
        select: vi.fn(() => ({
          order: mockOrder
        }))
      } as any)

      renderHook(() => useTldEvaluations())

      await waitFor(() => {
        expect(mockOrder).toHaveBeenCalledWith('updated_at', { ascending: false })
      })
    })
  })

  describe('Error Recovery', () => {
    it('should clear errors on successful refetch', async () => {
      const { supabase } = await import('@/lib/supabase')
      
      // First call fails
      vi.mocked(supabase.from).mockReturnValueOnce({
        select: vi.fn(() => ({
          order: vi.fn(() => ({
            limit: vi.fn(() => Promise.resolve({ 
              data: null, 
              error: { message: 'Network error' }
            }))
          }))
        }))
      } as any)

      const { result } = renderHook(() => useTldEvaluations())

      await waitFor(() => {
        expect(result.current.error).toBe('Network error')
      })

      // Second call succeeds
      vi.mocked(supabase.from).mockReturnValueOnce({
        select: vi.fn(() => ({
          order: vi.fn(() => ({
            limit: vi.fn(() => Promise.resolve({ 
              data: [], 
              error: null
            }))
          }))
        }))
      } as any)

      result.current.refetch()

      await waitFor(() => {
        expect(result.current.error).toBe(null)
      })
    })

    it('should handle network exceptions', async () => {
      const { supabase } = await import('@/lib/supabase')
      
      vi.mocked(supabase.from).mockReturnValue({
        select: vi.fn(() => ({
          order: vi.fn(() => ({
            limit: vi.fn(() => Promise.reject(new Error('Network timeout')))
          }))
        }))
      } as any)

      const { result } = renderHook(() => useTldEvaluations())

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      expect(result.current.error).toBe('Network timeout')
      expect(result.current.evaluations).toEqual([])
    })
  })
})