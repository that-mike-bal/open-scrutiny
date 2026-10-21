import { useState } from 'react';
import { Button } from './ui/button';
import { 
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/dialog';
import { Info, CheckCircle } from 'lucide-react';

interface EditFieldModalProps {
  isOpen: boolean;
  onClose: () => void;
  field: {
    name: string;
    label: string;
    currentValue: string | null;
    type: 'text' | 'email' | 'phone' | 'date' | 'textarea';
    description?: string;
    icannRequirement?: string;
    characterLimit?: number;
    validation?: {
      required: boolean;
      pattern?: string;
      minLength?: number;
      maxLength?: number;
    };
  };
  onSave: (value: string) => void;
}

export default function EditFieldModal({ 
  isOpen, 
  onClose, 
  field, 
  onSave 
}: EditFieldModalProps) {
  const [value, setValue] = useState(field.currentValue || '');
  const [error, setError] = useState('');

  const validateField = (inputValue: string): string => {
    if (field.validation?.required && !inputValue.trim()) {
      return 'This field is required';
    }

    if (field.validation?.minLength && inputValue.length < field.validation.minLength) {
      return `Minimum length is ${field.validation.minLength} characters`;
    }

    if (field.validation?.maxLength && inputValue.length > field.validation.maxLength) {
      return `Maximum length is ${field.validation.maxLength} characters`;
    }

    if (field.characterLimit && inputValue.length > field.characterLimit) {
      return `Character limit exceeded (${inputValue.length}/${field.characterLimit})`;
    }

    if (field.type === 'email' && inputValue && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(inputValue)) {
      return 'Please enter a valid email address';
    }

    if (field.validation?.pattern && inputValue && !new RegExp(field.validation.pattern).test(inputValue)) {
      return 'Invalid format';
    }

    return '';
  };

  const handleSave = () => {
    const validationError = validateField(value);
    if (validationError) {
      setError(validationError);
      return;
    }

    onSave(value);
    onClose();
  };

  const handleValueChange = (newValue: string) => {
    setValue(newValue);
    setError('');
  };

  const getInputComponent = () => {
    const baseClasses = `w-full p-3 border rounded-md ${
      error ? 'border-red-300 focus:border-red-500' : 'border-gray-300 focus:border-blue-500'
    } focus:outline-none focus:ring-1 ${
      error ? 'focus:ring-red-500' : 'focus:ring-blue-500'
    }`;

    switch (field.type) {
      case 'textarea':
        return (
          <textarea
            value={value}
            onChange={(e) => handleValueChange(e.target.value)}
            className={`${baseClasses} resize-none`}
            rows={4}
            placeholder={`Enter ${field.label.toLowerCase()}...`}
          />
        );
      
      case 'email':
        return (
          <input
            type="email"
            value={value}
            onChange={(e) => handleValueChange(e.target.value)}
            className={baseClasses}
            placeholder={`Enter ${field.label.toLowerCase()}...`}
          />
        );
      
      case 'phone':
        return (
          <input
            type="tel"
            value={value}
            onChange={(e) => handleValueChange(e.target.value)}
            className={baseClasses}
            placeholder="e.g., +1 234 567 8900"
          />
        );
      
      case 'date':
        return (
          <input
            type="date"
            value={value}
            onChange={(e) => handleValueChange(e.target.value)}
            className={baseClasses}
          />
        );
      
      default:
        return (
          <input
            type="text"
            value={value}
            onChange={(e) => handleValueChange(e.target.value)}
            className={baseClasses}
            placeholder={`Enter ${field.label.toLowerCase()}...`}
          />
        );
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Edit: {field.label}</DialogTitle>
          {field.description && (
            <DialogDescription className="text-gray-600">
              {field.description}
            </DialogDescription>
          )}
        </DialogHeader>

        <div className="space-y-4">
          {/* Current Value Display */}
          {field.currentValue && (
            <div className="p-3 bg-gray-50 rounded-md">
              <label className="text-sm font-medium text-gray-700 block mb-1">
                Current Value:
              </label>
              <span className="text-gray-900">{field.currentValue}</span>
            </div>
          )}

          {/* New Value Input */}
          <div>
            <label className="text-sm font-medium text-gray-700 block mb-2">
              New Value:
            </label>
            {getInputComponent()}
            {error && (
              <p className="text-red-600 text-sm mt-1">{error}</p>
            )}
          </div>

          {/* Field Context */}
          {field.description && (
            <div className="flex items-start gap-3 p-3 bg-blue-50 rounded-md">
              <Info className="w-5 h-5 text-blue-500 mt-0.5 flex-shrink-0" />
              <div className="text-sm">
                <p className="text-blue-800 font-medium mb-1">Field Information</p>
                <p className="text-blue-700">{field.description}</p>
              </div>
            </div>
          )}

          {/* Character Limit */}
          {field.characterLimit && (
            <div className="text-sm text-gray-500">
              📋 Character limit: {value.length}/{field.characterLimit}
            </div>
          )}

          {/* ICANN Requirements */}
          {field.icannRequirement && (
            <div className="flex items-start gap-3 p-3 bg-green-50 rounded-md">
              <CheckCircle className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" />
              <div className="text-sm">
                <p className="text-green-800 font-medium mb-1">ICANN Requirement</p>
                <p className="text-green-700">{field.icannRequirement}</p>
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button 
            onClick={handleSave}
            disabled={!!error || (field.validation?.required && !value.trim())}
          >
            Save Changes
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
} 