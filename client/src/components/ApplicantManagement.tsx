import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import Navigation from './Navigation';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Textarea } from './ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Checkbox } from './ui/checkbox';
import { Badge } from './ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import {
  User,
  Building,
  Building2,
  Phone,
  Mail,
  Globe,
  MapPin,
  DollarSign,
  Users,
  Save,
  Plus,
  Trash2,
  Edit,
  Loader2,
  AlertCircle,
  CheckCircle,
  Scale,
  Shield
} from 'lucide-react';

import { 
  getAllApplicants, 
  getApplicantById,
  updateApplicant,
  createApplicant,
  type ApplicantData,
  type KeyPersonnel 
} from '../lib/supabase-api';

interface ToastProps {
  message: string;
  type: 'success' | 'error' | 'info';
  onClose: () => void;
}

function Toast({ message, type, onClose }: ToastProps) {
  const bgColor = {
    success: 'bg-green-100 border-green-400 text-green-700',
    error: 'bg-red-100 border-red-400 text-red-700',
    info: 'bg-blue-100 border-blue-400 text-blue-700'
  }[type];

  const icon = {
    success: <CheckCircle className="w-4 h-4" />,
    error: <AlertCircle className="w-4 h-4" />,
    info: <AlertCircle className="w-4 h-4" />
  }[type];

  return (
    <div className={`fixed top-4 right-4 z-50 border px-4 py-3 rounded-md shadow-lg ${bgColor}`}>
      <div className="flex items-center space-x-2">
        {icon}
        <span className="text-sm font-medium">{message}</span>
        <button onClick={onClose} className="ml-2 text-lg leading-none hover:opacity-70">
          ×
        </button>
      </div>
    </div>
  );
}

