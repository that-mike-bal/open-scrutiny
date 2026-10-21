# Client Architecture - Working System Documentation

## Overview
This document describes the complete, functioning client architecture for TLD evaluation submissions. Last verified operational: April 2026 (CrewAI 1.13.0 + native Gemini provider).

## System Architecture

### High-Level Flow
```
User Input → Client Validation → API Submission → CrewAI Workflows → Database Storage → Dashboard Display
```

## 1. Client Components

### Dashboard Component (`SimpleDashboard.tsx`)
**Purpose**: Main interface showing TLD evaluation cards and handling submissions

**Key Features**:
- ✅ Displays evaluation cards with real-time status
- ✅ Handles new string modal opening/closing  
- ✅ Makes API calls to CrewAI service
- ✅ Shows loading states and progress

**Critical Code Paths**:
```typescript
// Modal submission handler (SimpleDashboard.tsx handleSuccess)
// Uses getApiBase() for environment-aware URL (localhost:8000 dev, production URL in prod)
const handleSuccess = async (tldString: string, useCase: string, autoExecution: boolean, stringType?: string) => {
  // 1. Check server availability via /api/server-status
  // 2. If available: call submitEvaluationDirect → POST /api/evaluations/auto-submit
  // 3. If busy: addToQueue (client-side localStorage only, no DB entry)
  // 4. If submitEvaluationDirect returns 409 (ServerBusyError): falls back to queue
}

// Queue auto-submission is handled solely by QueuedStrings.tsx
// (polls server status every 3s, auto-submits when available)
// submitQueuedString → submitEvaluationDirect (success) → dequeueString (silent)
//                     → ServerBusyError → keep in queue silently
//                     → other error → show toast, keep in queue
```

### New Evaluation Modal (`NewEvaluationModal.tsx`)
**Purpose**: Form for submitting new TLD strings with real-time validation

**Critical Architecture Decision - DUAL DATA SOURCES**:
```typescript
// 1. LOCAL DATA FILES (for real-time compliance checks):
//    - Purpose: Instant validation as user types (1-5ms response)
//    - Files: /public/data/Iana Root DB.json, reserved_names.json, etc.
//    - Why: API calls would cause timeouts and poor UX

// 2. BACKEND API (for actual submission):
//    - Purpose: Create evaluation record and start CrewAI workflow
//    - Endpoint: http://localhost:8000/api/evaluations/auto-submit
//    - Why: Requires backend processing and database operations
```

**Key Features**:
- ✅ Real-time binary compliance validation using local data files
- ✅ Form validation (TLD string format, use case required)
- ✅ Visual feedback with pass/fail indicators
- ✅ Calls parent component's `onSuccess` handler

**Flow**:
1. User types TLD string → Real-time validation using local files
2. User fills use case → Form validation
3. User submits → Calls `onSuccess(tldString, useCase, autoExecution)`
4. Parent component makes API call to CrewAI service

### Data Fetching Hook (`useTldEvaluations.ts`)
**Purpose**: Fetches evaluations from Supabase with proper field mapping

**Critical Field Mapping**:
```typescript
// Database uses 'overall_status' but UI expects 'status'
const transformedData = data?.map(item => ({
  ...item,
  status: item.overall_status || 'PENDING',  // ✅ CRITICAL MAPPING
  task_executions: item.task_executions || [],
  workflow_executions: item.workflow_executions || []
}))
```

**Database Query**:
```typescript
const { data, error } = await supabase
  .from('tld_strings')
  .select(`
    *,
    task_executions:task_executions(
      id, task_name, agent_name, status, result_status, result_data,
      confidence_score, completed_at, created_at, updated_at,
      execution_time_seconds,
      task_definitions:task_definitions(task_name, task_category, description)
    ),
    workflow_executions:workflow_executions(
      id, workflow_type, status, started_at, completed_at
    )
  `)
  .order('created_at', { ascending: false })
```

## 2. Backend Integration

### CrewAI Service Endpoint
**URL**: `${getApiBase()}/api/evaluations/auto-submit` (resolves to `http://localhost:8000` in dev, production URL in prod)

**Request Format**:
```json
{
  "tld_string": "muse",
  "use_case": "Testing submission flow", 
  "enable_auto_execution": true
}
```

**Response Format (success)**:
```json
{
  "evaluation_id": "59138d60-7198-4990-b155-f78db3e2111b",
  "tld_string": "muse",
  "workflows_queued": ["technical_risk_assessment", "legal_risk_assessment", "policy_safeguard_review"],
  "status": "RUNNING",
  "message": "Evaluation started for .muse"
}
```

**Error Response (server busy — HTTP 409)**:
```json
{
  "detail": "Server is currently processing .example. Please wait and try again."
}
```
The backend checks server availability **before** creating any DB entries. If busy, it returns 409 immediately — no phantom rows are created or deleted.

### Database Schema Alignment

**TLD Strings Table Fields** (11 columns):
- `id` (UUID, primary key)
- `user_id` (UUID, nullable)
- `tld_string` (text, the TLD being evaluated)
- `use_case` (text, application description)
- `workflow_type` (text)
- `overall_status` (text, maps to UI `status` field) ← **CRITICAL MAPPING**
- `generated_report` (JSONB, AI-generated report content)
- `string_type` (text, e.g. 'standard', 'brand', 'community')
- `created_at`, `updated_at`, `completed_at` (timestamps)

