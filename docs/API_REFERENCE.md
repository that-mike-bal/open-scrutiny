# API Reference

## 🚀 **Production Ready Endpoints**

All endpoints have been tested and verified working with complete data persistence.

---

## **Evaluation Management**

### **Submit TLD Evaluation** ✅
```http
POST /api/evaluations/auto-submit
Content-Type: application/json

{
  "tld_string": "example",
  "use_case": "Business application for gTLD", 
  "enable_auto_execution": true
}
```

**Response (success — HTTP 200):**
```json
{
  "evaluation_id": "uuid-string",
  "tld_string": "example",
  "workflows_queued": [
    "technical_risk_assessment",
    "legal_risk_assessment",
    "policy_safeguard_review"
  ],
  "status": "RUNNING",
  "message": "Evaluation started for .example"
}
```

**Response (server busy — HTTP 409):**
```json
{
  "detail": "Server is currently processing .other. Please wait and try again."
}
```

**Process:**
- Checks server availability **before** creating any DB entries
- If busy: returns HTTP 409 immediately (no DB row created)
- If available: creates TLD string record, starts 3 workflows sequentially (~6 minutes total)
- Report generation runs **before** marking COMPLETED (server stays busy until report is done)
- Updates dashboard with real-time progress

---

### **List All Evaluations** ✅
```http
GET /api/evaluations
```

**Response:**
```json
[
  {
    "id": "uuid-string",
    "tld_string": "example",
    "use_case": "Business application",
    "overall_status": "completed",
    "created_at": "2025-01-23T10:30:00Z",
    "completed_at": "2025-01-23T10:36:00Z"
  }
]
```

---

### **Get Evaluation by String** ✅
```http
GET /evaluations/{tld_string}
```

**Response:**
```json
{
  "id": "uuid-string",
  "tld_string": "example", 
  "use_case": "Business application",
  "workflow_type": "technical_risk_assessment",
  "overall_status": "completed",
  "created_at": "2025-01-23T10:30:00Z",
  "completed_at": "2025-01-23T10:36:00Z"
}
```

---

### **Get Workflow Status** ✅
```http
GET /evaluations/{tld_string_id}/workflows
```

**Response:**
```json
[
  {
    "id": "workflow-uuid",
    "workflow_type": "technical_risk_assessment",
    "status": "COMPLETED",
    "started_at": "2025-01-23T10:30:00Z",
    "completed_at": "2025-01-23T10:32:00Z"
  },
  {
    "id": "workflow-uuid-2", 
    "workflow_type": "legal_risk_assessment",
    "status": "COMPLETED",
    "started_at": "2025-01-23T10:32:00Z",
    "completed_at": "2025-01-23T10:33:00Z"
  },
  {
    "id": "workflow-uuid-3",
    "workflow_type": "policy_safeguard_review", 
    "status": "COMPLETED",
    "started_at": "2025-01-23T10:33:00Z",
    "completed_at": "2025-01-23T10:36:00Z"
  }
]
```

---

### **Delete Evaluation** ✅
```http
DELETE /api/evaluations/{evaluation_id}
```

**Response:**
```json
{
  "success": true,
  "message": "Evaluation deleted successfully"
}
```

---

## **Report Generation**

### **Generate Comprehensive Report** ✅
```http
POST /reports/generate
Content-Type: application/json

{
  "tld_string_id": "uuid-string",
  "tld_string": "example",
  "create_google_doc": false,
  "format": "markdown"
}
```

**Response:**
```json
{
  "success": true,
  "report": "# TLD Evaluation Report: .example\n\n## Executive Summary...",
  "google_doc_url": null,
  "google_docs_enabled": false,  
  "risk_score": 2.1,
  "overall_assessment": "LOW_RISK"
}
```

---

## **System Status**

### **Health Check** ✅
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "CrewAI TLD Evaluation Service (Synchronous)",
  "timestamp": "2025-01-23T10:30:00Z",
  "version": "2.0.0"
}
```

---

### **List Available Workflows** ✅
```http
GET /workflows
```

**Response:**
```json
{
  "workflows": [
    "technical_risk_assessment",
    "legal_risk_assessment", 
    "policy_safeguard_review"
  ],
  "total_workflows": 3
}
```

---

## **Data Structure**

### **Complete Evaluation Data**
When you submit an evaluation, the system creates:

```sql
-- 1 Main Record
tld_strings: {
  id: "uuid",
  tld_string: "example", 
  use_case: "description",
  overall_status: "completed",
  created_at: "timestamp",
  completed_at: "timestamp"
}

