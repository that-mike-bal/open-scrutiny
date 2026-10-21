import React, { useState, useCallback } from 'react';
import { Button } from './ui/button';
import { 
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/dialog';
import { 
  Upload, 
  FileText, 
  Loader2 
} from 'lucide-react';

interface DocumentUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  documentType: {
    name: string;
    title: string;
    description: string;
    icannRequirements: string[];
    acceptedFormats: string[];
    maxSizeMB: number;
  };
  onUpload: (file: File, validationResult: ValidationResult) => void;
}

interface ValidationResult {
  valid: boolean;
  issues: string[];
  entity_match: boolean;
  date_valid: boolean;
  confidence: number;
  extractedText?: string;
}

export default function DocumentUploadModal({
  isOpen,
  onClose,
  documentType,
  onUpload
}: DocumentUploadModalProps) {
  const [dragActive, setDragActive] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [validating, setValidating] = useState(false);
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);
  const [error, setError] = useState('');

  const validateFile = (selectedFile: File): string => {
    const fileExtension = selectedFile.name.split('.').pop()?.toLowerCase();
    if (!fileExtension || !documentType.acceptedFormats.includes(fileExtension)) {
      return `File type not supported. Accepted formats: ${documentType.acceptedFormats.join(', ')}`;
    }

    const fileSizeMB = selectedFile.size / (1024 * 1024);
    if (fileSizeMB > documentType.maxSizeMB) {
      return `File size too large. Maximum size: ${documentType.maxSizeMB}MB`;
    }

    return '';
  };

  const performAIValidation = async (selectedFile: File): Promise<ValidationResult> => {
    setValidating(true);
    
    try {
      // Create FormData to send the file to the API
      const formData = new FormData();
      formData.append('document', selectedFile);
      formData.append('documentType', documentType.name);
      formData.append('applicantId', 'default'); // Replace with actual applicant ID
      
      const response = await fetch('/api/documents/validate', {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) {
        throw new Error(`Validation failed: ${response.status}`);
      }
      
      const result = await response.json();
      
      if (result.success) {
        return {
          valid: result.data.valid,
          issues: result.data.issues || [],
          entity_match: result.data.entity_match || false,
          date_valid: result.data.date_valid || false,
          confidence: result.data.confidence || 0,
          extractedText: result.data.extracted_text || ''
        };
      } else {
        throw new Error(result.message || 'Validation failed');
      }
      
    } catch (error) {
      console.error('Document validation error:', error);
      
      // Return a basic validation result based on file properties as fallback
      const fallbackResult: ValidationResult = {
        valid: false,
        issues: ['Could not perform AI validation - please verify document manually'],
        entity_match: false,
        date_valid: false,
        confidence: 0,
        extractedText: `Failed to extract text from ${selectedFile.name}`
      };
      
      return fallbackResult;
    } finally {
      setValidating(false);
    }
  };

  const handleFileSelection = async (selectedFile: File) => {
    const validationError = validateFile(selectedFile);
    if (validationError) {
      setError(validationError);
      return;
    }

    setFile(selectedFile);
    setError('');
    
    try {
      const result = await performAIValidation(selectedFile);
      setValidationResult(result);
    } catch (err) {
      setError('Failed to validate document. Please try again.');
    }
  };

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelection(e.dataTransfer.files[0]);
    }
  }, []);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelection(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file || !validationResult) return;

    setUploading(true);
    try {
      await onUpload(file, validationResult);
      onClose();
    } catch (err) {
      setError('Upload failed. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Upload: {documentType.title}</DialogTitle>
          <DialogDescription>
            {documentType.description}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          <div className="p-4 bg-blue-50 rounded-lg">
            <h4 className="font-medium text-blue-800 mb-2">📋 ICANN Requirements:</h4>
            <ul className="space-y-1">
              {documentType.icannRequirements.map((req, index) => (
                <li key={index} className="text-sm text-blue-700 flex items-start gap-2">
                  <span className="text-blue-500 mt-1">•</span>
                  <span>{req}</span>
                </li>
              ))}
            </ul>
          </div>

          <div
            className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
              dragActive ? 'border-blue-400 bg-blue-50' : 'border-gray-300 hover:border-gray-400'
            }`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
          >
            {file ? (
              <div className="space-y-4">
                <FileText className="w-8 h-8 text-gray-500 mx-auto" />
                <div>
                  <p className="font-medium text-gray-900">{file.name}</p>
                  <p className="text-sm text-gray-500">
                    {(file.size / (1024 * 1024)).toFixed(2)} MB
                  </p>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <Upload className="w-12 h-12 text-gray-400 mx-auto" />
                <div>
                  <p className="text-lg font-medium text-gray-900 mb-2">
                    Drop file here or click to browse
                  </p>
                  <p className="text-sm text-gray-500">
                    {documentType.acceptedFormats.join(', ').toUpperCase()} • Max {documentType.maxSizeMB}MB
                  </p>
                </div>
                <input
                  type="file"
                  accept={documentType.acceptedFormats.map(ext => `.${ext}`).join(',')}
                  onChange={handleFileInput}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                />
              </div>
            )}
          </div>

          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
              {error}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button 
            onClick={handleUpload}
            disabled={!file || uploading || validating}
          >
            {uploading ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Uploading...
              </>
            ) : (
              'Upload & Validate'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