**Task Executions Table Fields**:
- `id`, `tld_string_id`, `task_definition_id`, `workflow_id`
- `task_name`, `status`, `result_status`, `result_data` ← **Contains evaluation outputs**
- `agent_name`, `started_at`, `completed_at`, `execution_time_seconds`
- `raw_output` ← **Where Gemini reports are stored**

## 3. Critical Fixes Applied

### 1. Database Field Mapping
**Problem**: Client expected `status` field, database used `overall_status`
**Solution**: Map `item.overall_status` to `status` in `useTldEvaluations.ts`

### 2. CORS Configuration  
**Problem**: Browser blocked API calls due to CORS
**Solution**: CrewAI service includes proper CORS headers:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # ✅ Client port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
```

### 3. Clean Database Operations
**Problem**: Service crashed trying to insert non-existent fields (`has_evaluation`, `has_application_draft`, `workflow_id`, `error_message` — none exist in `tld_strings`)
**Solution**: Only insert columns that actually exist in the DB:
```python
# Step 1: String submission - only valid columns
tld_data = {
    'tld_string': tld_string,
    'use_case': use_case,
    'overall_status': 'RUNNING',
    'string_type': string_type  # optional
}

# Step 2: After evaluation completes (set by run_sequential_workflows)
completion_data = {
    'overall_status': 'COMPLETED',
    'completed_at': datetime.now().isoformat()
}
```

### 4. Gemini Report Storage
**Problem**: Reports generated but not visible in UI
**Solution**: Store as task execution with expected field name:
```python
report_task_data = {
    'task_name': 'gemini_report_generation',  # ✅ UI looks for this exact name
    'raw_output': report_html,                # ✅ UI reads from this field
    'status': 'COMPLETED',
    'result_status': 'CLEAR'
}
```

## 4. Environment Configuration

### Client Environment (`.env`)
```
VITE_CREWAI_ENDPOINT=http://localhost:8000
```

### Service Requirements
- **CrewAI Service**: Running on port 8000
- **Supabase**: Connected with proper credentials in `/secrets`
- **API Keys**: OpenAI (for agents), Gemini (for reports) in `/secrets`

## 5. User Flow - Complete Working Process

### Step 1: String Submission
1. User opens dashboard → Clicks "Add New String"
2. Modal opens → User types TLD string
3. **Real-time validation** using local data files (instant feedback)
4. User enters use case → Clicks submit
5. Modal calls `handleSuccess()` → API call to CrewAI service
6. Service creates database entry → Starts background workflows
7. Modal closes → Dashboard shows new card with "RUNNING" status

### Step 2: Workflow Execution  
1. **Technical Risk Assessment**: 4 agents, 4 tasks (~60 seconds)
   - DNS stability review
   - Name collision assessment  
   - Similarity analysis
   - Technical risk validation
2. **Legal Risk Assessment**: 2 agents, 3 tasks (~45 seconds)
   - Trademark assessment
   - Patent conflict assessment
   - Legal risk validation  
3. **Policy Safeguard Review**: 3 agents, 3 tasks (~120 seconds)
   - Policy compliance review
   - Safeguard assessment
   - Policy risk validation

### Step 3: Report Generation
1. All workflows complete → Automatic Gemini report generation
2. Report stored as task execution with `task_name: 'gemini_report_generation'`
3. Report content in `raw_output` field → UI can display it
4. Report generation completes → **then** `overall_status` updated to `'COMPLETED'`
   (Server stays "busy" during report generation so the queue doesn't auto-submit prematurely)

### Step 4: Dashboard Display
1. Dashboard polls every few seconds → Shows updated status
2. Cards show evaluation progress → User can click for details
3. Evaluation document shows all task results → Including final report

## 6. Key Success Factors

### ✅ What Makes It Work
1. **Proper field mapping** between database schema and UI expectations
2. **CORS configuration** allowing client-to-service communication  
3. **Clean database operations** following logical user flow
4. **Background workflow execution** without blocking the UI
5. **Real-time validation** using local data files for instant feedback
6. **Comprehensive error handling** with graceful degradation

### ⚠️ Critical Dependencies
1. **CrewAI service** must be running on port 8000
2. **Supabase credentials** must be in `/secrets` directory
3. **API keys** (OpenAI, Gemini) must be configured
4. **Database schema** must match client expectations
5. **Local data files** must be in `/public/data` for validation

## 7. Monitoring & Debugging

### Service Logs
```bash
# Local development
cd crewai_service && python app.py  # logs to stdout

# Production (Render)
# Use Render dashboard → Logs, or Render MCP tools
```

### Key Log Indicators
- ✅ `Auto-submitting evaluation for {string}`
- ✅ `Created TLD entry: {uuid}`  
- ✅ `Starting sequential workflows`
- ✅ `Workflow {name} completed successfully`
- ✅ `Generated comprehensive investment report`

### Database Verification
```sql
-- Check recent submissions
SELECT tld_string, overall_status, created_at FROM tld_strings ORDER BY created_at DESC LIMIT 5;

-- Check task executions  
SELECT task_name, result_status, created_at FROM task_executions WHERE tld_string_id = '{uuid}';
```

---

**Last Updated**: April 6, 2026
**Status**: FULLY OPERATIONAL (CrewAI 1.13.0, native Gemini provider)
**Stack**: Python 3.12 / CrewAI 1.13.0 / React 18+ / Supabase / Render