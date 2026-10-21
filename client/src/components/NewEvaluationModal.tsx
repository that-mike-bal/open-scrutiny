import { useState, useEffect } from 'react'
import { checkBinaryCompliance } from '@/lib/binaryCompliance'
import { Button } from '@/components/ui/button'
import { CheckCircle, Shield, XCircle, Loader2 } from 'lucide-react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'

/**
 * NewEvaluationModal - TLD String Submission Component
 * 
 * ⚠️  CRITICAL ARCHITECTURE DECISION:
 * 
 * This component uses TWO DIFFERENT data sources for different purposes:
 * 
 * 1. LOCAL DATA FILES (for real-time compliance checks):
 *    - Used in: runComplianceChecks() function
 *    - Purpose: Instant validation as user types (1-5ms response)
 *    - Files: /public/data/Iana%20Root%20DB.json, reserved_names.json, ICANN%20gTLD%20Blocked%20Domains.json
 *    - Why: API calls would cause 8-second timeouts and poor UX
 * 
 * 2. BACKEND API (for actual submission):
 *    - Used in: handleSubmit() function  
 *    - Purpose: Create evaluation record and start CrewAI workflow
 *    - Endpoint: http://localhost:8000/api/evaluations/auto-submit
 *    - Why: This requires backend processing and database operations
 * 
 * 🚨 NEVER CHANGE THIS ARCHITECTURE without understanding the implications:
 * - Local files = instant validation, no network dependency
 * - Backend API = actual submission, requires service to be running
 * 
 * See: /client/public/data/README.md for detailed explanation
 */

interface NewEvaluationModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: (tldString: string, useCase: string, autoExecution: boolean, stringType?: 'primary' | 'secondary') => void
}

interface ComplianceResult {
  passes: boolean;
  reason?: string;
  category?: string;
  recommendation?: string;
  officialSource?: string;
}

interface ComplianceResults {
  iana: ComplianceResult;
  blocked: ComplianceResult;
  reserved: ComplianceResult;
  existing: ComplianceResult;
  overall: ComplianceResult;
}