export default function ApplicantManagement() {
  const [applicants, setApplicants] = useState<ApplicantData[]>([]);
  const [selectedApplicant, setSelectedApplicant] = useState<ApplicantData | null>(null);
  const [editedApplicant, setEditedApplicant] = useState<ApplicantData | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  const showToast = (message: string, type: 'success' | 'error' | 'info') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 5000);
  };

  // Load all applicants on component mount
  useEffect(() => {
    loadApplicants();
  }, []);

  const loadApplicants = async () => {
    try {
      setLoading(true);
      const applicantList = await getAllApplicants();
      setApplicants(applicantList);
      
      // Auto-select first applicant if available
      if (applicantList.length > 0 && !selectedApplicant) {
        setSelectedApplicant(applicantList[0]);
        setEditedApplicant(applicantList[0]);
      }
    } catch (error) {
      console.error('Error loading applicants:', error);
      showToast('Failed to load applicants', 'error');
    } finally {
      setLoading(false);
    }
  };

  const selectApplicant = async (applicant: ApplicantData) => {
    try {
      if (applicant.id) {
        // Fetch full details for selected applicant
        const fullApplicant = await getApplicantById(applicant.id);
        setSelectedApplicant(fullApplicant);
        setEditedApplicant(fullApplicant);
        setIsCreating(false);
      }
    } catch (error) {
      console.error('Error loading applicant details:', error);
      showToast('Failed to load applicant details', 'error');
    }
  };

  const startCreatingNew = () => {
    const newApplicant: ApplicantData = {
      legal_name: '',
      business_name: '',
      dba_name: '',
      entity_type: 'Limited Liability Company',
      jurisdiction: '',
      business_address: '',
      email: '',
      tax_id: '',
      tax_id_issuing_authority: '',
      lei: '',
      stock_symbol: '',
      stock_exchange: '',
      address_line1: '',
      address_line2: '',
      city: '',
      state_province: '',
      postal_code: '',
      country_code: '',
      is_existing_registry_operator: false,
      registry_relationship_explanation: '',
      is_rsp_or_provider: false,
      rsp_affiliate_explanation: '',
      parent_company_name: '',
      parent_company_dba: '',
      parent_company_entity_type: '',
      parent_company_jurisdiction: '',
      parent_company_address: {},
      ultimate_parent_name: '',
      ultimate_parent_dba: '',
      ultimate_parent_entity_type: '',
      ultimate_parent_jurisdiction: '',
      ultimate_parent_address: {},
      has_unique_legal_issues: false,
      legal_issues_explanation: '',
      key_personnel: []
    };
    setSelectedApplicant(newApplicant);
    setEditedApplicant(newApplicant);
    setIsCreating(true);
  };

  const saveApplicant = async () => {
    if (!editedApplicant) return;

    try {
      setSaving(true);
      
      if (isCreating) {
        // Create new applicant
        const newId = await createApplicant(editedApplicant);
        showToast('Applicant created successfully!', 'success');
        
        // Reload applicants list and select the new one
        await loadApplicants();
        const newApplicant = await getApplicantById(newId);
        setSelectedApplicant(newApplicant);
        setEditedApplicant(newApplicant);
        setIsCreating(false);
      } else if (selectedApplicant?.id) {
        // Update existing applicant
        const updated = await updateApplicant(selectedApplicant.id, editedApplicant);
        setSelectedApplicant(updated);
        setEditedApplicant(updated);
        showToast('Applicant updated successfully!', 'success');
        
        // Update in the list
        setApplicants(prev => 
          prev.map(a => a.id === updated.id ? updated : a)
        );
      }
    } catch (error) {
      console.error('Error saving applicant:', error);
      showToast(error instanceof Error ? error.message : 'Failed to save applicant', 'error');
    } finally {
      setSaving(false);
    }
  };

  const cancelEdit = () => {
    if (isCreating) {
      // If creating, go back to first applicant or empty state
      if (applicants.length > 0) {
        setSelectedApplicant(applicants[0]);
        setEditedApplicant(applicants[0]);
      } else {
        setSelectedApplicant(null);
        setEditedApplicant(null);
      }
      setIsCreating(false);
    } else {
      // If editing, revert changes
      setEditedApplicant(selectedApplicant);
    }
  };

  const updateField = (field: keyof ApplicantData, value: any) => {
    if (!editedApplicant) return;
    setEditedApplicant({
      ...editedApplicant,
      [field]: value
    });
  };

  const addPersonnel = () => {
    if (!editedApplicant) return;
    const newPerson: KeyPersonnel = {
      name: '',
      title: '',
      role: '',
      contact_type: 'staff'
    };
    setEditedApplicant({
      ...editedApplicant,
      key_personnel: [...(editedApplicant.key_personnel || []), newPerson]
    });
  };

  const updatePersonnel = (index: number, field: keyof KeyPersonnel, value: string) => {
    if (!editedApplicant || !editedApplicant.key_personnel) return;
    const updated = [...editedApplicant.key_personnel];
    updated[index] = { ...updated[index], [field]: value };
    setEditedApplicant({
      ...editedApplicant,
      key_personnel: updated
    });
  };

  const removePersonnel = (index: number) => {
    if (!editedApplicant || !editedApplicant.key_personnel) return;
    const updated = editedApplicant.key_personnel.filter((_, i) => i !== index);
    setEditedApplicant({
      ...editedApplicant,
      key_personnel: updated
    });
  };

  const hasUnsavedChanges = () => {
    return JSON.stringify(selectedApplicant) !== JSON.stringify(editedApplicant);
  };

  const updateParentAddress = (subfield: string, value: string) => {
    if (!editedApplicant) return;
    const current = editedApplicant.parent_company_address || {};
    setEditedApplicant({
      ...editedApplicant,
      parent_company_address: { ...current, [subfield]: value }
    });
  };

  const updateUltimateParentAddress = (subfield: string, value: string) => {
    if (!editedApplicant) return;
    const current = editedApplicant.ultimate_parent_address || {};
    setEditedApplicant({
      ...editedApplicant,
      ultimate_parent_address: { ...current, [subfield]: value }
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="flex items-center space-x-2">
          <Loader2 className="w-6 h-6 animate-spin" />
          <span>Loading applicants...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <Navigation />
      {/* Header */}
      <div className="border-b bg-white">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold">Applicant Management</h1>
              <p className="text-muted-foreground">Manage organization information for gTLD applications</p>
            </div>
            <div className="flex items-center space-x-2">
              <Badge variant="outline">{applicants.length} applicant{applicants.length !== 1 ? 's' : ''}</Badge>
              {hasUnsavedChanges() && (
                <Badge variant="destructive">Unsaved Changes</Badge>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="container mx-auto px-4 py-6">
        <div className="grid grid-cols-12 gap-6">
          {/* Applicant Selector Sidebar */}
          <div className="col-span-12 lg:col-span-3">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <span>Select Applicant</span>
                  <Button size="sm" onClick={startCreatingNew}>
                    <Plus className="w-4 h-4 mr-1" />
                    New
                  </Button>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {applicants.length === 0 && !isCreating ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <Building className="w-12 h-12 mx-auto mb-2 opacity-50" />
                    <p>No applicants found</p>
                    <Button size="sm" className="mt-2" onClick={startCreatingNew}>
                      Create First Applicant
                    </Button>
                  </div>
                ) : (
                  <>
                    {isCreating && (
                      <div className="p-3 border-2 border-blue-300 rounded-lg bg-blue-50">
                        <div className="flex items-center space-x-2">
                          <Edit className="w-4 h-4 text-blue-600" />
                          <span className="font-medium text-blue-800">Creating New Applicant</span>
                        </div>
                      </div>
                    )}
                    {applicants.map((applicant) => (
                      <div
                        key={applicant.id}
                        className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                          selectedApplicant?.id === applicant.id && !isCreating
                            ? 'border-blue-300 bg-blue-50'
                            : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                        }`}
                        onClick={() => selectApplicant(applicant)}
                      >
                        <div className="font-medium text-sm">{applicant.legal_name}</div>
                        <div className="text-xs text-muted-foreground">
                          {applicant.business_name || applicant.entity_type}
                        </div>
                      </div>
                    ))}
                  </>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Main Editing Area */}
          <div className="col-span-12 lg:col-span-9">
            {!selectedApplicant && !isCreating ? (
              <Card>
                <CardContent className="py-12 text-center">
                  <User className="w-16 h-16 mx-auto mb-4 opacity-50" />
                  <h3 className="text-lg font-semibold mb-2">No Applicant Selected</h3>
                  <p className="text-muted-foreground mb-4">
                    Select an applicant from the sidebar or create a new one to get started.
                  </p>
                  <Button onClick={startCreatingNew}>
                    <Plus className="w-4 h-4 mr-2" />
                    Create New Applicant
                  </Button>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-6">
                {/* Action Buttons */}
                <div className="flex justify-between items-center">
                  <h2 className="text-xl font-semibold">
                    {isCreating ? 'Create New Applicant' : `Edit ${selectedApplicant?.legal_name || 'Applicant'}`}
                  </h2>
                  <div className="flex space-x-2">
                    <Button
                      variant="outline"
                      onClick={cancelEdit}
                      disabled={saving}
                    >
                      Cancel
                    </Button>
                    <Button
                      onClick={saveApplicant}
                      disabled={saving || !editedApplicant?.legal_name || !editedApplicant?.email}
                    >
                      {saving && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                      <Save className="w-4 h-4 mr-2" />
                      {isCreating ? 'Create' : 'Save Changes'}
                    </Button>
                  </div>
                </div>

                <Tabs defaultValue="organization" className="w-full">
                  <TabsList className="flex-wrap h-auto">
                    <TabsTrigger value="organization">Organization</TabsTrigger>
                    <TabsTrigger value="contact">Contact Info</TabsTrigger>
                    <TabsTrigger value="personnel">Key Personnel</TabsTrigger>
                    <TabsTrigger value="business">Business Details</TabsTrigger>
                    <TabsTrigger value="parents">Parent Companies</TabsTrigger>
                    <TabsTrigger value="legal">Legal & Ownership</TabsTrigger>
                  </TabsList>

                  <TabsContent value="organization" className="space-y-4">
                    <Card>
                      <CardHeader>
                        <CardTitle className="flex items-center space-x-2">
                          <Building className="w-5 h-5" />
                          <span>Organization Information</span>
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div>
                            <label className="text-sm font-medium">Legal Entity Name *</label>
                            <Input
                              value={editedApplicant?.legal_name || ''}
                              onChange={(e) => updateField('legal_name', e.target.value)}
                              placeholder="Enter legal entity name"
                            />
                          </div>
                          <div>
                            <label className="text-sm font-medium">Business Name</label>
                            <Input
                              value={editedApplicant?.business_name || ''}
                              onChange={(e) => updateField('business_name', e.target.value)}
                              placeholder="Enter business/trading name"
                            />
                          </div>
                          <div>
                            <label className="text-sm font-medium">DBA Name</label>
                            <Input
                              value={editedApplicant?.dba_name || ''}
                              onChange={(e) => updateField('dba_name', e.target.value)}
                              placeholder="Doing Business As name"
                            />
                          </div>
                          <div>
                            <label className="text-sm font-medium">Entity Type</label>
                            <Select
                              value={editedApplicant?.entity_type || 'Limited Liability Company'}
                              onValueChange={(value) => updateField('entity_type', value)}
                            >
                              <SelectTrigger>
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="Limited Liability Company">Limited Liability Company</SelectItem>
                                <SelectItem value="Corporation">Corporation</SelectItem>
                                <SelectItem value="Private Limited Company">Private Limited Company</SelectItem>
                                <SelectItem value="Public Limited Company">Public Limited Company</SelectItem>
                                <SelectItem value="Partnership">Partnership</SelectItem>
                                <SelectItem value="Sole Proprietorship">Sole Proprietorship</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                          <div>
                            <label className="text-sm font-medium">Jurisdiction</label>
                            <Input
                              value={editedApplicant?.jurisdiction || ''}
                              onChange={(e) => updateField('jurisdiction', e.target.value)}
                              placeholder="e.g., Delaware, United States"
                            />
                          </div>
                          <div>
                            <label className="text-sm font-medium">Incorporation Date</label>
                            <Input
                              type="date"
                              value={editedApplicant?.incorporation_date || ''}
                              onChange={(e) => updateField('incorporation_date', e.target.value)}
                            />
                          </div>
                        </div>

                        <hr className="my-4" />
                        <h4 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">Tax & Identifiers</h4>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div>
                            <label className="text-sm font-medium">Tax ID</label>
                            <Input
                              value={editedApplicant?.tax_id || ''}
                              onChange={(e) => updateField('tax_id', e.target.value)}
                              placeholder="Tax ID / Business ID / VAT Registration"
                            />
                          </div>
                          <div>
                            <label className="text-sm font-medium">Tax ID Issuing Authority</label>
                            <Input
                              value={editedApplicant?.tax_id_issuing_authority || ''}
                              onChange={(e) => updateField('tax_id_issuing_authority', e.target.value)}
                              placeholder="e.g., IRS, HMRC"
                            />
                          </div>
                          <div>
                            <label className="text-sm font-medium">LEI</label>
                            <Input
                              value={editedApplicant?.lei || ''}
                              onChange={(e) => updateField('lei', e.target.value)}
                              placeholder="Legal Entity Identifier (20 chars)"
                              maxLength={20}
                            />
                            <p className="text-xs text-muted-foreground mt-1">20-character Legal Entity Identifier</p>
                          </div>
                        </div>

                        <hr className="my-4" />
                        <h4 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">Stock Information</h4>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div>
                            <label className="text-sm font-medium">Stock Symbol</label>
                            <Input
                              value={editedApplicant?.stock_symbol || ''}
                              onChange={(e) => updateField('stock_symbol', e.target.value)}
                              placeholder="If publicly traded"
                            />
                          </div>
                          <div>
                            <label className="text-sm font-medium">Stock Exchange</label>
                            <Select
                              value={editedApplicant?.stock_exchange || ''}
                              onValueChange={(value) => updateField('stock_exchange', value)}
                            >
                              <SelectTrigger>
                                <SelectValue placeholder="Select exchange" />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="NYSE">NYSE</SelectItem>
                                <SelectItem value="NASDAQ">NASDAQ</SelectItem>
                                <SelectItem value="LSE">LSE</SelectItem>
                                <SelectItem value="TSE">TSE</SelectItem>
                                <SelectItem value="HKEX">HKEX</SelectItem>
                                <SelectItem value="Euronext">Euronext</SelectItem>
                                <SelectItem value="SSE">SSE</SelectItem>
                                <SelectItem value="Other">Other</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </TabsContent>

                  <TabsContent value="contact" className="space-y-4">
                    <Card>
                      <CardHeader>
                        <CardTitle className="flex items-center space-x-2">
                          <MapPin className="w-5 h-5" />
                          <span>Contact Information</span>
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                          <div>
                            <label className="text-sm font-medium flex items-center space-x-1">
                              <Mail className="w-4 h-4" />
                              <span>Email *</span>
                            </label>
                            <Input
                              type="email"
                              value={editedApplicant?.email || ''}
                              onChange={(e) => updateField('email', e.target.value)}
                              placeholder="contact@company.com"
                            />
                          </div>
                          <div>
                            <label className="text-sm font-medium flex items-center space-x-1">
                              <Phone className="w-4 h-4" />
                              <span>Phone</span>
                            </label>
                            <Input
                              type="tel"
                              value={editedApplicant?.phone || ''}
                              onChange={(e) => updateField('phone', e.target.value)}
                              placeholder="+1-555-123-4567"
                            />
                          </div>
                          <div>
                            <label className="text-sm font-medium flex items-center space-x-1">
                              <Globe className="w-4 h-4" />
                              <span>Website</span>
                            </label>
                            <Input
                              type="url"
                              value={editedApplicant?.website || ''}
                              onChange={(e) => updateField('website', e.target.value)}
                              placeholder="https://company.com"
                            />
                          </div>
                        </div>

                        <hr className="my-4" />
                        <h4 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">Business Address</h4>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div className="md:col-span-2">
                            <label className="text-sm font-medium">Address Line 1</label>
                            <Input
                              value={editedApplicant?.address_line1 || ''}
                              onChange={(e) => updateField('address_line1', e.target.value)}
                              placeholder="Street address"
                            />
                          </div>
                          <div className="md:col-span-2">
                            <label className="text-sm font-medium">Address Line 2</label>
                            <Input
                              value={editedApplicant?.address_line2 || ''}
                              onChange={(e) => updateField('address_line2', e.target.value)}
                              placeholder="Suite, floor, unit"
                            />
                          </div>
                          <div>
                            <label className="text-sm font-medium">City</label>
                            <Input
                              value={editedApplicant?.city || ''}
                              onChange={(e) => updateField('city', e.target.value)}
                              placeholder="City"
                            />
                          </div>
                          <div>
                            <label className="text-sm font-medium">State / Province</label>
                            <Input
                              value={editedApplicant?.state_province || ''}
                              onChange={(e) => updateField('state_province', e.target.value)}
                              placeholder="State or province"
                            />
                          </div>
                          <div>
                            <label className="text-sm font-medium">Postal Code</label>
                            <Input
                              value={editedApplicant?.postal_code || ''}
                              onChange={(e) => updateField('postal_code', e.target.value)}
                              placeholder="Postal / ZIP code"
                            />
                          </div>
                          <div>
                            <label className="text-sm font-medium">Country Code</label>
                            <Input
                              value={editedApplicant?.country_code || ''}
                              onChange={(e) => updateField('country_code', e.target.value)}
                              placeholder="ISO 2-letter code (e.g., US, GB)"
                              maxLength={2}
                            />
                          </div>
                        </div>

                        <hr className="my-4" />
                        <h4 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">Mailing Address</h4>
                        <div>
                          <Textarea
                            value={editedApplicant?.mailing_address || ''}
                            onChange={(e) => updateField('mailing_address', e.target.value)}
                            placeholder="Enter mailing address if different from business address"
                            rows={3}
                          />
                        </div>
                      </CardContent>
                    </Card>
                  </TabsContent>

                  <TabsContent value="personnel" className="space-y-4">
                    <Card>
                      <CardHeader>
                        <CardTitle className="flex items-center justify-between">
                          <div className="flex items-center space-x-2">
                            <Users className="w-5 h-5" />
                            <span>Key Personnel</span>
                          </div>
                          <Button size="sm" onClick={addPersonnel}>
                            <Plus className="w-4 h-4 mr-1" />
                            Add Person
                          </Button>
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        {(!editedApplicant?.key_personnel || editedApplicant.key_personnel.length === 0) ? (
                          <div className="text-center py-8 text-muted-foreground">
                            <Users className="w-12 h-12 mx-auto mb-2 opacity-50" />
                            <p>No key personnel added yet</p>
                            <Button size="sm" className="mt-2" onClick={addPersonnel}>
                              Add First Person
                            </Button>
                          </div>
                        ) : (
                          <div className="space-y-4">
                            {editedApplicant.key_personnel.map((person, index) => (
                              <div key={index} className="p-4 border rounded-lg">
                                <div className="flex justify-between items-start mb-3">
                                  <h4 className="font-medium">Person #{index + 1}</h4>
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    onClick={() => removePersonnel(index)}
                                  >
                                    <Trash2 className="w-4 h-4" />
                                  </Button>
                                </div>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                  <div>
                                    <label className="text-sm font-medium">Name</label>
                                    <Input
                                      value={person.name}
                                      onChange={(e) => updatePersonnel(index, 'name', e.target.value)}
                                      placeholder="Full name"
                                    />
                                  </div>
                                  <div>
                                    <label className="text-sm font-medium">Title</label>
                                    <Input
                                      value={person.title}
                                      onChange={(e) => updatePersonnel(index, 'title', e.target.value)}
                                      placeholder="Job title"
                                    />
                                  </div>
                                  <div>
                                    <label className="text-sm font-medium">Role</label>
                                    <Input
                                      value={person.role}
                                      onChange={(e) => updatePersonnel(index, 'role', e.target.value)}
                                      placeholder="Role description"
                                    />
                                  </div>
                                  <div>
                                    <label className="text-sm font-medium">Contact Type</label>
                                    <Select
                                      value={person.contact_type}
                                      onValueChange={(value) => updatePersonnel(index, 'contact_type', value)}
                                    >
                                      <SelectTrigger>
                                        <SelectValue />
                                      </SelectTrigger>
                                      <SelectContent>
                                        <SelectItem value="primary_administrative">Primary Administrative</SelectItem>
                                        <SelectItem value="technical">Technical</SelectItem>
                                        <SelectItem value="billing">Billing</SelectItem>
                                        <SelectItem value="legal">Legal</SelectItem>
                                        <SelectItem value="staff">Staff</SelectItem>
                                      </SelectContent>
                                    </Select>
                                  </div>
                                  <div>
                                    <label className="text-sm font-medium">Email</label>
                                    <Input
                                      type="email"
                                      value={person.email || ''}
                                      onChange={(e) => updatePersonnel(index, 'email', e.target.value)}
                                      placeholder="person@company.com"
                                    />
                                  </div>
                                  <div>
                                    <label className="text-sm font-medium">Phone</label>
                                    <Input
                                      type="tel"
                                      value={person.phone || ''}
                                      onChange={(e) => updatePersonnel(index, 'phone', e.target.value)}
                                      placeholder="+1-555-123-4567"
                                    />
                                  </div>
                                </div>
                                <div className="mt-3">
                                  <label className="text-sm font-medium">Background</label>
                                  <Textarea
                                    value={person.background || ''}
                                    onChange={(e) => updatePersonnel(index, 'background', e.target.value)}
                                    placeholder="Professional background and experience"
                                    rows={2}
                                  />
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  </TabsContent>

                  <TabsContent value="business" className="space-y-4">
                    <Card>
                      <CardHeader>
                        <CardTitle className="flex items-center space-x-2">
                          <Shield className="w-5 h-5" />
                          <span>Registry Relationships</span>
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div className="space-y-4">
                          <div className="flex items-center space-x-3">
                            <Checkbox
                              id="is_existing_registry_operator"
                              checked={editedApplicant?.is_existing_registry_operator || false}
                              onCheckedChange={(checked) => updateField('is_existing_registry_operator', !!checked)}
                            />
                            <label htmlFor="is_existing_registry_operator" className="text-sm font-medium cursor-pointer">
                              Currently operating a gTLD registry?
                            </label>
                          </div>
                          {editedApplicant?.is_existing_registry_operator && (
                            <div className="ml-7">
                              <label className="text-sm font-medium">Registry Relationship Explanation</label>
                              <Textarea
                                value={editedApplicant?.registry_relationship_explanation || ''}
                                onChange={(e) => updateField('registry_relationship_explanation', e.target.value)}
                                placeholder="Describe current registry operations and relationships"
                                rows={3}
                              />
                            </div>
                          )}
                        </div>
                        <div className="space-y-4">
                          <div className="flex items-center space-x-3">
                            <Checkbox
                              id="is_rsp_or_provider"
                              checked={editedApplicant?.is_rsp_or_provider || false}
                              onCheckedChange={(checked) => updateField('is_rsp_or_provider', !!checked)}
                            />
                            <label htmlFor="is_rsp_or_provider" className="text-sm font-medium cursor-pointer">
                              Back-end registry service provider or data escrow agent?
                            </label>
                          </div>
                          {editedApplicant?.is_rsp_or_provider && (
                            <div className="ml-7">
                              <label className="text-sm font-medium">RSP / Affiliate Explanation</label>
                              <Textarea
                                value={editedApplicant?.rsp_affiliate_explanation || ''}
                                onChange={(e) => updateField('rsp_affiliate_explanation', e.target.value)}
                                placeholder="Describe RSP or data escrow agent relationships"
                                rows={3}
                              />
                            </div>
                          )}
                        </div>
                      </CardContent>
                    </Card>

                    <Card>
                      <CardHeader>
                        <CardTitle className="flex items-center space-x-2">
                          <DollarSign className="w-5 h-5" />
                          <span>Financial Details</span>
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div>
                            <label className="text-sm font-medium">Annual Revenue</label>
                            <Input
                              type="number"
                              min="0"
                              step="1000"
                              value={editedApplicant?.annual_revenue || ''}
                              onChange={(e) => updateField('annual_revenue', e.target.value ? Number(e.target.value) : null)}
                              placeholder="1000000"
                            />
                          </div>
                          <div>
                            <label className="text-sm font-medium">Total Assets</label>
                            <Input
                              type="number"
                              min="0"
                              step="1000"
                              value={editedApplicant?.total_assets || ''}
                              onChange={(e) => updateField('total_assets', e.target.value ? Number(e.target.value) : null)}
                              placeholder="5000000"
                            />
                          </div>
                        </div>
                        <div>
                          <label className="text-sm font-medium">Funding Sources</label>
                          <Textarea
                            value={editedApplicant?.funding_sources || ''}
                            onChange={(e) => updateField('funding_sources', e.target.value)}
                            placeholder="Describe funding sources and capital structure"
                            rows={3}
                          />
                        </div>
                        <div>
                          <label className="text-sm font-medium">Registry Experience</label>
                          <Textarea
                            value={editedApplicant?.registry_experience_description || ''}
                            onChange={(e) => updateField('registry_experience_description', e.target.value)}
                            placeholder="Describe previous registry operations experience"
                            rows={3}
                          />
                        </div>
                        <div>
                          <label className="text-sm font-medium">Current TLDs</label>
                          <Input
                            value={editedApplicant?.current_tlds?.join(', ') || ''}
                            onChange={(e) => updateField('current_tlds', e.target.value.split(',').map(s => s.trim()).filter(Boolean))}
                            placeholder="e.g., .com, .net, .org"
                          />
                          <p className="text-xs text-muted-foreground mt-1">Comma-separated list of currently operated TLDs</p>
                        </div>
                        <div>
                          <label className="text-sm font-medium">Affiliated Organizations</label>
                          <Input
                            value={editedApplicant?.affiliated_organizations?.join(', ') || ''}
                            onChange={(e) => updateField('affiliated_organizations', e.target.value.split(',').map(s => s.trim()).filter(Boolean))}
                            placeholder="e.g., ICANN, Registry Operator Group"
                          />
                          <p className="text-xs text-muted-foreground mt-1">Comma-separated list of affiliated organizations</p>
                        </div>
                      </CardContent>
                    </Card>
                  </TabsContent>
                  <TabsContent value="parents" className="space-y-4">
                    <Card>
                      <CardHeader>
                        <CardTitle className="flex items-center space-x-2">
                          <Building2 className="w-5 h-5" />
                          <span>Direct Parent Company</span>
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div>
                            <label className="text-sm font-medium">Name</label>
                            <Input
                              value={editedApplicant?.parent_company_name || ''}
                              onChange={(e) => updateField('parent_company_name', e.target.value)}
                              placeholder="Parent company legal name"
                            />
                          </div>
                          <div>
                            <label className="text-sm font-medium">DBA</label>
                            <Input
                              value={editedApplicant?.parent_company_dba || ''}
                              onChange={(e) => updateField('parent_company_dba', e.target.value)}
                              placeholder="Doing Business As"
                            />
                          </div>
                          <div>
                            <label className="text-sm font-medium">Entity Type</label>
                            <Input
                              value={editedApplicant?.parent_company_entity_type || ''}
                              onChange={(e) => updateField('parent_company_entity_type', e.target.value)}
                              placeholder="e.g., Corporation, LLC"
                            />
                          </div>
                          <div>
                            <label className="text-sm font-medium">Jurisdiction</label>
                            <Input
                              value={editedApplicant?.parent_company_jurisdiction || ''}
                              onChange={(e) => updateField('parent_company_jurisdiction', e.target.value)}
                              placeholder="e.g., Delaware, United States"
                            />
                          </div>
                        </div>
                        <hr className="my-2" />
                        <h4 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">Parent Company Address</h4>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div className="md:col-span-2">
                            <label className="text-sm font-medium">Address Line 1</label>
                            <Input
                              value={editedApplicant?.parent_company_address?.line1 || ''}
                              onChange={(e) => updateParentAddress('line1', e.target.value)}
                              placeholder="Street address"
                            />
                          </div>
                          <div className="md:col-span-2">
                            <label className="text-sm font-medium">Address Line 2</label>
                            <Input
                              value={editedApplicant?.parent_company_address?.line2 || ''}
                              onChange={(e) => updateParentAddress('line2', e.target.value)}
                              placeholder="Suite, floor, unit"
                            />
                          </div>
                          <div>
                            <label className="text-sm font-medium">City</label>
                            <Input
                              value={editedApplicant?.parent_company_address?.city || ''}
                              onChange={(e) => updateParentAddress('city', e.target.value)}
                              placeholder="City"
                            />
                          </div>
                          <div>
                            <label className="text-sm font-medium">State / Province</label>
                            <Input
                              value={editedApplicant?.parent_company_address?.state_province || ''}
                              onChange={(e) => updateParentAddress('state_province', e.target.value)}
                              placeholder="State or province"
                            />
                          </div>
                          <div>
                            <label className="text-sm font-medium">Postal Code</label>
                            <Input
                              value={editedApplicant?.parent_company_address?.postal_code || ''}
                              onChange={(e) => updateParentAddress('postal_code', e.target.value)}
                              placeholder="Postal / ZIP code"
                            />
                          </div>
                          <div>
                            <label className="text-sm font-medium">Country Code</label>
                            <Input
                              value={editedApplicant?.parent_company_address?.country_code || ''}
                              onChange={(e) => updateParentAddress('country_code', e.target.value)}
                              placeholder="ISO 2-letter code (e.g., US, GB)"
                              maxLength={2}
                            />
                          </div>
                        </div>
                      </CardContent>
                    </Card>

                    <Card>
                      <CardHeader>
                        <CardTitle className="flex items-center space-x-2">
                          <Building2 className="w-5 h-5" />
                          <span>Ultimate Parent Company</span>
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div>
                            <label className="text-sm font-medium">Name</label>
                            <Input
                              value={editedApplicant?.ultimate_parent_name || ''}
                              onChange={(e) => updateField('ultimate_parent_name', e.target.value)}
                              placeholder="Ultimate parent company legal name"
                            />
                          </div>
                          <div>
                            <label className="text-sm font-medium">DBA</label>
                            <Input
                              value={editedApplicant?.ultimate_parent_dba || ''}
                              onChange={(e) => updateField('ultimate_parent_dba', e.target.value)}
                              placeholder="Doing Business As"
                            />
                          </div>
                          <div>
                            <label className="text-sm font-medium">Entity Type</label>
                            <Input
                              value={editedApplicant?.ultimate_parent_entity_type || ''}
                              onChange={(e) => updateField('ultimate_parent_entity_type', e.target.value)}
                              placeholder="e.g., Corporation, LLC"
                            />
                          </div>
                          <div>
                            <label className="text-sm font-medium">Jurisdiction</label>
                            <Input
                              value={editedApplicant?.ultimate_parent_jurisdiction || ''}
                              onChange={(e) => updateField('ultimate_parent_jurisdiction', e.target.value)}
                              placeholder="e.g., Delaware, United States"
                            />
                          </div>
                        </div>
                        <hr className="my-2" />
                        <h4 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">Ultimate Parent Address</h4>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div className="md:col-span-2">
                            <label className="text-sm font-medium">Address Line 1</label>
                            <Input
                              value={editedApplicant?.ultimate_parent_address?.line1 || ''}
                              onChange={(e) => updateUltimateParentAddress('line1', e.target.value)}
                              placeholder="Street address"
                            />
                          </div>
                          <div className="md:col-span-2">
                            <label className="text-sm font-medium">Address Line 2</label>
                            <Input
                              value={editedApplicant?.ultimate_parent_address?.line2 || ''}
                              onChange={(e) => updateUltimateParentAddress('line2', e.target.value)}
                              placeholder="Suite, floor, unit"
                            />
                          </div>
                          <div>
                            <label className="text-sm font-medium">City</label>
                            <Input
                              value={editedApplicant?.ultimate_parent_address?.city || ''}
                              onChange={(e) => updateUltimateParentAddress('city', e.target.value)}
                              placeholder="City"
                            />
                          </div>
                          <div>
                            <label className="text-sm font-medium">State / Province</label>
                            <Input
                              value={editedApplicant?.ultimate_parent_address?.state_province || ''}
                              onChange={(e) => updateUltimateParentAddress('state_province', e.target.value)}
                              placeholder="State or province"
                            />
                          </div>
                          <div>
                            <label className="text-sm font-medium">Postal Code</label>
                            <Input
                              value={editedApplicant?.ultimate_parent_address?.postal_code || ''}
                              onChange={(e) => updateUltimateParentAddress('postal_code', e.target.value)}
                              placeholder="Postal / ZIP code"
                            />
                          </div>
                          <div>
                            <label className="text-sm font-medium">Country Code</label>
                            <Input
                              value={editedApplicant?.ultimate_parent_address?.country_code || ''}
                              onChange={(e) => updateUltimateParentAddress('country_code', e.target.value)}
                              placeholder="ISO 2-letter code (e.g., US, GB)"
                              maxLength={2}
                            />
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </TabsContent>

                  <TabsContent value="legal" className="space-y-4">
                    <Card>
                      <CardHeader>
                        <CardTitle className="flex items-center space-x-2">
                          <Scale className="w-5 h-5" />
                          <span>Legal & Ownership</span>
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div className="space-y-4">
                          <div className="flex items-center space-x-3">
                            <Checkbox
                              id="has_unique_legal_issues"
                              checked={editedApplicant?.has_unique_legal_issues || false}
                              onCheckedChange={(checked) => updateField('has_unique_legal_issues', !!checked)}
                            />
                            <label htmlFor="has_unique_legal_issues" className="text-sm font-medium cursor-pointer">
                              Are there any unique legal issues the applicant needs to disclose?
                            </label>
                          </div>
                          {editedApplicant?.has_unique_legal_issues && (
                            <div className="ml-7">
                              <label className="text-sm font-medium">Legal Issues Explanation</label>
                              <Textarea
                                value={editedApplicant?.legal_issues_explanation || ''}
                                onChange={(e) => updateField('legal_issues_explanation', e.target.value)}
                                placeholder="Describe any unique legal issues, pending litigation, or regulatory matters"
                                rows={4}
                              />
                            </div>
                          )}
                        </div>

                        <hr className="my-4" />
                        <div className="rounded-md border border-amber-200 bg-amber-50 p-4">
                          <p className="text-sm text-amber-800">
                            <strong>Ownership Chart (Q46)</strong> -- An ownership chart showing the relationship between the applicant entity and all parent companies is required as a file upload in the application.
                          </p>
                        </div>
                      </CardContent>
                    </Card>
                  </TabsContent>
                </Tabs>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Toast Notification */}
      {toast && (
        <Toast 
          message={toast.message} 
          type={toast.type} 
          onClose={() => setToast(null)} 
        />
      )}
    </div>
  );
}