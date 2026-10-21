import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import EditFieldModal from './EditFieldModal';
import DocumentUploadModal from './DocumentUploadModal';
import { 
  FileText, 
  Edit3, 
  CheckCircle, 
  AlertCircle, 
  XCircle, 
  Upload,
  ChevronDown,
  ChevronUp,
  User,
  Building,
  FileCheck,
  Clock,
  ArrowLeft
} from 'lucide-react';

interface ApplicantData {
  id: string;
  legal_name: string;
  business_name: string;
  entity_type: string;
  jurisdiction: string;
  incorporation_date: string;
  business_address: string;
  mailing_address: string;
  phone: string;
  email: string;
  website: string;
  key_personnel: any[];
  registry_experience_description: string;
  current_tlds: string[];
  affiliated_organizations: string[];
  funding_sources: string;
  completion_percentage?: number;
  missing_fields?: string[];
  // Additional optional fields that might be missing
  lei?: string;
  primary_contact_address?: string;
}

interface MissingField {
  field: string;
  label: string;
  description: string;
  required: boolean;
  section: string;
  type: 'text' | 'email' | 'phone' | 'date' | 'textarea' | 'document';
}

interface DocumentType {
  name: string;
  title: string;
  description: string;
  icannRequirements: string[];
  acceptedFormats: string[];
  maxSizeMB: number;
  status: 'missing' | 'uploaded' | 'verified' | 'rejected';
}

const StatusIcon = ({ status }: { status: 'verified' | 'missing' | 'partial' | 'pending' }) => {
  switch (status) {
    case 'verified':
      return <CheckCircle className="w-4 h-4 text-green-500" />;
    case 'missing':
      return <XCircle className="w-4 h-4 text-red-500" />;
    case 'partial':
      return <AlertCircle className="w-4 h-4 text-yellow-500" />;
    case 'pending':
      return <Clock className="w-4 h-4 text-blue-500" />;
    default:
      return null;
  }
};

const EditableField = ({ 
  label, 
  value, 
  status, 
  onEdit, 
  className = "" 
}: {
  label: string;
  value: string | null;
  status: 'verified' | 'missing' | 'partial' | 'pending';
  onEdit: () => void;
  className?: string;
}) => {
  return (
    <div className={`group cursor-pointer hover:bg-gray-50 p-2 rounded transition-colors ${className}`} onClick={onEdit}>
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="font-medium text-sm text-gray-700">{label}:</span>
            <StatusIcon status={status} />
          </div>
          <div className="mt-1">
            {value ? (
              <span className="text-gray-900">{value}</span>
            ) : (
              <span className="text-gray-400 italic">[Missing]</span>
            )}
          </div>
        </div>
        <Edit3 className="w-4 h-4 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity" />
      </div>
    </div>
  );
};