export default function NewEvaluationModal({ isOpen, onClose, onSuccess }: NewEvaluationModalProps) {
  const [formData, setFormData] = useState({
    tld_string: '',
    use_case: '',
    enable_auto_execution: true,
    string_type: 'primary' as 'primary' | 'secondary'
  })
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [, setError] = useState<string | null>(null)
  const [complianceResults, setComplianceResults] = useState<ComplianceResults | null>(null)

  // Reset form when modal opens
  useEffect(() => {
    if (isOpen) {
      setFormData({ tld_string: '', use_case: '', enable_auto_execution: true, string_type: 'primary' })
      setError(null)
      setComplianceResults(null)
      setIsSubmitting(false)
    }
  }, [isOpen])

  // Run compliance checks when TLD string changes
  useEffect(() => {
    if (formData.tld_string.trim()) {
      runComplianceChecks()
    } else {
      setComplianceResults(null)
    }
  }, [formData.tld_string])

  const runComplianceChecks = async () => {
    const cleanTldString = formData.tld_string.replace(/^\.+/, '').toLowerCase().trim()
    if (!cleanTldString) return

    try {
      const results = await checkBinaryCompliance(cleanTldString)
      setComplianceResults(results)
    } catch (error) {
      setComplianceResults({
        iana: { passes: false, reason: 'IANA check failed' },
        blocked: { passes: false, reason: 'Blocked names check failed' },
        reserved: { passes: false, reason: 'Reserved names check failed' },
        existing: { passes: false, reason: 'Already evaluated check failed' },
        overall: { passes: false, reason: 'Validation failed' }
      })
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!formData.tld_string.trim()) {
      setError('Please enter a TLD string')
      return
    }
    if (!formData.use_case.trim()) {
      setError('Please enter a use case')
      return
    }
    if (!complianceResults?.overall.passes) {
      setError('TLD string failed compliance checks')
      return
    }
    
    setIsSubmitting(true)
    setError('')
    
    try {
      const cleanTldString = formData.tld_string.replace(/^\.+/, '').toLowerCase().trim()
      onSuccess(cleanTldString, formData.use_case, formData.enable_auto_execution, formData.string_type)
      onClose()
    } catch (err) {
      setError('An error occurred')
      setIsSubmitting(false)
    }
  }

  const handleClose = () => {
    if (isSubmitting) return
    setFormData({ tld_string: '', use_case: '', enable_auto_execution: true, string_type: 'primary' })
    setError(null)
    setComplianceResults(null)
    setIsSubmitting(false)
    onClose()
  }

  /**
   * Render individual compliance check result
   * Shows pass/fail status with detailed information
   */
  const renderComplianceCheck = (result: ComplianceResult, label: string) => {
    if (!result) return null;

    const getIcon = () => {
      if (result.passes) {
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      } else {
        return <XCircle className="h-5 w-5 text-red-500" />;
      }
    };

    const getStatusColor = () => {
      return result.passes ? 'text-green-700' : 'text-red-700';
    };

    const getBgColor = () => {
      return result.passes ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200';
    };

    return (
      <div className={`flex items-start space-x-3 p-3 rounded-lg border ${getBgColor()}`}>
        {getIcon()}
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between">
            <p className={`text-sm font-medium ${getStatusColor()}`}>
              {label}
            </p>
            {result.category && (
              <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                {result.category}
              </span>
            )}
          </div>
          <p className="text-sm text-gray-600 mt-1">
            {result.reason}
          </p>
          {result.officialSource && (
            <p className="text-xs text-gray-500 mt-1">
              Source: {result.officialSource}
            </p>
          )}
          {result.recommendation && (
            <p className="text-xs text-blue-600 mt-1 font-medium">
              💡 {result.recommendation}
            </p>
          )}
        </div>
      </div>
    );
  };

  const canSubmit = complianceResults?.overall.passes && formData.tld_string.trim() && formData.use_case.trim() && !isSubmitting

  if (!isOpen) return null

  return (
    <Dialog 
      key={isOpen ? 'open' : 'closed'}
      open={isOpen} 
      onOpenChange={(open) => {
        if (!open) {
          handleClose()
        }
      }}
    >
      <DialogContent className="sm:max-w-md max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Add New TLD Evaluation</DialogTitle>
        </DialogHeader>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="tld" className="block text-sm font-medium text-gray-700 mb-1">
              TLD String
            </label>
            <input
              id="tld"
              type="text"
              value={formData.tld_string}
              onChange={(e) => setFormData(prev => ({ ...prev, tld_string: e.target.value }))}
              placeholder="e.g., agent, guru, tech"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={isSubmitting}
              autoComplete="off"
            />
          </div>

          {/* Real-time compliance checks - uses LOCAL DATA FILES for instant validation */}
          {complianceResults && (
            <div className="space-y-3">
              <h4 className="text-sm font-medium text-gray-900 flex items-center gap-2">
                <Shield className="h-4 w-4" />
                Binary Compliance Results
              </h4>
              
              {complianceResults && (
                <div className="space-y-2">
                  {renderComplianceCheck(complianceResults.iana, 'IANA Database Check')}
                  {renderComplianceCheck(complianceResults.blocked, 'Blocked Names Check')}
                  {renderComplianceCheck(complianceResults.reserved, 'Reserved Names Check')}
                  {renderComplianceCheck(complianceResults.existing, 'Already Evaluated Check')}
                  
                  {/* Overall status */}
                  <div className={`p-3 rounded-lg border-2 ${
                    complianceResults.overall.passes 
                      ? 'bg-green-50 border-green-300' 
                      : 'bg-red-50 border-red-300'
                  }`}>
                    <div className="flex items-center gap-2">
                      {complianceResults.overall.passes ? (
                        <CheckCircle className="h-5 w-5 text-green-600" />
                      ) : (
                        <XCircle className="h-5 w-5 text-red-600" />
                      )}
                      <span className={`font-medium ${
                        complianceResults.overall.passes ? 'text-green-800' : 'text-red-800'
                      }`}>
                        {complianceResults.overall.passes ? 'Ready to Submit' : 'Cannot Submit'}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 mt-1">
                      {complianceResults.overall.reason}
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}

          <div>
            <label htmlFor="useCase" className="block text-sm font-medium text-gray-700 mb-1">
              Use Case
            </label>
            <textarea
              id="useCase"
              value={formData.use_case}
              onChange={(e) => setFormData(prev => ({ ...prev, use_case: e.target.value }))}
              placeholder="Describe the intended use case for this TLD..."
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={isSubmitting}
              autoComplete="off"
            />
          </div>

          <div>
            <label htmlFor="stringType" className="block text-sm font-medium text-gray-700 mb-1">
              String Type
            </label>
            <select
              id="stringType"
              value={formData.string_type}
              onChange={(e) => setFormData(prev => ({ ...prev, string_type: e.target.value as 'primary' | 'secondary' }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
              disabled={isSubmitting}
            >
              <option value="primary">Primary String</option>
              <option value="secondary">Secondary (Alternate) String</option>
            </select>
            <p className="text-xs text-gray-500 mt-1">
              ICANN allows one alternate string per application. Select "Secondary" for your alternate.
            </p>
          </div>

          <div className="flex justify-end space-x-2">
            <Button
              type="button"
              variant="outline"
              onClick={handleClose}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={!canSubmit}
              className={`${
                canSubmit 
                  ? 'bg-blue-600 hover:bg-blue-700' 
                  : 'bg-gray-300 cursor-not-allowed'
              }`}
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Submitting...
                </>
              ) : (
                'Submit Evaluation'
              )}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
} 