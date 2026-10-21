/**
 * Critical Tests for NewEvaluationModal Component
 * 
 * Tests the core string validation and submission functionality that protects
 * against invalid TLD submissions and ensures proper compliance checking.
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import NewEvaluationModal from '@/components/NewEvaluationModal'
import { checkBinaryCompliance } from '@/lib/binaryCompliance'

// Mock the binary compliance checker
vi.mock('@/lib/binaryCompliance', () => ({
  checkBinaryCompliance: vi.fn()
}))

// Mock fetch for local data files
global.fetch = vi.fn()

describe('NewEvaluationModal - String Validation', () => {
  const mockOnClose = vi.fn()
  const mockOnSuccess = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Binary Compliance Validation', () => {
    it('should reject existing IANA TLDs', async () => {
      const mockComplianceResults = {
        iana: { passes: false, reason: 'TLD already exists in IANA Root Zone' },
        blocked: { passes: true },
        reserved: { passes: true },
        existing: { passes: true },
        overall: { passes: false, reason: 'TLD already exists in IANA Root Zone' }
      }

      vi.mocked(checkBinaryCompliance).mockResolvedValue(mockComplianceResults)

      render(
        <NewEvaluationModal 
          isOpen={true} 
          onClose={mockOnClose} 
          onSuccess={mockOnSuccess} 
        />
      )

      const input = screen.getByPlaceholderText(/enter tld string/i)
      fireEvent.change(input, { target: { value: 'com' } })

      await waitFor(() => {
        expect(screen.getByText(/already exists in IANA Root Zone/i)).toBeInTheDocument()
        expect(screen.getByTestId('submit-button')).toBeDisabled()
      })
    })

    it('should reject ICANN blocked domains', async () => {
      const mockComplianceResults = {
        iana: { passes: true },
        blocked: { passes: false, reason: 'String is in ICANN blocked domains list' },
        reserved: { passes: true },
        existing: { passes: true },
        overall: { passes: false, reason: 'String is in ICANN blocked domains list' }
      }

      vi.mocked(checkBinaryCompliance).mockResolvedValue(mockComplianceResults)

      render(
        <NewEvaluationModal 
          isOpen={true} 
          onClose={mockOnClose} 
          onSuccess={mockOnSuccess} 
        />
      )

      const input = screen.getByPlaceholderText(/enter tld string/i)
      fireEvent.change(input, { target: { value: 'corp' } })

      await waitFor(() => {
        expect(screen.getByText(/ICANN blocked domains list/i)).toBeInTheDocument()
        expect(screen.getByTestId('submit-button')).toBeDisabled()
      })
    })

    it('should accept valid new TLD strings', async () => {
      const mockComplianceResults = {
        iana: { passes: true },
        blocked: { passes: true },
        reserved: { passes: true },
        existing: { passes: true },
        overall: { passes: true }
      }

      vi.mocked(checkBinaryCompliance).mockResolvedValue(mockComplianceResults)

      render(
        <NewEvaluationModal 
          isOpen={true} 
          onClose={mockOnClose} 
          onSuccess={mockOnSuccess} 
        />
      )

      const input = screen.getByPlaceholderText(/enter tld string/i)
      fireEvent.change(input, { target: { value: 'testvalidtld' } })

      await waitFor(() => {
        expect(screen.getByTestId('submit-button')).not.toBeDisabled()
      })
    })
  })

  describe('Input Sanitization', () => {
    it('should remove leading dots from input', async () => {
      render(
        <NewEvaluationModal 
          isOpen={true} 
          onClose={mockOnClose} 
          onSuccess={mockOnSuccess} 
        />
      )

      const input = screen.getByPlaceholderText(/enter tld string/i)
      fireEvent.change(input, { target: { value: '...test' } })

      expect(checkBinaryCompliance).toHaveBeenCalledWith('test')
    })

    it('should convert input to lowercase', async () => {
      render(
        <NewEvaluationModal 
          isOpen={true} 
          onClose={mockOnClose} 
          onSuccess={mockOnSuccess} 
        />
      )

      const input = screen.getByPlaceholderText(/enter tld string/i)
      fireEvent.change(input, { target: { value: 'TEST' } })

      expect(checkBinaryCompliance).toHaveBeenCalledWith('test')
    })

    it('should trim whitespace', async () => {
      render(
        <NewEvaluationModal 
          isOpen={true} 
          onClose={mockOnClose} 
          onSuccess={mockOnSuccess} 
        />
      )

      const input = screen.getByPlaceholderText(/enter tld string/i)
      fireEvent.change(input, { target: { value: '  test  ' } })

      expect(checkBinaryCompliance).toHaveBeenCalledWith('test')
    })
  })

  describe('Auto-execution Toggle', () => {
    it('should default to auto-execution enabled', () => {
      render(
        <NewEvaluationModal 
          isOpen={true} 
          onClose={mockOnClose} 
          onSuccess={mockOnSuccess} 
        />
      )

      const autoExecuteToggle = screen.getByRole('checkbox')
      expect(autoExecuteToggle).toBeChecked()
    })

    it('should allow disabling auto-execution', () => {
      render(
        <NewEvaluationModal 
          isOpen={true} 
          onClose={mockOnClose} 
          onSuccess={mockOnSuccess} 
        />
      )

      const autoExecuteToggle = screen.getByRole('checkbox')
      fireEvent.click(autoExecuteToggle)
      expect(autoExecuteToggle).not.toBeChecked()
    })
  })

  describe('Form Reset on Modal Open', () => {
    it('should reset form when modal reopens', () => {
      const { rerender } = render(
        <NewEvaluationModal 
          isOpen={false} 
          onClose={mockOnClose} 
          onSuccess={mockOnSuccess} 
        />
      )

      rerender(
        <NewEvaluationModal 
          isOpen={true} 
          onClose={mockOnClose} 
          onSuccess={mockOnSuccess} 
        />
      )

      const input = screen.getByPlaceholderText(/enter tld string/i)
      expect(input).toHaveValue('')
    })
  })
})