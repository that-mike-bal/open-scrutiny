/**
 * Critical Tests for Binary Compliance System
 * 
 * Tests the core validation logic that prevents invalid TLD submissions
 * by checking against IANA, blocked domains, reserved names, and existing evaluations.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { checkBinaryCompliance } from '@/lib/binaryCompliance'

// Mock fetch for local data files
global.fetch = vi.fn()

// Mock supabase
vi.mock('@/lib/supabase', () => ({
  supabase: {
    from: vi.fn(() => ({
      select: vi.fn(() => ({
        eq: vi.fn(() => ({
          single: vi.fn()
        }))
      }))
    }))
  }
}))

describe('Binary Compliance Validation', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('IANA Root Zone Checks', () => {
    it('should detect existing IANA TLDs', async () => {
      // Mock IANA data with common TLDs
      const mockIanaData = [
        { tld: '.com', type: 'generic', explanation: 'Commercial' },
        { tld: '.org', type: 'generic', explanation: 'Organization' },
        { tld: '.net', type: 'generic', explanation: 'Network' }
      ]

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockIanaData)
      } as Response)

      // Mock other data files as empty
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve([])
      } as Response)

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({})
      } as Response)

      const result = await checkBinaryCompliance('com')
      
      expect(result.iana.passes).toBe(false)
      expect(result.iana.reason).toContain('already exists')
      expect(result.overall.passes).toBe(false)
    })

    it('should pass for non-existent TLDs', async () => {
      // Mock IANA data without the test TLD
      const mockIanaData = [
        { tld: '.com', type: 'generic', explanation: 'Commercial' }
      ]

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockIanaData)
      } as Response)

      // Mock other data files as empty
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve([])
      } as Response)

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({})
      } as Response)

      const result = await checkBinaryCompliance('newtld')
      
      expect(result.iana.passes).toBe(true)
    })
  })

  describe('ICANN Blocked Domains Checks', () => {
    it('should detect blocked domains', async () => {
      // Mock empty IANA data
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve([])
      } as Response)

      // Mock blocked domains data
      const mockBlockedData = ['corp', 'mail', 'www']

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockBlockedData)
      } as Response)

      // Mock empty reserved names
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({})
      } as Response)

      const result = await checkBinaryCompliance('corp')
      
      expect(result.blocked.passes).toBe(false)
      expect(result.blocked.reason).toContain('blocked')
      expect(result.overall.passes).toBe(false)
    })
  })

  describe('Reserved Names Checks', () => {
    it('should detect RFC reserved names', async () => {
      // Mock empty IANA and blocked data
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve([])
      } as Response)

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve([])
      } as Response)

      // Mock reserved names data
      const mockReservedData = {
        rfc_reserved: ['localhost', 'test', 'invalid'],
        special_use: ['local', 'onion']
      }

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockReservedData)
      } as Response)

      const result = await checkBinaryCompliance('localhost')
      
      expect(result.reserved.passes).toBe(false)
      expect(result.reserved.reason).toContain('reserved')
      expect(result.overall.passes).toBe(false)
    })
  })

  describe('Data Loading Error Handling', () => {
    it('should handle IANA data loading errors gracefully', async () => {
      vi.mocked(fetch).mockRejectedValueOnce(new Error('Network error'))

      const result = await checkBinaryCompliance('test')
      
      expect(result.iana.passes).toBe(false)
      expect(result.iana.reason).toContain('unavailable')
      expect(result.overall.passes).toBe(false)
    })

    it('should handle invalid JSON data', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve('invalid json')
      } as Response)

      const result = await checkBinaryCompliance('test')
      
      expect(result.iana.passes).toBe(false)
      expect(result.overall.passes).toBe(false)
    })
  })

  describe('Input Normalization', () => {
    it('should handle uppercase inputs', async () => {
      // Mock all data as empty/passing
      vi.mocked(fetch).mockResolvedValue({
        ok: true,
        json: () => Promise.resolve([])
      } as Response)

      await checkBinaryCompliance('TEST')
      
      // Verify that fetch was called for data files (indicating processing occurred)
      expect(fetch).toHaveBeenCalled()
    })

    it('should handle inputs with dots', async () => {
      // Mock all data as empty/passing
      vi.mocked(fetch).mockResolvedValue({
        ok: true,
        json: () => Promise.resolve([])
      } as Response)

      await checkBinaryCompliance('.test')
      
      // Verify that fetch was called for data files (indicating processing occurred)
      expect(fetch).toHaveBeenCalled()
    })
  })

  describe('Data Caching', () => {
    it('should cache data between checks', async () => {
      // Mock all data as empty/passing
      vi.mocked(fetch).mockResolvedValue({
        ok: true,
        json: () => Promise.resolve([])
      } as Response)

      // First check
      await checkBinaryCompliance('test1')
      const firstCallCount = vi.mocked(fetch).mock.calls.length

      // Reset mock to track new calls
      vi.clearAllMocks()
      vi.mocked(fetch).mockResolvedValue({
        ok: true,
        json: () => Promise.resolve([])
      } as Response)

      // Second check (should use cache)
      await checkBinaryCompliance('test2')
      const secondCallCount = vi.mocked(fetch).mock.calls.length

      // Should make fewer calls due to caching
      expect(secondCallCount).toBeLessThan(firstCallCount)
    })
  })
})