# Application Questions Parsing Specification

## Overview
This document defines the consistent data points and patterns found in the ICANN application questions document that can be systematically parsed and structured for database storage and UI generation.

## Identified Consistent Data Points

### 1. Question Structure
Every question follows this consistent format:
```
**Question {number}**
*   **Sub-section:** {section_name}
*   **Question #:** {question_number}
*   **Question:** {question_text}
*   **Public Posting:** {Yes|No}
*   **Notes/Instructions:** {instructions_text}
*   **Criteria:** {criteria_list}
*   **Input Field Requirements:** {requirements_text}
```

### 2. Question Identification
- **Question Number**: Sequential numbering (7, 8, 9, 10, etc.)
- **Sub-section**: Categorical groupings like:
  - "Applicant Entity"
  - "Stock and Exchange"
  - "Primary Business Phone"
  - "Primary Business Email Address"
  - "Primary Business Address"
  - "Direct Parent Company"
  - "Ultimate Parent Company"

### 3. Public Posting Classification
- **Values**: "Yes" or "No"
- **Meaning**: Whether ICANN will make this information publicly available
- **Usage**: Critical for privacy/confidentiality considerations

### 4. Input Field Requirements (Submission Format/Requirements)

#### Character Limits
- **255 character limit** (most common)
- **4000 character limit** (longer text fields)
- **20 alphanumeric characters** (specific format like LEI)

#### Input Types
- **Text fields**: "Enter appropriate information in text field"
- **Dropdown selections**: "Select from a Dropdown Menu", "Choose one of the provided options"
- **Radio buttons**: "Select from Radio Buttons - Yes/No"
- **File uploads**: "Upload no more than X pages, subject to acceptable file types"
- **Email validation**: "Entered text must be valid email address"
- **URL validation**: "Entered text must be valid URL"
- **Phone validation**: "Must be valid phone number format"

#### Validation Rules
- **Physical address required**: "Must be a physical address, no PO Box"
- **Alphanumeric only**: "Must be 20 alphanumeric (a-z, 0-9) characters"
- **Latin characters**: "Use only Latin characters"
- **Format validation**: Email, URL, phone number formats
- **Selection required**: "An option must be selected"

#### File Upload Specifications
- **Page limits**: "Upload no more than 10 pages"
- **File type restrictions**: "subject to acceptable file types"
- **Document requirements**: Specific document types (certificates, articles of incorporation, etc.)

### 5. Criteria Patterns
- **CR-1**: Most common, typically "Enter appropriate information in text field" or "Upload the appropriate documentation"
- **CR-2**: Additional requirements like age restrictions ("no more than 6 months old")
- **Conditional requirements**: Some questions become required based on other answers

### 6. Data Type Classifications (Inferred)

#### Organization Information
- Legal names, business names, entity types
- Jurisdiction and incorporation details
- Website URLs and business descriptions

#### Contact Details
- Addresses (business, mailing, parent company)
- Phone numbers and email addresses
- Geographic information (country codes, regions)

#### Financial Data
- Revenue information, asset details
- Stock exchange information
- Financial statements and certificates

#### Legal Documents
- Articles of incorporation
- Good standing certificates
- Proof of establishment documents

#### Technical Specifications
- Registry services descriptions
- Technical infrastructure details
- Operational capabilities

### 7. Address Patterns
Standard address structure repeated for different entities:
- **Address Line 1**: Street address (no PO boxes)
- **Address Line 2**: Additional address info
- **Locality**: City, village, municipality
- **Region**: State, province, territory
- **Postal Code**: Postal/ZIP code
- **Country Code**: ISO country code selection

### 8. Error Handling Considerations

#### Missing Data Scenarios
- **Optional vs Required**: Some fields are conditional
- **Document Dependencies**: Some questions require documents from previous questions
- **Parent Company Logic**: Ultimate parent questions only required if different from direct parent

#### Validation Failures
- **Format mismatches**: Email, URL, phone number format issues
- **Length violations**: Character/word count exceeded
- **Business rule violations**: PO Box addresses, invalid dates, etc.

## Database Schema Mapping

### Input Type Mapping
```sql
-- Derived from Input Field Requirements parsing
input_type VARCHAR(50) -- Maps to:
'text'        -- Basic text input
'textarea'    -- 4000+ character fields  
'upload'      -- File upload requirements
'dropdown'    -- "Select from dropdown"
'radio'       -- "Select from Radio Buttons"
'email'       -- Email validation required
'url'         -- URL validation required
'phone'       -- Phone validation required
```

### Validation Rules Structure
```json
{
    "required": true,
    "character_limit": 255,
    "format": "email|url|phone|alphanumeric",
    "no_po_box": true,
    "latin_characters_only": true,
    "file_types": ["PDF", "DOC"],
    "max_pages": 10,
    "max_age_months": 6
}
```

### Expected Data Types
```sql
expected_data_type VARCHAR(50) -- Categories:
'organization_info'    -- Company details, legal structure
'contact_details'     -- Addresses, phone, email
'financial_data'      -- Revenue, assets, funding
'legal_documents'     -- Certificates, articles
'technical_specs'     -- Registry capabilities
'operational_details' -- Business processes
```

## UI Generation Implications

### Form Field Generation
Each question can automatically generate appropriate UI components:
- Text inputs with character limits
- Textareas for long-form content
- File upload components with restrictions
- Dropdown menus with validation
- Radio button groups
- Email/URL/phone inputs with format validation

### Error Handling Strategy
- **Missing Data**: Clear indication when required data unavailable
- **Validation Errors**: Real-time validation with specific error messages
- **Conditional Logic**: Show/hide dependent questions based on previous answers
- **Progress Tracking**: Visual indication of completion status

### Data Source Integration
Questions mapped to evaluation data sources:
- Applicant information → existing applicant tables
- Technical details → technical risk assessment results
- Legal information → trademark/legal analysis results
- Financial projections → business case analysis results

## Error Handling for Missing Data

### Strategy Categories
1. **Skip with Notice**: Questions that can't be answered with available data
2. **Use Placeholder**: Generic but appropriate placeholder text
3. **Request Manual Input**: Flag for human review and completion
4. **Use Evaluation Data**: Extract from existing string evaluation results
5. **Generate from Template**: Use AI to generate based on similar applications

### Missing Data Field Tracking
Track which specific data points are missing for each question:
- Organization details (legal name, jurisdiction, etc.)
- Contact information (addresses, phone, email)
- Financial data (revenue, assets, projections)
- Technical specifications (infrastructure, capabilities)
- Legal documentation (certificates, articles)

This comprehensive parsing specification enables systematic processing of all ~227 ICANN application questions with proper error handling and data source mapping.