-- 3 Workflow Records  
workflow_executions: [
  { workflow_type: "technical_risk_assessment", status: "COMPLETED", ... },
  { workflow_type: "legal_risk_assessment", status: "COMPLETED", ... },
  { workflow_type: "policy_safeguard_review", status: "COMPLETED", ... }
]

-- 12 Task Records (4 per workflow)
task_executions: [
  { task_name: "comprehensive_similarity_analysis", result_status: "CLEAR", result_data: {...} },
  { task_name: "dns_stability_review", result_status: "CLEAR", result_data: {...} },
  { task_name: "name_collision_assessment", result_status: "CLEAR", result_data: {...} },
  { task_name: "technical_risk_validation", result_status: "CLEAR", result_data: {...} },
  { task_name: "global_trademark_assessment", result_status: "CLEAR", result_data: {...} },
  { task_name: "patent_conflict_assessment", result_status: "CLEAR", result_data: {...} },
  { task_name: "legal_risk_validation", result_status: "CLEAR", result_data: {...} },
  { task_name: "geographic_name_assessment", result_status: "CLEAR", result_data: {...} },
  { task_name: "safeguard_assessment", result_status: "CLEAR", result_data: {...} },
  { task_name: "gac_risk_analysis", result_status: "CLEAR", result_data: {...} },
  { task_name: "cultural_linguistic_assessment", result_status: "CLEAR", result_data: {...} },
  { task_name: "policy_safeguard_validation", result_status: "CLEAR", result_data: {...} }
]
```

### **Task Result Data Structure**
Each `task_execution.result_data` contains:
```json
{
  "summary": "Brief task description",
  "full_output": "Complete CrewAI markdown analysis (2,000-7,000 characters)"
}
```

---

## **Error Responses**

### **409 Conflict (Server Busy)**
```json
{
  "detail": "Server is currently processing .example. Please wait and try again."
}
```
Returned when `enable_auto_execution: true` and the server is already running an evaluation. The client should keep the string in its queue and retry when the server becomes available.

### **400 Bad Request**
```json
{
  "success": false,
  "error": "Missing required field: tld_string",
  "details": "Request validation failed"
}
```

### **404 Not Found**
```json
{
  "success": false,
  "error": "Evaluation not found",
  "evaluation_id": "uuid-string"
}
```

### **500 Internal Server Error**
```json
{
  "success": false,
  "error": "Workflow execution failed",
  "details": "Technical error details"
}
```

---

## **Usage Examples**

### **Complete Evaluation Flow**
```bash
# 1. Submit evaluation
curl -X POST http://localhost:8000/api/evaluations/auto-submit \
  -H "Content-Type: application/json" \
  -d '{"tld_string": "test", "use_case": "Testing", "enable_auto_execution": true}'

# 2. Check workflow status  
curl http://localhost:8000/evaluations/{tld_string_id}/workflows

# 3. Generate report
curl -X POST http://localhost:8000/reports/generate \
  -H "Content-Type: application/json" \
  -d '{"tld_string_id": "uuid", "tld_string": "test", "format": "markdown"}'
```

### **Dashboard Integration**
```typescript
// Submit evaluation
const response = await fetch('/api/evaluations/auto-submit', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    tld_string: 'example',
    use_case: 'Business application',
    enable_auto_execution: true
  })
});

// Poll for completion
const checkStatus = async () => {
  const result = await fetch(`/evaluations/${tld_string_id}/workflows`);
  const workflows = await result.json();
  return workflows.every(w => w.status === 'COMPLETED');
};
```

---

## **Performance & Reliability**

### **Execution Times**
- **technical_risk_assessment**: ~2 minutes
- **legal_risk_assessment**: ~1 minute  
- **policy_safeguard_review**: ~3 minutes
- **Total**: ~6 minutes for complete evaluation

### **Data Persistence**
- ✅ **Complete storage verified**: All 12 task executions saved
- ✅ **Full analysis captured**: ~40,000 characters per evaluation
- ✅ **Database constraints**: All foreign keys and data types validated
- ✅ **Error handling**: Comprehensive logging and recovery

### **System Status**
- 🟢 **Production Ready**: End-to-end system verified working
- 🟢 **Data Integrity**: Complete CrewAI output stored in database
- 🟢 **Real-time Updates**: Dashboard displays live evaluation data
- 🟢 **API Reliability**: All endpoints tested and operational

---

**For engineers**: This API is production-ready and provides complete TLD evaluation capabilities with full data persistence. No mock data or placeholder functionality. 