const MissingDataQueue = ({ 
  missingFields, 
  currentIndex, 
  onNext, 
  onSkip, 
  onViewInDocument 
}: {
  missingFields: MissingField[];
  currentIndex: number;
  onNext: (data: any) => void;
  onSkip: () => void;
  onViewInDocument: () => void;
}) => {
  const [inputValue, setInputValue] = useState('');
  const currentField = missingFields[currentIndex];

  if (!currentField) {
    return (
      <Card className="bg-green-50 border-green-200">
        <CardContent className="p-6 text-center">
          <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-green-800 mb-2">All Information Complete!</h3>
          <p className="text-green-600">All required and optional fields have been filled.</p>
        </CardContent>
      </Card>
    );
  }

  const progress = ((missingFields.length - currentIndex) / missingFields.length) * 100;

  return (
    <Card className="sticky top-4">
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>Missing Information ({missingFields.length - currentIndex} remaining)</span>
          <Badge variant={currentField.required ? "destructive" : "secondary"}>
            {currentField.required ? 'Required' : 'Optional'}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <h4 className="font-medium text-gray-900 mb-2 flex items-center gap-2">
            <FileText className="w-4 h-4" />
            {currentField.label}
          </h4>
          <p className="text-sm text-gray-600 mb-4">{currentField.description}</p>
          
          {currentField.type === 'textarea' ? (
            <textarea
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              className="w-full p-3 border border-gray-300 rounded-md resize-none"
              rows={4}
              placeholder={`Enter ${currentField.label.toLowerCase()}...`}
            />
          ) : (
            <input
              type={currentField.type === 'email' ? 'email' : currentField.type === 'date' ? 'date' : 'text'}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              className="w-full p-3 border border-gray-300 rounded-md"
              placeholder={`Enter ${currentField.label.toLowerCase()}...`}
            />
          )}
        </div>

        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={onSkip}
            disabled={currentField.required}
          >
            Skip
          </Button>
          <Button
            size="sm"
            onClick={() => {
              onNext({ [currentField.field]: inputValue });
              setInputValue('');
            }}
            disabled={currentField.required && !inputValue.trim()}
          >
            Save & Next
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={onViewInDocument}
          >
            View in Doc
          </Button>
        </div>

        <div>
          <div className="flex justify-between text-sm text-gray-600 mb-2">
            <span>Progress</span>
            <span>{Math.round(progress)}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className="bg-blue-500 h-2 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

const DocumentSection = ({ 
  applicantData, 
  onFieldEdit, 
  onDocumentUpload 
}: { 
  applicantData: ApplicantData;
  onFieldEdit: (field: any) => void;
  onDocumentUpload: (docType: DocumentType) => void;
}) => {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['organization']));

  const toggleSection = (sectionId: string) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(sectionId)) {
      newExpanded.delete(sectionId);
    } else {
      newExpanded.add(sectionId);
    }
    setExpandedSections(newExpanded);
  };

  const getFieldStatus = (value: any): 'verified' | 'missing' | 'partial' => {
    if (!value) return 'missing';
    if (typeof value === 'string' && value.trim() === '') return 'missing';
    if (Array.isArray(value) && value.length === 0) return 'missing';
    return 'verified';
  };

  const documentTypes: DocumentType[] = [
    {
      name: 'articles_of_incorporation',
      title: 'Articles of Incorporation',
      description: 'ICANN Requirement: Proof of legal entity establishment',
      icannRequirements: [
        'Must be issued by official government authority',
        'Must clearly identify the entity name',
        'Must show date of incorporation',
        'Must be officially stamped or certified'
      ],
      acceptedFormats: ['pdf', 'doc', 'docx', 'jpg', 'png'],
      maxSizeMB: 10,
      status: 'missing'
    },
    {
      name: 'good_standing_certificate',
      title: 'Good Standing Certificate',
      description: 'ICANN Requirement: Must be no more than 6 months old',
      icannRequirements: [
        'No more than 6 months old',
        'Shows entity in good standing',
        'From official government authority',
        'Must clearly identify the entity'
      ],
      acceptedFormats: ['pdf', 'doc', 'docx', 'jpg', 'png'],
      maxSizeMB: 10,
      status: 'missing'
    },
    {
      name: 'financial_statements',
      title: 'Financial Statements',
      description: 'ICANN Requirement: Audited statements from certified accountant',
      icannRequirements: [
        'Must be audited by certified accountant',
        'Must cover most recent fiscal year',
        'Must include balance sheet and income statement',
        'Must show adequate financial resources'
      ],
      acceptedFormats: ['pdf', 'doc', 'docx'],
      maxSizeMB: 20,
      status: 'missing'
    }
  ];

  return (
    <div className="max-w-4xl mx-auto">
      {/* Document Header */}
      <div className="mb-8 p-6 bg-white border border-gray-200 rounded-lg">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Example Registry Ltd.</h1>
            <h2 className="text-xl text-gray-600 mb-4">Applicant Information Document</h2>
            <p className="text-sm text-gray-500">
              Last updated: {new Date().toLocaleDateString()} • 
              Completion: {applicantData.completion_percentage || 75}%
            </p>
          </div>
          <div className="text-right">
            <Badge variant="secondary" className="mb-2">
              ICANN Application Ready: {(applicantData.completion_percentage || 75) >= 90 ? 'Yes' : 'No'}
            </Badge>
            <div className="text-sm text-gray-500">
              {applicantData.missing_fields?.length || 0} fields remaining
            </div>
          </div>
        </div>
      </div>

      {/* Organization Profile Section */}
      <Card className="mb-6">
        <CardHeader 
          className="cursor-pointer hover:bg-gray-50 transition-colors"
          onClick={() => toggleSection('organization')}
        >
          <CardTitle className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Building className="w-5 h-5" />
              <span>1. Organization Profile</span>
              <Badge variant="outline">8 fields</Badge>
              <Badge variant="outline" className="text-yellow-600">2 missing</Badge>
            </div>
            {expandedSections.has('organization') ? 
              <ChevronUp className="w-5 h-5" /> : 
              <ChevronDown className="w-5 h-5" />
            }
          </CardTitle>
        </CardHeader>
        
        {expandedSections.has('organization') && (
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <EditableField
                label="Legal Entity Name"
                value={applicantData.legal_name}
                status={getFieldStatus(applicantData.legal_name)}
                onEdit={() => onFieldEdit({
                  name: 'legal_name',
                  label: 'Legal Entity Name',
                  currentValue: applicantData.legal_name,
                  type: 'text',
                  description: 'Your official legal entity name as registered with your jurisdiction',
                  icannRequirement: 'Must match legal documents exactly',
                  characterLimit: 255,
                  validation: { required: true, minLength: 2, maxLength: 255 }
                })}
              />
              <EditableField
                label="Entity Type"
                value={applicantData.entity_type}
                status={getFieldStatus(applicantData.entity_type)}
                onEdit={() => onFieldEdit({
                  name: 'entity_type',
                  label: 'Entity Type',
                  currentValue: applicantData.entity_type,
                  type: 'text',
                  description: 'Legal structure of your organization (e.g., Limited Company, Corporation)',
                  icannRequirement: 'Must be a legally recognized business entity type',
                  validation: { required: true }
                })}
              />
              <EditableField
                label="Registration Number"
                value="EX-0000001"
                status="verified"
                onEdit={() => {}}
              />
              <EditableField
                label="Legal Entity Identifier"
                value={null}
                status="missing"
                onEdit={() => onFieldEdit({
                  name: 'lei',
                  label: 'Legal Entity Identifier',
                  currentValue: null,
                  type: 'text',
                  description: 'Enter the 20-character alphanumeric Legal Entity Identifier if available',
                  icannRequirement: 'LEI is recommended for large organizations',
                  validation: { required: false, pattern: '^[A-Z0-9]{20}$' }
                })}
              />
              <EditableField
                label="Incorporation Date"
                value={applicantData.incorporation_date}
                status={getFieldStatus(applicantData.incorporation_date)}
                onEdit={() => onFieldEdit({
                  name: 'incorporation_date',
                  label: 'Incorporation Date',
                  currentValue: applicantData.incorporation_date,
                  type: 'date',
                  description: 'Date when your organization was legally incorporated',
                  icannRequirement: 'Must match official incorporation documents',
                  validation: { required: true }
                })}
              />
              <EditableField
                label="Jurisdiction"
                value={applicantData.jurisdiction}
                status={getFieldStatus(applicantData.jurisdiction)}
                onEdit={() => onFieldEdit({
                  name: 'jurisdiction',
                  label: 'Jurisdiction',
                  currentValue: applicantData.jurisdiction,
                  type: 'text',
                  description: 'Country/state where your organization is legally incorporated',
                  icannRequirement: 'Must be a recognized legal jurisdiction',
                  validation: { required: true }
                })}
              />
            </div>

            <div className="mt-6">
              <EditableField
                label="Primary Business Address"
                value={applicantData.business_address}
                status={getFieldStatus(applicantData.business_address)}
                onEdit={() => onFieldEdit({
                  name: 'business_address',
                  label: 'Primary Business Address',
                  currentValue: applicantData.business_address,
                  type: 'textarea',
                  description: 'Complete business address including street, city, postal code, and country',
                  icannRequirement: 'Must be a valid business address, not a P.O. Box',
                  validation: { required: true }
                })}
                className="mb-2"
              />
              <EditableField
                label="Website"
                value={applicantData.website}
                status={getFieldStatus(applicantData.website)}
                onEdit={() => onFieldEdit({
                  name: 'website',
                  label: 'Website',
                  currentValue: applicantData.website,
                  type: 'text',
                  description: 'Your organization\'s primary website URL',
                  validation: { required: false, pattern: '^https?://.+' }
                })}
              />
            </div>
          </CardContent>
        )}
      </Card>

      {/* Key Personnel Section */}
      <Card className="mb-6">
        <CardHeader 
          className="cursor-pointer hover:bg-gray-50 transition-colors"
          onClick={() => toggleSection('personnel')}
        >
          <CardTitle className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <User className="w-5 h-5" />
              <span>2. Key Personnel</span>
              <Badge variant="outline">{applicantData.key_personnel?.length || 0} people</Badge>
              <Badge variant="outline" className="text-yellow-600">12 fields missing</Badge>
            </div>
            {expandedSections.has('personnel') ? 
              <ChevronUp className="w-5 h-5" /> : 
              <ChevronDown className="w-5 h-5" />
            }
          </CardTitle>
        </CardHeader>
        
        {expandedSections.has('personnel') && (
          <CardContent className="space-y-6">
            <div className="space-y-4">
              <h4 className="font-semibold text-gray-900">Primary Contact</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pl-4 border-l-2 border-green-200">
                <EditableField
                  label="Name"
                  value="Jordan Rivera"
                  status="verified"
                  onEdit={() => {}}
                />
                <EditableField
                  label="Email"
                  value={applicantData.email}
                  status={getFieldStatus(applicantData.email)}
                  onEdit={() => onFieldEdit({
                    name: 'email',
                    label: 'Primary Contact Email',
                    currentValue: applicantData.email,
                    type: 'email',
                    description: 'Primary administrative contact email address',
                    icannRequirement: 'Must be a valid, monitored email address',
                    validation: { required: true }
                  })}
                />
                <EditableField
                  label="Phone"
                  value={applicantData.phone}
                  status={getFieldStatus(applicantData.phone)}
                  onEdit={() => onFieldEdit({
                    name: 'phone',
                    label: 'Primary Contact Phone',
                    currentValue: applicantData.phone,
                    type: 'phone',
                    description: 'Primary administrative contact phone number with country code',
                    validation: { required: true }
                  })}
                />
                <EditableField
                  label="Permanent Address"
                  value={null}
                  status="missing"
                  onEdit={() => onFieldEdit({
                    name: 'primary_contact_address',
                    label: 'Primary Contact Permanent Address',
                    currentValue: null,
                    type: 'textarea',
                    description: 'Permanent residential address of the primary administrative contact',
                    icannRequirement: 'Required for ICANN verification purposes',
                    validation: { required: true }
                  })}
                />
              </div>
            </div>

            <div className="space-y-4">
              <h4 className="font-semibold text-gray-900">Directors</h4>
              {applicantData.key_personnel?.filter(p => p.title?.includes('Director')).map((person, index) => (
                <div key={index} className="pl-4 border-l-2 border-blue-200 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{person.name} - {person.title}</span>
                    <StatusIcon status="partial" />
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm">
                    <EditableField
                      label="Birth Date"
                      value={null}
                      status="missing"
                      onEdit={() => onFieldEdit({
                        name: `director_${index}_birth_date`,
                        label: `${person.name} Birth Date`,
                        currentValue: null,
                        type: 'date',
                        description: `Birth date for director ${person.name}`,
                        icannRequirement: 'Required for background screening',
                        validation: { required: true }
                      })}
                    />
                    <EditableField
                      label="Birth Country"
                      value={null}
                      status="missing"
                      onEdit={() => onFieldEdit({
                        name: `director_${index}_birth_country`,
                        label: `${person.name} Birth Country`,
                        currentValue: null,
                        type: 'text',
                        description: `Country of birth for director ${person.name}`,
                        icannRequirement: 'Required for background screening',
                        validation: { required: true }
                      })}
                    />
                  </div>
                </div>
              )) || (
                <p className="text-gray-500 italic">No directors found in personnel data</p>
              )}
            </div>
          </CardContent>
        )}
      </Card>

      {/* Required Documents Section */}
      <Card className="mb-6">
        <CardHeader 
          className="cursor-pointer hover:bg-gray-50 transition-colors"
          onClick={() => toggleSection('documents')}
        >
          <CardTitle className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <FileCheck className="w-5 h-5" />
              <span>3. Required Documents</span>
              <Badge variant="outline">0 of {documentTypes.length} uploaded</Badge>
            </div>
            {expandedSections.has('documents') ? 
              <ChevronUp className="w-5 h-5" /> : 
              <ChevronDown className="w-5 h-5" />
            }
          </CardTitle>
        </CardHeader>
        
        {expandedSections.has('documents') && (
          <CardContent className="space-y-6">
            <div className="space-y-4">
              {documentTypes.map((docType, index) => (
                <div key={index} className="flex items-center justify-between p-4 border border-red-200 rounded-lg bg-red-50">
                  <div>
                    <h4 className="font-medium text-gray-900">{docType.title}</h4>
                    <p className="text-sm text-gray-600">{docType.description}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <XCircle className="w-5 h-5 text-red-500" />
                    <Button 
                      size="sm" 
                      variant="outline"
                      onClick={() => onDocumentUpload(docType)}
                    >
                      <Upload className="w-4 h-4 mr-2" />
                      Upload Document
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        )}
      </Card>
    </div>
  );
};

export default function ApplicantInformation() {
  const [viewMode, setViewMode] = useState<'queue' | 'document' | 'hybrid'>('hybrid');
  const [applicantData, setApplicantData] = useState<ApplicantData | null>(null);
  const [missingFields, setMissingFields] = useState<MissingField[]>([]);
  const [currentQueueIndex, setCurrentQueueIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [currentEditField, setCurrentEditField] = useState<any>(null);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [currentDocType, setCurrentDocType] = useState<DocumentType | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    // Fetch applicant data and missing fields from TLD Application Store
    const fetchApplicantData = async () => {
      try {
        const response = await fetch('/api/tld-applications/applicant');
        if (response.ok) {
          const result = await response.json();
          if (result.success) {
            setApplicantData(result.data);
            
            // Get missing fields from the API response, or use defaults if not provided
            const missingFieldsFromApi = result.data?.missing_fields || [];
            
            // If no missing fields from API, calculate based on incomplete data
            if (missingFieldsFromApi.length === 0) {
              const calculatedMissingFields = calculateMissingFields(result.data);
              setMissingFields(calculatedMissingFields);
            } else {
              setMissingFields(missingFieldsFromApi);
            }
          } else {
            console.error('API returned unsuccessful response:', result);
            setMissingFields([]);
          }
        } else {
          console.error('Failed to fetch applicant data:', response.status);
          setMissingFields([]);
        }
      } catch (error) {
        console.error('Error fetching applicant data:', error);
        setMissingFields([]);
      } finally {
        setLoading(false);
      }
    };

    fetchApplicantData();
  }, []);

  // Helper function to calculate missing fields based on incomplete data
  const calculateMissingFields = (applicantData: ApplicantData): MissingField[] => {
    const missingFields: MissingField[] = [];
    
    // Check for common required fields that might be missing
    if (!applicantData.lei) {
      missingFields.push({
        field: 'lei',
        label: 'Legal Entity Identifier',
        description: 'Enter the 20-character alphanumeric Legal Entity Identifier if available',
        required: false,
        section: 'organization',
        type: 'text'
      });
    }
    
    if (!applicantData.primary_contact_address) {
      missingFields.push({
        field: 'primary_contact_address',
        label: 'Primary Contact Permanent Address',
        description: 'Permanent residential address of the primary administrative contact',
        required: true,
        section: 'personnel',
        type: 'textarea'
      });
    }
    
    // Check key personnel for missing birth dates or other required fields
    if (applicantData.key_personnel && Array.isArray(applicantData.key_personnel)) {
      applicantData.key_personnel.forEach((person: any, index: number) => {
        if (!person.birth_date) {
          missingFields.push({
            field: `personnel_${index}_birth_date`,
            label: `${person.name || 'Personnel'} Birth Date`,
            description: `Birth date of ${person.role || 'key personnel'} (${person.name || 'Unknown'})`,
            required: true,
            section: 'personnel',
            type: 'date'
          });
        }
        
        if (!person.permanent_address) {
          missingFields.push({
            field: `personnel_${index}_address`,
            label: `${person.name || 'Personnel'} Permanent Address`,
            description: `Permanent residential address of ${person.role || 'key personnel'} (${person.name || 'Unknown'})`,
            required: true,
            section: 'personnel',
            type: 'textarea'
          });
        }
      });
    }
    
    return missingFields;
  };

  const handleQueueNext = (data: any) => {
    console.log('Updating field:', data);
    setCurrentQueueIndex(prev => Math.min(prev + 1, missingFields.length));
  };

  const handleQueueSkip = () => {
    setCurrentQueueIndex(prev => Math.min(prev + 1, missingFields.length));
  };

  const handleViewInDocument = () => {
    setViewMode('document');
  };

  const handleFieldEdit = (field: any) => {
    setCurrentEditField(field);
    setEditModalOpen(true);
  };

  const handleFieldSave = async (value: string) => {
    console.log('Saving field:', currentEditField.name, 'with value:', value);
    // Here you would call the API to update the field
    setEditModalOpen(false);
    setCurrentEditField(null);
  };

  const handleDocumentUpload = (docType: DocumentType) => {
    setCurrentDocType(docType);
    setUploadModalOpen(true);
  };

  const handleDocumentSave = async (file: File) => {
    console.log('Uploading document:', file.name, 'for type:', currentDocType?.name);
    // Here you would call the API to upload and save the document
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg text-gray-600">Loading applicant information...</div>
      </div>
    );
  }

  if (!applicantData) {
    return (
      <div className="text-center py-12">
        <h2 className="text-xl font-semibold text-gray-900 mb-2">No Applicant Data Found</h2>
        <p className="text-gray-600">Please ensure Example Registry data has been properly loaded.</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate('/')}
              className="flex items-center gap-2"
            >
              <ArrowLeft className="w-4 h-4" />
              Back to Dashboard
            </Button>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Applicant Information</h1>
              <p className="text-gray-600">Review and complete Example Registry's applicant profile</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex bg-gray-100 rounded-lg p-1">
              <Button
                variant={viewMode === 'queue' ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setViewMode('queue')}
              >
                Completion Queue
              </Button>
              <Button
                variant={viewMode === 'document' ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setViewMode('document')}
              >
                Document View
              </Button>
              <Button
                variant={viewMode === 'hybrid' ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setViewMode('hybrid')}
              >
                Hybrid
              </Button>
            </div>
            <Badge variant="secondary">
              Missing Data: {missingFields.length - currentQueueIndex}
            </Badge>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="p-6">
        {viewMode === 'queue' && (
          <div className="max-w-2xl mx-auto">
            <MissingDataQueue
              missingFields={missingFields}
              currentIndex={currentQueueIndex}
              onNext={handleQueueNext}
              onSkip={handleQueueSkip}
              onViewInDocument={handleViewInDocument}
            />
          </div>
        )}

        {viewMode === 'document' && (
          <DocumentSection 
            applicantData={applicantData} 
            onFieldEdit={handleFieldEdit}
            onDocumentUpload={handleDocumentUpload}
          />
        )}

        {viewMode === 'hybrid' && (
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            <div className="lg:col-span-1">
              <MissingDataQueue
                missingFields={missingFields}
                currentIndex={currentQueueIndex}
                onNext={handleQueueNext}
                onSkip={handleQueueSkip}
                onViewInDocument={handleViewInDocument}
              />
            </div>
            <div className="lg:col-span-3">
              <DocumentSection 
                applicantData={applicantData} 
                onFieldEdit={handleFieldEdit}
                onDocumentUpload={handleDocumentUpload}
              />
            </div>
          </div>
        )}
      </div>

      {/* Modals */}
      {editModalOpen && currentEditField && (
        <EditFieldModal
          isOpen={editModalOpen}
          onClose={() => setEditModalOpen(false)}
          field={currentEditField}
          onSave={handleFieldSave}
        />
      )}

      {uploadModalOpen && currentDocType && (
        <DocumentUploadModal
          isOpen={uploadModalOpen}
          onClose={() => setUploadModalOpen(false)}
          documentType={currentDocType}
          onUpload={handleDocumentSave}
        />
      )}
    </div>
  );
}
