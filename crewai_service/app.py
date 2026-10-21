"""
FastAPI service for running CrewAI TLD evaluation workflows
"""

from fastapi import FastAPI, HTTPException, Response, Request, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import json
import uuid
import logging
import traceback
from datetime import datetime
import httpx
import asyncio
import sys
import os
from pathlib import Path
from contextlib import asynccontextmanager
# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crewai_service.crew import CrewBuilder, build_crew_for_workflow, kickoff_and_get_results
from crewai_service.utils.config import ensure_env_secrets, load_api_key
from crewai_service.utils.supabase_client import get_supabase_client
from crewai_service.utils.api_call_logger import clear_api_call_log, get_api_call_log, compute_tool_execution_summary, get_trademark_audit_log, partition_api_calls_by_task
from crewai_service.utils.audit_log_generator import TASK_METADATA
from crewai_service.utils.google_drive_exporter import export_report_to_google_drive, batch_export_all_reports
from crewai_service.rag_chat_agent import rag_chat_agent
from supabase import create_client
from postgrest import APIError
from db.tld_application_store import TldApplicationStore
from crewai_service.file_upload_service import file_upload_service
from pydantic import BaseModel, EmailStr, field_validator
import re

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def _add_string_to_json_file(tld_string: str):
    """Add a TLD string to the existing strings JSON file"""
    import json
    import os
    
    strings_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'existing_tld_strings.json')
    cleaned_tld = tld_string.lower().lstrip('.')
    
    try:
        # Load existing strings
        if os.path.exists(strings_file):
            with open(strings_file, 'r') as f:
                existing_strings = json.load(f)
        else:
            existing_strings = []
        
        # Add string if not already present
        if cleaned_tld not in existing_strings:
            existing_strings.append(cleaned_tld)
            existing_strings.sort()  # Keep sorted for easier management
            
            # Write back to file
            with open(strings_file, 'w') as f:
                json.dump(existing_strings, f, indent=2)
            
            logger.info(f"Added '{cleaned_tld}' to existing strings file")
        
    except Exception as e:
        logger.error(f"Error updating existing strings file: {e}")

def _remove_string_from_json_file(tld_string: str):
    """Remove a TLD string from the existing strings JSON file"""
    import json
    import os
    
    strings_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'existing_tld_strings.json')
    cleaned_tld = tld_string.lower().lstrip('.')
    
    try:
        # Load existing strings
        if os.path.exists(strings_file):
            with open(strings_file, 'r') as f:
                existing_strings = json.load(f)
        else:
            return  # File doesn't exist, nothing to remove
        
        # Remove string if present
        if cleaned_tld in existing_strings:
            existing_strings.remove(cleaned_tld)
            
            # Write back to file
            with open(strings_file, 'w') as f:
                json.dump(existing_strings, f, indent=2)
            
            logger.info(f"Removed '{cleaned_tld}' from existing strings file")
        
    except Exception as e:
        logger.error(f"Error updating existing strings file: {e}")

# API keys are loaded by ensure_env_secrets() in lifespan startup

def load_gemini_prompt() -> str:
    """Load Gemini prompt template from file"""
    prompt_file = os.path.join(os.path.dirname(__file__), 'prompts', 'gemini_report_prompt.txt')
    try:
        with open(prompt_file, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        logger.error(f"Gemini prompt file not found: {prompt_file}")
        # Fallback to a basic prompt
        return """You are an expert gTLD analyst. Generate a comprehensive TLD feasibility assessment report as HTML.
        
TLD STRING: .{tld_string}
EVALUATION DATA: {evaluation_data}

Create a professional report with executive summary, compliance analysis, risk assessment, and recommendations."""
    except Exception as e:
        logger.error(f"Failed to load Gemini prompt: {e}")
        # Same fallback
        return """You are an expert gTLD analyst. Generate a comprehensive TLD feasibility assessment report as HTML.
        
TLD STRING: .{tld_string}
EVALUATION DATA: {evaluation_data}

Create a professional report with executive summary, compliance analysis, risk assessment, and recommendations."""

def create_personalized_gemini_prompt(tld_string: str, task_executions: list) -> str:
    """
    Create a unique prompt for each TLD string by injecting CrewAI output into the template.
    
    Args:
        tld_string: The TLD string being evaluated (e.g., 'example')
        task_executions: List of task execution results from CrewAI workflows
    
    Returns:
        Personalized prompt ready to send to Gemini
    """
    try:
        # Load the comprehensive prompt template
        template = load_gemini_prompt()
        
        # Format raw output - the actual CrewAI analysis content
        raw_output_sections = []
        
        for task in task_executions:
            task_name = task.get('task_name', 'Unknown Task')
            workflow_type = task.get('workflow_type', 'Unknown Workflow')
            agent_name = task.get('agent_name', 'Unknown Agent')
            
            # Get the actual analysis content - this is what CrewAI produced
            full_output = task.get('full_output', '')
            result_data = task.get('result_data', {})
            output_summary = task.get('output_summary', '')
            
            # Extract actual content from result_data if it's a dict
            if isinstance(result_data, dict):
                # Prioritize raw_output, then full_output, then output from result_data
                extracted_content = (
                    result_data.get('raw_output', '') or 
                    result_data.get('full_output', '') or 
                    result_data.get('output', '')
                )
            else:
                extracted_content = str(result_data) if result_data else ''
            
            # Use the most detailed content available
            content = full_output or extracted_content or output_summary or 'No detailed output available'
            
            # Create formatted section with actual CrewAI analysis
            task_section = f"""
## {task_name.replace('_', ' ').title()}
**Workflow**: {workflow_type}
**Agent**: {agent_name}

{content}

---
"""
            raw_output_sections.append(task_section)
        
        # Combine all raw CrewAI output
        raw_output = "\n".join(raw_output_sections)
        
        # Inject variables into template using safe string replacement
        # Use replace() instead of format() to avoid issues with JSON braces in template
        # Only inject TLD string and raw output - metadata isn't needed for report generation
        # Note: Template uses escaped underscores {tld_string} and {raw_output}
        personalized_prompt = template.replace('{tld_string}', tld_string)
        personalized_prompt = personalized_prompt.replace('{raw_output}', raw_output)
        
        return personalized_prompt
        
    except Exception as e:
        logger.error(f"Error creating personalized Gemini prompt: {str(e)}")
        # Don't create generic fallback content - raise the error instead
        raise Exception(f"Failed to create personalized prompt for .{tld_string}: {str(e)}")

# Simplified server status - just check if busy
async def get_server_status():
    """Get simple server status - just running or available"""
    try:
        app_store = TldApplicationStore()
    except Exception as e:
        return {"error": "Database not available"}
    
    try:
        # Get currently running evaluations
        running_response = app_store.supabase.table('tld_strings').select('*').eq('overall_status', 'RUNNING').execute()
        running = running_response.data if running_response.data else []
        
        return {
            "running_count": len(running),
            "running": running,
            "available": len(running) == 0
        }
    except Exception as e:
        logger.error(f"Error getting server status: {e}")
        return {"error": str(e), "available": False}

# Lifespan event handler (modern FastAPI approach)
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events"""
    # Startup — log which credentials are configured (names only)
    ensure_env_secrets()
    logger.info("Starting CrewAI evaluation service")
    logger.info(f"Gemini API key loaded: {'Yes' if os.getenv('GEMINI_API_KEY') else 'No'}")
    logger.info("Service initialized - no background tasks needed")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down CrewAI service")
    logger.info("✅ Service stopped")

# Create FastAPI app
app = FastAPI(
    title="CrewAI TLD Evaluation Service",
    description="AI-powered TLD string evaluation using CrewAI multi-agent orchestration",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for the canvas interface
# CORS origins come from CORS_ALLOW_ORIGINS (comma-separated); defaults to local
# dev origins. Never combine "*" with allow_credentials=True.
_default_cors_origins = (
    "http://localhost:3000,http://localhost:3001,http://localhost:5173,"
    "http://localhost:5174,http://localhost:5175,http://localhost:5176,"
    "http://localhost:5177,http://localhost:5178"
)
_cors_allow_origins = [o.strip() for o in os.getenv("CORS_ALLOW_ORIGINS", _default_cors_origins).split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allow_origins,
    allow_origin_regex=os.getenv("CORS_ALLOW_ORIGIN_REGEX", r"https://.*\.onrender\.com"),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Note: Static files will be mounted after API routes are defined to avoid conflicts

from datetime import timedelta

# Simplified queue management - no background tasks needed

async def trigger_workflow(tld_string_id: str, workflow_type: str, priority: int = 3, auto_triggered: bool = False):
    """Execute a single workflow for a TLD string"""
    try:
        # Get supabase client
        app_store = TldApplicationStore()
        supabase = app_store.supabase
        
        logger.info(f"🚀 Starting {workflow_type} workflow for TLD ID: {tld_string_id}")
        
        # Get TLD string info
        tld_result = supabase.table('tld_strings').select('*').eq('id', tld_string_id).execute()
        if not tld_result.data:
            logger.error(f"❌ TLD string not found: {tld_string_id}")
            return None
            
        tld_data = tld_result.data[0]
        tld_string = tld_data['tld_string'] 
        use_case = tld_data.get('use_case', '')
        
        # Update workflow status to RUNNING
        await update_workflow_status(supabase, tld_string_id, workflow_type, "RUNNING")
        
        # Execute the workflow using existing logic
        import os

        # Determine config directory based on workflow type
        evaluation_workflows = ['technical_risk_assessment', 'legal_risk_assessment', 'policy_safeguard_review']
        application_workflows = ['application_generation']

        if workflow_type in evaluation_workflows:
            config_dir = os.path.join(os.path.dirname(__file__), "evaluation", "config")
        elif workflow_type in application_workflows:
            config_dir = os.path.join(os.path.dirname(__file__), "application", "config")
        else:
            # Unknown workflow type: fall back to the evaluation ruleset
            config_dir = os.path.join(os.path.dirname(__file__), "evaluation", "config")

        # Use workflows.yaml file instead of individual workflow files
        workflow_config_path = os.path.join(config_dir, "workflows.yaml")

        if not os.path.exists(workflow_config_path):
            logger.error(f"❌ Workflow config not found: {workflow_config_path}")
            await update_workflow_status(supabase, tld_string_id, workflow_type, "FAILED", f"Config file not found: {workflow_config_path}")
            return {'status': 'FAILED', 'error': 'Config file not found'}
        
        # Load and execute workflow using CrewBuilder
        crew_builder = CrewBuilder(config_dir=config_dir)
        crew = build_crew_for_workflow(
            workflow_name=workflow_type,
            tld_string=tld_string,
            config_dir=config_dir
        )

        # Prepare inputs for the workflow
        inputs = {
            "tld_string": tld_string,
            "workflow_name": workflow_type,
            "tld_string_id": tld_string_id
        }

        result = kickoff_and_get_results(crew=crew, inputs=inputs)
        
        if result and result.get('status') == 'success':
            await update_workflow_status(supabase, tld_string_id, workflow_type, "COMPLETED")
            logger.info(f"✅ {workflow_type} completed successfully for {tld_string}")
            
            # Note: Overall completion and report generation handled by sequential workflow completion
            logger.info(f"Individual workflow {workflow_type} completed, waiting for all workflows to finish")
            
            return {'status': 'COMPLETED', 'result': result}
        else:
            error_msg = result.get('error', 'Unknown error') if result else 'No result returned'
            await update_workflow_status(supabase, tld_string_id, workflow_type, "FAILED", error_msg)
            logger.error(f"❌ {workflow_type} failed for {tld_string}: {error_msg}")
            
            # Note: Queue processing handled by sequential workflow completion or background processor
            
            return {'status': 'FAILED', 'error': error_msg}
            
    except Exception as e:
        logger.error(f"❌ Error executing {workflow_type} for {tld_string_id}: {e}")
        await update_workflow_status(supabase, tld_string_id, workflow_type, "FAILED", str(e))
        
        # Note: Queue processing handled by sequential workflow completion or background processor
        
        return {'status': 'FAILED', 'error': str(e)}


async def execute_auto_evaluation_workflows(evaluation):
    """Execute the full auto-evaluation workflow for a queued item - ALL THREE WORKFLOWS SEQUENTIALLY"""
    try:
        tld_string_id = evaluation['id']
        tld_string = evaluation['tld_string']
        
        logger.info(f"🚀 Starting sequential auto-evaluation for: {tld_string}")
        
        # Execute all three workflows sequentially to avoid rate limiting
        workflows = [
            'technical_risk_assessment',
            'legal_risk_assessment', 
            'policy_safeguard_review'
        ]
        
        for i, workflow_type in enumerate(workflows, 1):
            logger.info(f"🔄 Starting workflow {i}/3: {workflow_type} for {tld_string}")
            await trigger_workflow(tld_string_id, workflow_type, priority=5, auto_triggered=True)
            logger.info(f"✅ Completed workflow {i}/3: {workflow_type} for {tld_string}")
        
        logger.info(f"🎉 All workflows completed for: {tld_string}")
        
    except Exception as e:
        logger.error(f"❌ Error in execute_auto_evaluation_workflows: {e}")
        raise

# Deprecated on_event handlers replaced with lifespan above

# Load workflows at startup
def load_workflows():
    """Load available workflows from configuration"""
    try:
        import yaml
        # Get the directory of this file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(current_dir, 'config', 'workflows.yaml')
        
        # Log the path for debugging
        logger.info(f"Loading workflows from: {config_path}")
        logger.info(f"File exists: {os.path.exists(config_path)}")
        
        with open(config_path, 'r') as f:
            workflows = yaml.safe_load(f)
        logger.info(f"Successfully loaded workflows: {list(workflows.keys())}")
        return workflows
    except Exception as e:
        logger.error(f"Failed to load workflows: {e}")
        logger.error(f"Current working directory: {os.getcwd()}")
        logger.error(f"Script directory: {os.path.dirname(os.path.abspath(__file__))}")
        return {}

WORKFLOWS = load_workflows()

def extract_markdown_summary(output_str: str, task_name: str) -> str:
    """Extract and format markdown summary from task output"""
    try:
        # If output already looks like markdown, use it directly
        if output_str.startswith('#') or '##' in output_str:
            return output_str
        
        # For binary gate results, create structured markdown
        if 'BINARY_GATE_RESULT:' in output_str:
            result = "PASS" if "BINARY_GATE_RESULT: PASS" in output_str else "BLOCKED"
            status_line = output_str.split('\n')[0] if '\n' in output_str else output_str[:100]
            
            markdown = f"""# {task_name.replace('_', ' ').title()}

## Result
**Status:** {result}

## Summary
{status_line}

## Details
{output_str[:1000]}...
"""
            return markdown
        
        # For other outputs, create basic markdown structure
        lines = output_str.split('\n')
        title = f"# {task_name.replace('_', ' ').title()}"
        
        # Find key sections
        summary_lines = []
        for line in lines[:10]:  # Look at first 10 lines for summary info
            if line.strip() and not line.startswith('#'):
                summary_lines.append(line.strip())
        
        summary = '\n'.join(summary_lines[:3]) if summary_lines else "Task completed successfully"
        
        markdown = f"""{title}

## Summary
{summary}

## Full Output
{output_str[:1500]}...
"""
        return markdown
        
    except Exception as e:
        logger.warning(f"Error extracting markdown for {task_name}: {e}")
        return f"# {task_name.replace('_', ' ').title()}\n\n{output_str[:1000]}..."

def parse_html_risk_assessment(report_content: str) -> Dict[str, Any]:
    """Parse risk assessment data from HTML report"""
    import re
    
    def clean_text(text):
        """Remove HTML tags and clean text"""
        if not text:
            return text
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    risk_data = {
        'risk_score': None,
        'risk_classification': None,
        'risk_level': None,
        'recommendation': None
    }
    
    try:
        # Try multiple patterns to find risk score
        score_patterns = [
            r'(\d+)/100',  # Look for "68/100" pattern
            r'Risk Score[:\s]*(\d+)',
            r'<div class="risk-score[^"]*">(\d+)/100',
            r'RISK SCORE:\s*(\d+)'
        ]
        
        for pattern in score_patterns:
            score_match = re.search(pattern, report_content, re.IGNORECASE)
            if score_match:
                risk_data['risk_score'] = int(score_match.group(1))
                break
        
        # Extract risk classification with better patterns
        classification_patterns = [
            r'OVERALL RISK CLASSIFICATION:\s*\*\*([^*\n]+)\*\*',  # **HIGH** format from Gemini
            r'OVERALL RISK CLASSIFICATION:\s*\*\*?([^*\n]+?)\*\*?',  # Handle optional ** formatting
            r'OVERALL RISK CLASSIFICATION:\s*([^<\n*]+)',
            r'Risk Classification:\s*([^<\n]+)',
            r'<div class="risk-classification[^"]*">([^<]+)',
            r'Classification:\s*([^<\n]+)'
        ]
        
        for pattern in classification_patterns:
            match = re.search(pattern, report_content, re.IGNORECASE)
            if match:
                risk_data['risk_classification'] = clean_text(match.group(1))
                break
        
        # Extract risk level
        level_patterns = [
            r'Risk Level:\s*([^<\n]+)',
            r'<div class="risk-level[^"]*">([^<]+)',
            r'Level:\s*([^<\n]+)'
        ]
        
        for pattern in level_patterns:
            match = re.search(pattern, report_content, re.IGNORECASE)
            if match:
                risk_data['risk_level'] = clean_text(match.group(1))
                break
        
        # Extract recommendation
        rec_patterns = [
            r'Recommendation:\s*([^<\n]+)',
            r'<div class="recommendation[^"]*">([^<]+)',
            r'Investment Recommendation:\s*([^<\n]+)'
        ]
        
        for pattern in rec_patterns:
            match = re.search(pattern, report_content, re.IGNORECASE)
            if match:
                risk_data['recommendation'] = clean_text(match.group(1))
                break
        
        logger.info(f"✅ Parsed HTML risk data: {risk_data}")
        
    except Exception as e:
        logger.error(f"❌ Error parsing HTML risk assessment: {e}")
    
    return risk_data

def parse_gemini_json_response(response_content: str) -> Dict[str, Any]:
    """Parse JSON response from Gemini and extract structured data"""
    import json
    import re
    
    result = {
        'risk_assessment': None,
        'scoring_breakdown': None,
        'executive_summary': None,
        'compliance_status': None,
        'risk_mitigation': None,
        'detailed_report': None,
        'success': False
    }
    
    try:
        # Clean the response more aggressively
        content = response_content.strip()
        
        # Remove markdown code blocks
        if content.startswith('```json'):
            content = content[7:]
        elif content.startswith('```'):
            content = content[3:]
        if content.endswith('```'):
            content = content[:-3]
        
        # Remove any leading/trailing whitespace
        content = content.strip()
        
        # Try to find JSON content within the response
        json_match = re.search(r'(\{.*\})', content, re.DOTALL)
        if json_match:
            content = json_match.group(1)
        
        # Clean up common JSON formatting issues
        content = re.sub(r'\\n\s*', ' ', content)  # Replace escaped newlines with spaces
        content = re.sub(r'\n\s*', ' ', content)   # Replace actual newlines with spaces
        content = re.sub(r'\s+', ' ', content)     # Collapse multiple spaces
        
        logger.info(f"🔍 Attempting to parse JSON content: {content[:200]}...")
        
        # Parse JSON
        parsed_data = json.loads(content)
        
        # Extract the structured components
        result['risk_assessment'] = parsed_data.get('risk_assessment', {})
        result['scoring_breakdown'] = parsed_data.get('scoring_breakdown', {})
        result['executive_summary'] = parsed_data.get('executive_summary', {})
        result['compliance_status'] = parsed_data.get('compliance_status', {})
        result['risk_mitigation'] = parsed_data.get('risk_mitigation', {})
        result['detailed_report'] = parsed_data.get('detailed_report', '')
        result['success'] = True
        
        risk_score = result['risk_assessment'].get('risk_score') if result['risk_assessment'] else None
        risk_classification = result['risk_assessment'].get('risk_classification') if result['risk_assessment'] else None
        logger.info(f"✅ Successfully parsed Gemini JSON response with risk score: {risk_score}, classification: {risk_classification}")
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ Error parsing Gemini JSON response: {e}")
        logger.error(f"Raw response content: {response_content[:1000]}...")
        logger.error(f"Cleaned content: {content[:1000] if 'content' in locals() else 'N/A'}...")
    except Exception as e:
        logger.error(f"❌ Unexpected error parsing Gemini response: {e}")
    
    return result

class EvaluationRequest(BaseModel):
    tld_string: str
    use_case: Optional[str] = "General purpose TLD"
    workflow_type: Optional[str] = "technical_risk_assessment"

class EvaluationResponse(BaseModel):
    evaluation_id: str
    workflow_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: str

class ReportGenerationRequest(BaseModel):
    tld_string: str
    evaluation_data: Dict[str, Any]
    create_google_doc: bool = True  # Default to True for better UX

class ReportGenerationResponse(BaseModel):
    success: bool
    report: str
    google_doc_url: Optional[str] = None
    google_docs_enabled: bool = False
    error: Optional[str] = None
    risk_score: Optional[int] = None
    risk_classification: Optional[str] = None
    risk_level: Optional[str] = None
    recommendation: Optional[str] = None

# =====================================================
# APPLICANT MANAGEMENT MODELS
# =====================================================

class KeyPersonnel(BaseModel):
    name: str
    title: str
    role: str
    email: Optional[str] = None
    phone: Optional[str] = None
    background: Optional[str] = None
    contact_type: str = "staff"

class ApplicantCreate(BaseModel):
    legal_name: str
    business_name: Optional[str] = None
    entity_type: str = "Limited Liability Company"
    jurisdiction: str
    incorporation_date: Optional[str] = None
    business_address: str
    mailing_address: Optional[str] = None
    phone: Optional[str] = None
    email: str
    website: Optional[str] = None
    annual_revenue: Optional[float] = None
    total_assets: Optional[float] = None
    funding_sources: Optional[str] = None
    financial_statement_url: Optional[str] = None
    key_personnel: Optional[List[KeyPersonnel]] = []
    registry_experience_description: Optional[str] = None
    current_tlds: Optional[List[str]] = []
    affiliated_organizations: Optional[List[str]] = []
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if v and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
            raise ValueError('Invalid email format')
        return v
    
    @field_validator('annual_revenue', 'total_assets')
    @classmethod
    def validate_financial_amounts(cls, v):
        if v is not None and v < 0:
            raise ValueError('Financial amounts cannot be negative')
        return v
    
    @field_validator('website')
    @classmethod
    def validate_website(cls, v):
        if v and not re.match(r'^https?://', v):
            raise ValueError('Website must start with http:// or https://')
        return v

class ApplicantUpdate(BaseModel):
    legal_name: Optional[str] = None
    business_name: Optional[str] = None
    entity_type: Optional[str] = None
    jurisdiction: Optional[str] = None
    incorporation_date: Optional[str] = None
    business_address: Optional[str] = None
    mailing_address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    annual_revenue: Optional[float] = None
    total_assets: Optional[float] = None
    funding_sources: Optional[str] = None
    financial_statement_url: Optional[str] = None
    key_personnel: Optional[List[KeyPersonnel]] = None
    registry_experience_description: Optional[str] = None
    current_tlds: Optional[List[str]] = None
    affiliated_organizations: Optional[List[str]] = None
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if v and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
            raise ValueError('Invalid email format')
        return v
    
    @field_validator('annual_revenue', 'total_assets')
    @classmethod
    def validate_financial_amounts(cls, v):
        if v is not None and v < 0:
            raise ValueError('Financial amounts cannot be negative')
        return v
    
    @field_validator('website')
    @classmethod
    def validate_website(cls, v):
        if v and not re.match(r'^https?://', v):
            raise ValueError('Website must start with http:// or https://')
        return v

class ApplicantResponse(BaseModel):
    success: bool
    applicant: Optional[Dict[str, Any]] = None
    applicant_id: Optional[str] = None
    message: str
    error: Optional[str] = None

# Task definition ID mapping - now dynamically loaded from database
# This will be populated from the task_definitions table to match YAML task names

def save_task_executions(supabase_client, tld_string_id: str, workflow_execution_id: str, task_executions: List[Dict[str, Any]], workflow_name: str, tld_string: str, use_case: str, api_call_log: Optional[List[Dict[str, Any]]] = None, tool_execution_summary: Optional[Dict[str, Any]] = None, trademark_audit_log: Optional[List[Dict[str, Any]]] = None):
    """
    Save the results of multiple task executions to Supabase.
    Uses actual task names from YAML files and creates task definitions if needed.
    """
    if not task_executions:
        logger.info("No task executions to save.")
        return 0

    # Check if Supabase client is enabled
    if not supabase_client.enabled:
        logger.warning("Supabase client not enabled - skipping task execution save")
        return 0

    try:
        # 1. Get all task definitions from the database
        task_def_table = supabase_client.table('task_definitions')
        if not task_def_table:
            logger.error("Failed to get task_definitions table - client not properly initialized")
            return 0
        
        response = task_def_table.select('id, task_name').execute()
        if response.data is None:
            logger.error("Failed to fetch task definitions from Supabase.")
            return 0
        
        task_def_map = {item['task_name']: item['id'] for item in response.data}
        logger.info(f"Loaded {len(task_def_map)} task definitions from DB.")

        # 2. Create missing task definitions dynamically
        missing_tasks = []
        for task_exec in task_executions:
            task_name = task_exec.get('task_name')
            if task_name and task_name not in task_def_map:
                missing_tasks.append(task_name)
        
        if missing_tasks:
            logger.info(f"Creating {len(missing_tasks)} missing task definitions: {missing_tasks}")
            new_task_definitions = []
            for task_name in missing_tasks:
                new_task_def = {
                    'task_name': task_name,
                    'task_display_name': task_name.replace('_', ' ').title(),
                    'task_category': 'analysis',  # Default category
                    'description': f'Task: {task_name}',
                    'is_binary_gate': False,
                    'can_block_workflow': False
                }
                new_task_definitions.append(new_task_def)
            
            # Insert new task definitions
            insert_response = task_def_table.insert(new_task_definitions).execute()
            if insert_response.data:
                # Update the task_def_map with new entries
                for new_task in insert_response.data:
                    task_def_map[new_task['task_name']] = new_task['id']
                logger.info(f"✅ Created {len(insert_response.data)} new task definitions")
            else:
                logger.warning("Failed to create new task definitions")

        # 3. Partition the workflow-level API call log into per-task logs
        task_names_ordered = [te.get('task_name') for te in task_executions]
        per_task_calls = partition_api_calls_by_task(
            api_call_log or [], task_names_ordered, TASK_METADATA
        )
        logger.info(
            "Partitioned %d workflow API calls across %d tasks: %s",
            len(api_call_log or []),
            len(task_executions),
            {name: len(calls) for name, calls in per_task_calls.items() if calls},
        )

        # 4. Prepare records for insertion
        records_to_insert = []
        for i, task_exec in enumerate(task_executions):
            task_name = task_exec.get('task_name')
            task_definition_id = task_def_map.get(task_name)

            logger.info(f"Saving task execution {i+1}/{len(task_executions)}: {task_name}")

            if not task_definition_id:
                logger.warning(f"No task_definition_id mapping found for task: {task_name} - storing with NULL task_definition_id")

            logger.info(f"Mapped {task_name} to task_definition_id: {task_definition_id}")

            # Get the full output for storage
            full_output = task_exec.get('full_output', 'No raw output available.')

            # Per-task API call log and summary (not the shared workflow total)
            task_api_calls = per_task_calls.get(task_name, [])
            task_tool_summary = compute_tool_execution_summary(task_api_calls)

            record = {
                'id': str(uuid.uuid4()),
                'tld_string_id': tld_string_id,
                'task_definition_id': task_definition_id,
                'workflow_id': workflow_execution_id,
                'task_name': task_name,  # Store the actual task name for reference
                'status': 'COMPLETED',
                'result_status': task_exec.get('result_status', 'UNKNOWN'),
                'result_data': {
                    "summary": task_exec.get('summary', 'No summary available.'),
                    "full_output": full_output,
                    "output": full_output,  # Client compatibility - EvaluationReportViewer looks for this
                    "raw_output": full_output,  # Client compatibility - StringEvaluation looks for this
                    "workflow_context": task_exec.get('workflow_type', workflow_name),  # Store workflow context
                    "evaluation_metadata": {
                        "tld_string": tld_string,
                        "use_case": use_case,
                        "task_index": i + 1,
                        "total_tasks": len(task_executions)
                    },
                    "api_call_log": task_api_calls,
                    "tool_execution_summary": task_tool_summary,
                    "trademark_audit_log": (
                        trademark_audit_log or []
                    ) if task_name in ("global_trademark_assessment", "deep_research_legal_assessment") else []
                },
                'agent_name': task_exec.get('agent'),
                'started_at': task_exec.get('started_at'),
                'completed_at': task_exec.get('completed_at'),
                'execution_time_seconds': task_exec.get('execution_time_seconds'),
                'confidence_score': _compute_confidence_score(
                    task_exec.get('result_status', 'UNKNOWN'),
                    task_tool_summary,
                ),
            }
            logger.info(f"Prepared task execution: {task_name} -> {record['result_status']} (ID: {record['id']}, api_calls: {len(task_api_calls)})")
            records_to_insert.append(record)

        # 5. Batch insert the records
        if records_to_insert:
            # Get task executions table
            task_exec_table = supabase_client.table('task_executions')
            if not task_exec_table:
                logger.error("Failed to get task_executions table - client not properly initialized")
                return 0
            
            # Insert task execution records
            response = task_exec_table.insert(records_to_insert).execute()
            
            if response.data:
                saved_count = len(response.data)
                logger.info(f"✅ Successfully saved {saved_count}/{len(records_to_insert)} task executions to database.")
                logger.info(f"📋 Task execution IDs: {[r['id'] for r in response.data[:3]]}{'...' if len(response.data) > 3 else ''}")
                return saved_count
            else:
                logger.error(f"❌ Database insert returned no data. Response: {response}")
                return 0

    except APIError as e:
        logger.error(f"❌ Supabase API Error storing task executions: {e.message}")
        logger.error(f"Details: {e.details if hasattr(e, 'details') else 'No additional details'}")
        logger.error(f"Records being inserted: {len(records_to_insert) if 'records_to_insert' in locals() else 'Unknown'}")
    except Exception as e:
        logger.error(f"❌ Unexpected error storing task executions: {e}", exc_info=True)
        logger.error(f"Records being inserted: {len(records_to_insert) if 'records_to_insert' in locals() else 'Unknown'}")
        if 'records_to_insert' in locals():
            logger.error(f"Sample record: {records_to_insert[0] if records_to_insert else 'No records'}")
        
    return 0


def _compute_confidence_score(result_status: str, tool_summary: Dict[str, Any]) -> float:
    """Derive a confidence score (0.0–1.0) from data quality signals.

    Combines:
    - Data reliability from tool execution (FULL/PARTIAL/NONE)
    - Result status certainty (definitive statuses score higher)
    - Search bypass penalty (model-knowledge-only results are less reliable)
    """
    score = 0.5  # baseline

    # Boost/penalty based on tool data reliability
    overall = tool_summary.get("overall", {})
    reliability = overall.get("data_reliability", "NONE")
    if reliability == "FULL":
        score += 0.3
    elif reliability == "PARTIAL":
        score += 0.15
    elif reliability == "NONE":
        score -= 0.1

    # Boost for definitive result statuses (even HIGH_RISK is a confident finding)
    if result_status in ("CLEAR", "PASS", "LOW_RISK"):
        score += 0.1
    elif result_status in ("FAIL", "HIGH_RISK", "CRITICAL"):
        score += 0.05
    elif result_status in ("REVIEW_REQUIRED",):
        score -= 0.15

    # Penalty if API calls all failed
    total_calls = overall.get("total_api_calls", 0)
    successful_calls = overall.get("total_successful", 0)
    if total_calls > 0 and successful_calls == 0:
        score -= 0.2

    return max(0.0, min(1.0, round(score, 2)))


def _classify_result_status(raw_output: str) -> str:
    """
    Classify task result_status from raw output text.

    Checks specific patterns in priority order. Defaults to REVIEW_REQUIRED
    for ambiguous cases rather than silently marking everything CLEAR.

    Valid DB values: PASS, FAIL, BLOCKED, REVIEW_REQUIRED, CLEAR,
                     LOW_RISK, MEDIUM_RISK, HIGH_RISK
    """
    if not raw_output:
        return 'FAIL'

    text = raw_output.upper()

    # 1. Explicit tool/task failure phrases (highest priority)
    failure_phrases = [
        'CANNOT FULFILL THIS REQUEST',
        'UNABLE TO COMPLETE',
        'UNABLE TO PERFORM',
        'COULD NOT BE COMPLETED',
        'TOOL EXECUTION FAILED',
        'ANALYSIS COULD NOT',
        'ERROR PREVENTED',
        'I AM SORRY, BUT I CANNOT',
        'I DO NOT HAVE ACCESS TO TOOLS',
        'I DO NOT HAVE THE FUNCTIONALITY',
        "'NONETYPE' OBJECT",
        'COULD NOT COMPLETE',          # agent: "could not complete the analysis"
        'ENCOUNTERED AN ERROR',        # agent: "encountered an error"
        'WAS UNABLE TO',               # agent: "was unable to complete"
        'ANALYSIS FAILED',             # agent: "the enhanced analysis failed"
        'I AM UNABLE TO PROVIDE',      # agent: "I am unable to provide a report"
        'COULD NOT FULFILL',           # agent: "I cannot fulfill the request"
        'THEREFORE, I CANNOT',         # agent: "Therefore, I cannot: 1. Identify..."
        'I CANNOT PROVIDE',            # agent: "I cannot provide a comprehensive report"
    ]
    if any(phrase in text for phrase in failure_phrases):
        return 'FAIL'

    # 2. Specific risk levels (before generic PASS/FAIL to avoid substring issues)
    if 'HIGH_RISK' in text or 'HIGH RISK' in text:
        return 'HIGH_RISK'
    if 'MEDIUM_RISK' in text or 'MEDIUM RISK' in text:
        return 'MEDIUM_RISK'
    if 'LOW_RISK' in text or 'LOW RISK' in text:
        return 'LOW_RISK'

    # 3. Explicit blocked status
    if 'BLOCKED' in text:
        return 'BLOCKED'

    # 4. Degraded/ambiguous results that need human review
    review_phrases = [
        'EXPERT REVIEW IS RECOMMENDED',
        'EXPERT REVIEW REQUIRED',
        'MANUAL ASSESSMENT',
        'RISK LEVEL: UNKNOWN',
        'ANALYSIS STATUS: FAILED',
        'SEARCH BYPASSED',
        'MODEL KNOWLEDGE ONLY',
    ]
    if any(phrase in text for phrase in review_phrases):
        return 'REVIEW_REQUIRED'

    # 5. Clear success indicators (specific phrases to avoid false matches)
    if 'RISK LEVEL: CLEAR' in text or 'OVERALL RISK LEVEL: CLEAR' in text:
        return 'CLEAR'
    if 'RECOMMENDATION: PROCEED' in text or 'RECOMMENDATION:** PROCEED' in text:
        return 'CLEAR'

    # 6. Contextual FAIL (not as substring of other words)
    fail_contexts = ['STATUS: FAIL', 'RESULT: FAIL', 'ASSESSMENT: FAIL', ': FAILED']
    if any(ctx in text for ctx in fail_contexts):
        return 'FAIL'

    # 7. Contextual PASS (not as substring of "bypass", "compass", etc.)
    pass_contexts = ['STATUS: PASS', 'RESULT: PASS', 'ASSESSMENT: PASS']
    if any(ctx in text for ctx in pass_contexts):
        return 'PASS'

    # 8. Substantive output without error language → CLEAR
    if len(raw_output) > 200:
        return 'CLEAR'

    return 'REVIEW_REQUIRED'


def extract_task_results(crew, workflow_type: str,
                         workflow_start_time: float = None,
                         workflow_execution_time: float = None) -> List[Dict[str, Any]]:
    """
    Extract structured task results from a completed crew execution.
    Uses actual task names from YAML files instead of parsing descriptions.
    """
    task_executions = []
    if not crew or not crew.tasks:
        logger.warning("Crew or crew.tasks not found, cannot extract results.")
        return task_executions

    logger.info(f"🔍 Extracting results from {len(crew.tasks)} tasks for workflow '{workflow_type}'")

    task_count = len(crew.tasks)
    completed_at = datetime.now().isoformat()

    for i, task in enumerate(crew.tasks):
        task_output = task.output
        if not task_output:
            logger.warning(f"Task {i+1}/{task_count} '{getattr(task, '_task_name', 'unknown')}' has no output.")
            continue

        # Get the actual task name from the YAML file (set by CrewBuilder)
        task_name = getattr(task, '_task_name', None)
        if not task_name:
            # Fallback to extracting from description if _task_name wasn't set
            task_name = task.description.split('\n')[0].strip()
            logger.warning(f"Task {i+1}/{task_count} missing _task_name attribute, using fallback: {task_name}")
        else:
            logger.info(f"📋 Processing task {i+1}/{task_count}: '{task_name}'")

        result_status = 'CLEAR'
        summary = 'Task finished.'
        full_output = task_output.raw_output if hasattr(task_output, 'raw_output') else str(task_output)

        # Attempt to parse structured output if available
        if hasattr(task_output, 'pydantic') and task_output.pydantic:
            structured_output = task_output.pydantic
            if hasattr(structured_output, 'risk_level'):
                result_status = structured_output.risk_level.upper()
            elif hasattr(structured_output, 'is_compliant'):
                result_status = 'PASS' if structured_output.is_compliant else 'FAIL'
            summary = task_output.description or f"{task_name} completed"

        elif hasattr(task_output, 'raw_output'):
            result_status = _classify_result_status(task_output.raw_output)
            summary = task_output.description or f"Completed: {task_name}"

        logger.info(f"  -> {task_name}: result_status={result_status}")

        task_exec_data = {
            "task_name": task_name,
            "agent": task.agent.role if task.agent else "Unknown",
            "result_status": result_status,
            "summary": summary,
            "full_output": full_output,
            "started_at": None,
            "completed_at": completed_at,
            "execution_time_seconds": None,
        }
        task_executions.append(task_exec_data)

    logger.info(f"Extracted {len(task_executions)} task results for workflow '{workflow_type}'.")
    return task_executions

# Add explicit route handlers for common React Router paths to ensure they serve index.html
@app.get("/login")
@app.get("/signup") 
@app.get("/forgot-password")
@app.get("/reset-password")
@app.get("/dashboard")
@app.get("/evaluation/{path:path}")
@app.get("/applicants")
@app.get("/applications")
@app.get("/applications/{path:path}")
async def serve_react_routes():
    """Serve React app for common routes"""
    client_dist_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "client", "dist")
    index_path = os.path.join(client_dist_path, "index.html")
    
    if os.path.exists(index_path):
        with open(index_path, 'r', encoding='utf-8') as f:
            return Response(content=f.read(), media_type='text/html')
    else:
        raise HTTPException(status_code=404, detail="Frontend not found")

@app.head("/")
async def root_head():
    """Root HEAD endpoint for Render health checks"""
    return Response(status_code=200)

@app.get("/api")
async def api_info():
    """API information endpoint"""
    return {
        "service": "CrewAI TLD Evaluation Service",
        "version": "2.0.0",
        "status": "healthy",
        "frontend": "Available at /",
        "api": "Available at /api/*",
        "docs": "Available at /docs",
        "health": "Available at /health"
    }

@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    logger.info("Health check endpoint called")
    return {
        "status": "healthy",
        "service": "CrewAI TLD Evaluation Service (Synchronous)",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0"
    }

@app.post("/debug/test-response")
async def test_response_model():
    """Debug endpoint to test AutoEvaluationResponse model"""
    try:
        response = AutoEvaluationResponse(
            evaluation_id="test-id",
            tld_string="test",
            workflows_queued=["technical_risk_assessment", "legal_risk_assessment", "policy_safeguard_review"],
            queue_position=1,
            estimated_completion_minutes=18,
            status="CREATED",
            message="Test response",
            evaluation={"id": "test-id", "tld_string": "test"}
        )
        return {"success": True, "response": response}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/workflows")
async def list_workflows():
    """List all available workflows from configuration"""
    try:
        builder = CrewBuilder()
        workflows = builder.get_available_workflows()
        return JSONResponse(content=workflows)
    except Exception as e:
        logger.error(f"Error listing workflows: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load workflow configurations.")

@app.get("/api/evaluations/check/{tld_string}")
async def check_tld_string_exists(tld_string: str):
    """
    Simple check if a TLD string already exists
    Returns basic true/false like other validation checks
    """
    try:
        # Clean the TLD string (remove dots, convert to lowercase)
        cleaned_tld = tld_string.lower().lstrip('.')
        
        # Load existing strings from JSON file
        import json
        import os
        
        strings_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'existing_tld_strings.json')
        
        try:
            if os.path.exists(strings_file):
                with open(strings_file, 'r') as f:
                    existing_strings = json.load(f)
            else:
                existing_strings = []
        except Exception as e:
            logger.warning(f"Could not load existing strings file: {e}")
            existing_strings = []
        
        # Simple check
        exists = cleaned_tld in existing_strings
        
        return {
            "exists": exists,
            "tld_string": cleaned_tld
        }
            
    except Exception as e:
        logger.error(f"Error checking TLD string {tld_string}: {e}")
        return {
            "exists": False,
            "tld_string": tld_string.lower().lstrip('.'),
            "error": "Could not verify string"
        }

@app.get("/api/server-status")
async def get_server_status_endpoint():
    """Get simple server status - busy or available"""
    try:
        status = await get_server_status()
        
        # Format response for client-side queue management
        response = {
            "available": status.get("available", False),
            "running_count": status.get("running_count", 0),
            "currently_running": [
                {
                    "id": item["id"],
                    "tld_string": item["tld_string"],
                    "use_case": item.get("use_case", ""),
                    "started_at": item.get("created_at"),
                    "status": item.get("overall_status")
                }
                for item in status.get("running", [])
            ] if status.get("running") else []
        }
        
        return JSONResponse(content=response)
        
    except Exception as e:
        logger.error(f"Error getting server status: {e}")
        return JSONResponse(content={"error": str(e), "available": False}, status_code=500)


class AutoEvaluationRequest(BaseModel):
    tld_string: str
    use_case: Optional[str] = "General purpose TLD evaluation"
    enable_auto_execution: bool = True
    string_type: Optional[str] = "primary"


class AutoEvaluationResponse(BaseModel):
    evaluation_id: str
    tld_string: str
    workflows_queued: List[str]
    queue_position: int
    estimated_completion_minutes: int
    status: str
    message: str
    evaluation: Optional[Dict[str, Any]] = None

class ChatMessage(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    success: bool
    response: str
    sources: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    error: Optional[str] = None



@app.post("/api/evaluations/auto-submit")
async def auto_submit_evaluation(request: AutoEvaluationRequest):
    """
    Submit a TLD evaluation with auto-execution of all workflows
    This creates the evaluation and automatically runs all three workflows sequentially.
    """
    try:
        tld_string = request.tld_string
        use_case = request.use_case

        logger.info(f"Auto-submitting evaluation for {tld_string}")

        # Check server availability BEFORE creating any DB entries
        if request.enable_auto_execution:
            server_status = await get_server_status()

            if not server_status.get("available", False):
                currently_running = server_status.get("running", [])
                running_string = currently_running[0]["tld_string"] if currently_running else "unknown"
                logger.info(f"Server busy (running .{running_string}), rejecting .{tld_string} with 409")
                raise HTTPException(
                    status_code=409,
                    detail=f"Server is currently processing .{running_string}. Please wait and try again."
                )

        # Create TLD string entry in database using working client
        app_store = TldApplicationStore()
        evaluation_id = None

        # Try to get existing TLD string
        result = app_store.supabase.table('tld_strings').select('id').eq('tld_string', tld_string).execute()

        if result.data and len(result.data) > 0:
            evaluation_id = result.data[0]['id']
            logger.info(f"Using existing TLD string ID: {evaluation_id}")
        else:
            # Create new TLD string entry - Clean logical flow
            tld_data = {
                'tld_string': tld_string,
                'use_case': use_case,
                'string_type': request.string_type or 'primary'
                # Database defaults handle:
                # - has_evaluation: FALSE
                # - has_application_draft: FALSE
                # - overall_status: 'not_started'
            }
            result = app_store.supabase.table('tld_strings').insert(tld_data).execute()
            if result.data:
                evaluation_id = result.data[0]['id']
                logger.info(f"✅ Created TLD entry: {evaluation_id}")

                # Add to existing strings JSON file
                try:
                    _add_string_to_json_file(tld_string)
                except Exception as e:
                    logger.warning(f"Could not add string to JSON file: {e}")
            else:
                logger.error(f"❌ Insert failed: {result}")
                raise HTTPException(status_code=500, detail="Failed to create TLD entry")

        logger.info(f"✅ About to generate response for {tld_string}, auto_execution={request.enable_auto_execution}")

        # Use the same response format for both paths to fix the 500 error
        workflows_queued = ["technical_risk_assessment", "legal_risk_assessment", "policy_safeguard_review"] if request.enable_auto_execution else []
        message = f"String '{tld_string}' created successfully. Workflows starting." if request.enable_auto_execution else f"Evaluation created for '{tld_string}'. Auto-execution disabled."

        logger.info(f"✅ Response data prepared: workflows_queued={len(workflows_queued)}, message='{message[:50]}...')")

        # Server is available (checked above) - start workflows
        if request.enable_auto_execution and evaluation_id:
            
            # Server is available - start immediately
            logger.info(f"🚀 Server available - starting {tld_string} immediately")
            
            try:
                app_store.supabase.table('tld_strings').update({
                    'overall_status': 'RUNNING'
                }).eq('id', evaluation_id).execute()
                logger.info(f"Updated status to 'RUNNING' for {tld_string}")
            except Exception as e:
                logger.error(f"Failed to update status to RUNNING: {e}")
            
            # Start workflows with timeout
            async def run_evaluation_with_timeout():
                try:
                    await asyncio.wait_for(
                        run_sequential_workflows(evaluation_id, tld_string, use_case),
                        timeout=2700  # 45 minutes
                    )
                    # Status is set by run_sequential_workflows based on actual task results
                    logger.info(f"✅ Evaluation finished for {tld_string}")
                    
                except asyncio.TimeoutError:
                    logger.error(f"⏰ Evaluation timed out for {tld_string}")
                    try:
                        app_store.supabase.table('tld_strings').update({
                            'overall_status': 'FAILED'
                        }).eq('id', evaluation_id).execute()
                    except Exception as e:
                        logger.error(f"Failed to update status to FAILED (timeout): {e}")
                        
                except Exception as e:
                    logger.error(f"❌ Evaluation failed for {tld_string}: {e}")
                    try:
                        app_store.supabase.table('tld_strings').update({
                            'overall_status': 'FAILED'
                        }).eq('id', evaluation_id).execute()
                    except Exception as e:
                        logger.error(f"Failed to update status to FAILED: {e}")
            
            asyncio.create_task(run_evaluation_with_timeout())
            
            return {
                "evaluation_id": evaluation_id,
                "tld_string": tld_string,
                "workflows_queued": workflows_queued,
                "status": "RUNNING",
                "message": f"Evaluation started for .{tld_string}",
                "evaluation": {"id": evaluation_id, "tld_string": tld_string}
            }
        
        # No auto-execution requested
        return {
            "evaluation_id": evaluation_id,
            "tld_string": tld_string,
            "workflows_queued": [],
            "queue_position": 0,
            "estimated_completion_minutes": 0,
            "status": "CREATED",
            "message": f"Evaluation created for .{tld_string}. Auto-execution disabled.",
            "evaluation": {"id": evaluation_id, "tld_string": tld_string}
        }

    except APIError as e:
        logger.error(f"Supabase API Error in auto-submit: {e.message}")
        raise HTTPException(status_code=500, detail=f"Database error: {e.message}")
    except HTTPException:
        # Preserve intended status codes (e.g. 409 "server busy") instead of
        # masking them as 500 via the generic Exception handler below.
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred in auto-submit: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal server error occurred.")

async def generate_automatic_report(tld_string_id: str, tld_string: str, supabase):
    """
    Automatically generate a Gemini report after all workflows complete.
    Fetches all task executions and generates a comprehensive report.
    """
    try:
        # Get all task executions for this TLD
        task_response = supabase.table('task_executions').select('*').eq('tld_string_id', tld_string_id).execute()
        task_executions = task_response.data if task_response.data else []
        
        if not task_executions:
            logger.warning(f"No task executions found for {tld_string} - skipping report generation")
            return
        
        logger.info(f"📊 Found {len(task_executions)} task executions for report generation")
        
        # Prepare evaluation data in the format expected by the report generator
        evaluation_data = {
            'tld_string': tld_string,
            'use_case': 'Auto-generated report',
            'task_executions': []
        }
        
        # Convert task executions to the expected format
        for task in task_executions:
            task_data = {
                'task_name': task.get('task_name', 'Unknown'),
                'workflow_type': 'auto_workflow',
                'status': task.get('status', 'Unknown'),
                'result_status': task.get('result_status', 'Unknown'),
                'output_summary': task.get('result_data', {}).get('summary', '')[:500] if task.get('result_data') else '',
                'completed_at': task.get('completed_at', ''),
                'full_output': str(task.get('result_data', ''))[:1000]  # Limit output size
            }
            evaluation_data['task_executions'].append(task_data)
        
        # Call the report generation logic directly
        report_html = await generate_report_content(tld_string, evaluation_data)
        
        if report_html:
            # Parse risk classification from the report
            risk_data = parse_html_risk_assessment(report_html)
            
            # Store the report in the tld_strings.generated_report field (proper method)
            await save_report_to_database(tld_string, report_html, 'gemini-2.5-pro', risk_data)
            logger.info(f"✅ Automatic report saved to database for {tld_string}")
            
            # Verify the report was saved
            try:
                verify_result = supabase.table('tld_strings').select('generated_report').eq('tld_string', tld_string).execute()
                if verify_result.data and verify_result.data[0]['generated_report']:
                    logger.info(f"✅ Verified report exists in database for {tld_string}")
                else:
                    logger.warning(f"⚠️ Report not found in database after save for {tld_string}")
            except Exception as verify_error:
                logger.error(f"❌ Failed to verify report save for {tld_string}: {verify_error}")
        else:
            logger.warning(f"❌ No report content generated for {tld_string}")
            
    except Exception as e:
        logger.error(f"❌ Error in generate_automatic_report for {tld_string}: {e}", exc_info=True)
        raise

async def generate_report_content(tld_string: str, evaluation_data: dict, retry_count: int = 0) -> str:
    """
    Generate report content using Gemini API with Google Cloud key (higher rate limits).
    OpenAI fallback if Gemini fails.
    """
    MAX_RETRIES = 2
    
    try:
        if retry_count > MAX_RETRIES:
            logger.error(f"❌ Max retries ({MAX_RETRIES}) exceeded for report generation")
            return None
            
        logger.info(f"🤖 Generating report for .{tld_string} (attempt {retry_count + 1}/{MAX_RETRIES + 1})")
        
        # Load Gemini API key (env populated by ensure_env_secrets at startup)
        api_key = os.getenv("GEMINI_API_KEY") or load_api_key("gemini")
        if not api_key:
            logger.error("❌ No Gemini API key found - cannot generate reports")
            return None
        
        # Build evaluation content for Gemini
        task_executions = evaluation_data.get('task_executions', [])
        report_prompt = create_personalized_gemini_prompt(tld_string, task_executions)
        
        # Call Gemini API with Google Cloud key
        gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={api_key}"
        gemini_request = {
            "contents": [{
                "parts": [{
                    "text": report_prompt
                }]
            }],
            "generationConfig": {
                "temperature": 0.3,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 8192,
                "candidateCount": 1
            }
        }
        
        async with httpx.AsyncClient() as client:
            gemini_response = await client.post(
                gemini_url, 
                json=gemini_request,
                timeout=60.0
            )
        
        if gemini_response.status_code != 200:
            logger.error(f"Gemini API error: {gemini_response.status_code} - {gemini_response.text}")
            
            # Retry for recoverable errors
            if gemini_response.status_code in [429, 500, 502, 503, 504] and retry_count < MAX_RETRIES:
                wait_time = (2 ** retry_count) * 1
                logger.info(f"⏳ Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
                return await generate_report_content(tld_string, evaluation_data, retry_count + 1)
            
            # Fall back to OpenAI
            logger.warning("🔄 Switching to OpenAI fallback")
            return await generate_report_with_openai(tld_string, evaluation_data)
        
        gemini_data = gemini_response.json()
        
        if 'candidates' not in gemini_data or not gemini_data['candidates']:
            logger.error("No candidates in Gemini response")
            return await generate_report_with_openai(tld_string, evaluation_data)
        
        candidate = gemini_data['candidates'][0]
        if 'content' not in candidate:
            logger.error("No content in Gemini candidate")
            return await generate_report_with_openai(tld_string, evaluation_data)
            
        content = candidate['content']
        if 'parts' not in content or not content['parts']:
            logger.error("No parts in Gemini content - likely safety filter")
            return await generate_report_with_openai(tld_string, evaluation_data)
            
        response_text = content['parts'][0]['text']
        logger.info(f"✅ Received Gemini response: {len(response_text)} characters")
        
        # Clean up markdown code blocks
        if response_text.startswith('```markdown'):
            response_text = response_text.replace('```markdown', '').replace('```', '').strip()
        elif response_text.startswith('```'):
            response_text = response_text.replace('```', '').strip()
        
        return response_text
        
    except Exception as e:
        logger.error(f"❌ Error generating report content: {e}", exc_info=True)
        if retry_count < MAX_RETRIES:
            await asyncio.sleep(1)
            return await generate_report_content(tld_string, evaluation_data, retry_count + 1)
        else:
            logger.warning("🔄 Error - switching to OpenAI fallback")
            return await generate_report_with_openai(tld_string, evaluation_data)

async def generate_report_with_openai(tld_string: str, evaluation_data: dict) -> str:
    """
    Generate report content using OpenAI GPT-4o as fallback.
    """
    try:
        # Load OpenAI API key (env populated by ensure_env_secrets at startup)
        openai_api_key = os.getenv("OPENAI_API_KEY") or load_api_key("openai")
        
        if not openai_api_key:
            logger.error("❌ No OpenAI API key found - cannot use fallback")
            return "# Report Generation Failed\n\nBoth Gemini and OpenAI APIs are unavailable. Please try again later."
        
        logger.info("🔄 Using OpenAI GPT-4o as fallback for report generation")
        
        # Use the same personalized prompt template as Gemini for consistency
        task_executions = evaluation_data.get('task_executions', [])
        
        # Use the personalized prompt template with proper CrewAI output injection
        report_prompt = create_personalized_gemini_prompt(tld_string, task_executions)
        
        # Call OpenAI API
        openai_url = "https://api.openai.com/v1/chat/completions"
        openai_request = {
            "model": "gpt-4o",
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert TLD investment analyst. Generate comprehensive, professional reports based on evaluation data."
                },
                {
                    "role": "user", 
                    "content": report_prompt
                }
            ],
            "max_tokens": 4000,
            "temperature": 0.3
        }
        
        headers = {
            "Authorization": f"Bearer {openai_api_key}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            openai_response = await client.post(
                openai_url,
                json=openai_request,
                headers=headers,
                timeout=60.0
            )
        
        if openai_response.status_code != 200:
            logger.error(f"OpenAI API error: {openai_response.status_code} - {openai_response.text}")
            return "# Report Generation Failed\n\nBoth Gemini and OpenAI APIs failed. Please try again later."
        
        openai_data = openai_response.json()
        
        if 'choices' not in openai_data or not openai_data['choices']:
            logger.error("No choices in OpenAI response")
            return "# Report Generation Failed\n\nOpenAI API returned no content."
        
        response_text = openai_data['choices'][0]['message']['content']
        logger.info(f"✅ OpenAI fallback successful: {len(response_text)} characters")
        
        # Add fallback notice
        response_text = f"*Generated using OpenAI GPT-4o (Gemini unavailable)*\n\n{response_text}"
        
        return response_text
        
    except Exception as e:
        logger.error(f"❌ OpenAI fallback failed: {e}", exc_info=True)
        return "# Report Generation Failed\n\nBoth primary and fallback report generation failed. Please try again later."

async def run_sequential_workflows(tld_string_id: str, tld_string: str, use_case: str):
    """
    Run all workflows sequentially in the background.
    Updates database with workflow status and results.
    """
    workflows = [
        "technical_risk_assessment",
        "legal_risk_assessment", 
        "policy_safeguard_review"
    ]
    
    app_store = TldApplicationStore()
    supabase = app_store.supabase
    
    try:
        logger.info(f"🚀 Starting sequential workflows for {tld_string} (ID: {tld_string_id})")
        
        # Verify supabase connection
        if not supabase:
            logger.error("❌ Supabase client not enabled - cannot save workflow results")
            logger.error("❌ Check that SUPABASE_URL and SUPABASE_SERVICE_KEY are set in the environment")
            return
        else:
            logger.info(f"✅ Supabase client enabled and ready for {tld_string}")
            
            # Test database connection
            try:
                test_table = supabase.table('tld_strings')
                if test_table:
                    test_result = test_table.select('id').limit(1).execute()
                    logger.info(f"✅ Database connection test successful, can access tld_strings table")
                else:
                    logger.error("❌ Failed to get table handle from Supabase client")
            except Exception as test_e:
                logger.error(f"❌ Database connection test failed: {test_e}")
        
        for workflow_name in workflows:
            # Update workflow status to running
            try:
                await update_workflow_status(supabase, tld_string_id, workflow_name, "RUNNING")
                logger.info(f"✅ Updated workflow status to 'RUNNING' for {workflow_name}")
            except Exception as e:
                logger.error(f"❌ Failed to update workflow status to 'RUNNING': {e}")

            try:
                logger.info(f"🔄 Executing {workflow_name} for {tld_string}")

                # Execute workflow - CRASH PROTECTED
                import os
                config_dir = os.path.join(os.path.dirname(__file__), "evaluation", "config")

                # CRASH PREVENTION: Wrap crew building in try-catch
                try:
                    crew = build_crew_for_workflow(workflow_name, {
                        "tld_string": tld_string,
                        "use_case": use_case
                    }, config_dir=config_dir)
                    logger.info(f"🔒 Built crew for {workflow_name} - {len(crew.agents) if crew and crew.agents else 0} agents")
                except Exception as crew_error:
                    logger.error(f"🛡️ Failed to build crew for {workflow_name}: {crew_error}")
                    raise  # Re-raise to trigger workflow failure handling

                # CRASH PREVENTION: Wrap execution with timeout and retry
                import signal
                import time
                start_time = time.time()

                try:
                    logger.info(f"🚀 Executing {workflow_name} with {len(crew.tasks) if crew and crew.tasks else 0} tasks")

                    clear_api_call_log()
                    results = kickoff_and_get_results(crew, {
                        "tld_string": tld_string,
                        "use_case": use_case
                    })

                    execution_time = time.time() - start_time
                    logger.info(f"✅ Workflow {workflow_name} completed successfully in {execution_time:.1f}s")
                    
                except Exception as execution_error:
                    execution_time = time.time() - start_time
                    logger.error(f"🛡️ Workflow execution failed for {workflow_name} after {execution_time:.1f}s: {execution_error}")
                    raise  # Re-raise to trigger workflow failure handling
                
                # Extract and save task results
                try:
                    task_executions = extract_task_results(
                        crew, workflow_name,
                        workflow_start_time=start_time,
                        workflow_execution_time=execution_time
                    )
                    logger.info(f"📊 Extracted {len(task_executions)} task results from {workflow_name}")

                    # Collect API call logs accumulated during tool execution
                    api_call_log = get_api_call_log()
                    trademark_audit_log = get_trademark_audit_log()
                    tool_execution_summary = compute_tool_execution_summary(api_call_log)
                    logger.info(
                        f"📡 API call log: {tool_execution_summary.get('overall', {}).get('total_api_calls', 0)} calls, "
                        f"reliability={tool_execution_summary.get('overall', {}).get('data_reliability', 'N/A')}"
                    )
                    if trademark_audit_log:
                        logger.info(f"📋 Trademark audit: {len(trademark_audit_log)} Brave results logged")

                    if task_executions:
                        # Generate a proper UUID for the workflow execution
                        workflow_execution_id = str(uuid.uuid4())
                        num_saved = save_task_executions(
                            supabase,
                            tld_string_id,
                            workflow_execution_id,
                            task_executions,
                            workflow_name,
                            tld_string,
                            use_case,
                            api_call_log=api_call_log,
                            tool_execution_summary=tool_execution_summary,
                            trademark_audit_log=trademark_audit_log if trademark_audit_log else None
                        )
                        logger.info(f"💾 Saved {num_saved}/{len(task_executions)} task results for {workflow_name}")
                    else:
                        logger.warning(f"⚠️ No task executions extracted for {workflow_name}")
                        
                except Exception as e:
                    logger.error(f"❌ Failed to save task results for {workflow_name}: {e}", exc_info=True)
                
                # Update workflow status to completed
                try:
                    await update_workflow_status(supabase, tld_string_id, workflow_name, "COMPLETED")
                    logger.info(f"✅ Updated workflow status to 'COMPLETED' for {workflow_name}")
                except Exception as e:
                    logger.error(f"❌ Failed to update workflow status to 'COMPLETED': {e}")
                
                logger.info(f"✅ Completed {workflow_name} for {tld_string}")

            except Exception as e:
                logger.error(f"❌ Failed {workflow_name} for {tld_string}: {e}", exc_info=True)
                try:
                    await update_workflow_status(supabase, tld_string_id, workflow_name, "FAILED", str(e))
                    logger.info(f"✅ Updated workflow status to 'FAILED' for {workflow_name}")
                except Exception as status_error:
                    logger.error(f"❌ Failed to update workflow status to 'FAILED': {status_error}")
                # Continue with next workflow instead of breaking
                continue

        # Check if tasks actually ran — fail early if nothing was saved.
        # If the check itself errors we don't know the count; continue rather
        # than abort the run on a transient database error.
        task_count = None
        try:
            task_result = supabase.table('task_executions').select('id').eq('tld_string_id', tld_string_id).execute()
            task_count = len(task_result.data) if task_result.data else 0

            if task_count == 0:
                supabase.table('tld_strings').update({
                    'overall_status': 'FAILED'
                }).eq('id', tld_string_id).execute()
                logger.error(f"❌ No task executions saved for {tld_string} — marking as FAILED")
                return
        except Exception as e:
            logger.error(f"❌ Failed to check task executions: {e}")

        logger.info(f"🎉 All workflows completed for {tld_string} ({task_count if task_count is not None else 'unknown'} tasks)")

        # Generate report BEFORE marking COMPLETED so server stays "busy"
        # and the frontend won't auto-submit the next string until report is done
        try:
            logger.info(f"📊 Starting automatic report generation for {tld_string}")
            await generate_automatic_report(tld_string_id, tld_string, supabase)
            logger.info(f"✅ Automatic report generation completed for {tld_string}")
        except Exception as report_error:
            logger.error(f"❌ Failed to generate automatic report for {tld_string}: {report_error}", exc_info=True)

        # NOW mark as COMPLETED — server becomes available for next string
        try:
            completion_data = {
                'overall_status': 'COMPLETED',
                'completed_at': datetime.now().isoformat()
            }
            supabase.table('tld_strings').update(completion_data).eq('id', tld_string_id).execute()
            logger.info(f"✅ Marked evaluation complete for {tld_string}")
        except Exception as e:
            logger.error(f"❌ Failed to update evaluation completion: {e}")
        
    except Exception as e:
        logger.error(f"❌ Critical error in sequential workflows for {tld_string}: {e}", exc_info=True)
        # Update overall status to failed
        try:
            supabase.table('tld_strings').update({
                'overall_status': 'FAILED'
            }).eq('id', tld_string_id).execute()
            logger.info(f"✅ Updated overall status to 'FAILED' for {tld_string}")
        except Exception as status_error:
            logger.error(f"❌ Failed to update overall status to 'failed': {status_error}")

async def update_workflow_status(supabase, tld_string_id: str, workflow_name: str, status: str, error_message: str = None):
    """Update or create workflow execution status in database"""
    try:
        # Check if Supabase client is enabled
        if not supabase.enabled:
            logger.warning("Supabase client not enabled - skipping workflow status update")
            return
        
        # Get workflow executions table
        workflow_table = supabase.table('workflow_executions')
        if not workflow_table:
            logger.error("Failed to get workflow_executions table - client not properly initialized")
            return
        
        # Check if workflow execution record exists
        existing = workflow_table.select('id').eq('tld_string_id', tld_string_id).eq('workflow_type', workflow_name).execute()
        
        update_data = {
            'status': status
        }
        
        if status == "RUNNING":
            update_data['started_at'] = datetime.now().isoformat()
        elif status in ["COMPLETED", "FAILED"]:
            update_data['completed_at'] = datetime.now().isoformat()
            
        # Note: error_message column doesn't exist in workflow_executions table
        
        if existing.data:
            # Update existing record
            workflow_table.update(update_data).eq('tld_string_id', tld_string_id).eq('workflow_type', workflow_name).execute()
        else:
            # Create new record
            insert_data = {
                'tld_string_id': tld_string_id,
                'workflow_type': workflow_name,
                **update_data
            }
            workflow_table.insert(insert_data).execute()
            
        logger.debug(f"📝 Updated {workflow_name} status to {status} for TLD {tld_string_id}")
        
    except Exception as e:
        logger.error(f"Failed to update workflow status: {e}")





@app.get("/evaluations/{tld_string_id}/workflows")
async def get_evaluation_workflow_status(tld_string_id: str):
    """Get workflow status for specific TLD evaluation from database"""
    try:
        app_store = TldApplicationStore()
        supabase = app_store.supabase
        
        if not supabase:
            return {
                "success": False,
                "error": "Database not available",
                "tld_string_id": tld_string_id
            }
        
        # Get workflow executions from database
        result = supabase.table('workflow_executions').select('*').eq('tld_string_id', tld_string_id).execute()
        
        workflow_status = {
            "tld_string_id": tld_string_id,
            "workflows": {},
            "all_complete": True,
            "has_failures": False
        }
        
        for execution in result.data:
            workflow_name = execution.get('workflow_type', 'unknown')
            status = execution.get('status', 'unknown')
            
            workflow_status["workflows"][workflow_name] = {
                "status": status,
                "started_at": execution.get('started_at'),
                "completed_at": execution.get('completed_at'),
                "error_message": execution.get('error_message')
            }
            
            if status not in ['COMPLETED', 'FAILED']:
                workflow_status["all_complete"] = False
            if status == 'failed':
                workflow_status["has_failures"] = True
        
        return {
            "success": True,
            "tld_string_id": tld_string_id,
            "workflow_status": workflow_status,
            "server_time": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting workflow status for {tld_string_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get workflow status: {str(e)}")

@app.get("/evaluations/{tld_string}")
async def get_evaluation_by_tld_string(tld_string: str):
    """Retrieve all evaluation data for a given TLD string"""
    app_store = TldApplicationStore()

    try:
        # 1. Get the most recent TLD string record for this name
        tld_response = app_store.supabase.table("tld_strings").select("*").eq("tld_string", tld_string).order("created_at", desc=True).limit(1).execute()
        if not tld_response.data:
            raise HTTPException(status_code=404, detail=f"TLD string '{tld_string}' not found")
        
        tld_data = tld_response.data[0]
        tld_string_id = tld_data['id']

        # 2. Get all task executions for this TLD
        tasks_response = app_store.supabase.table("task_executions").select("*").eq("tld_string_id", tld_string_id).order("created_at", desc=True).execute()
        task_executions = tasks_response.data if tasks_response.data else []

        # 3. Get all workflow executions for this TLD
        workflows = []
        try:
            workflow_response = app_store.supabase.table("workflow_executions").select("*").eq("tld_string_id", tld_string_id).order("started_at", desc=True).execute()
            if workflow_response.data:
                workflows = workflow_response.data
        except APIError as e:
            logger.warning(f"Could not get workflow executions for TLD {tld_string_id}: {e.message}")
        except Exception as e:
            logger.warning(f"An unexpected error occurred while fetching workflow executions for TLD {tld_string_id}: {e}")

        logger.info(f"Retrieved evaluation for .{tld_string} with {len(task_executions)} tasks and {len(workflows)} workflows")

        # Calculate completed and total tasks from actual task executions
        completed_tasks = len([task for task in task_executions if task.get('result_status') in ['SUCCESS', 'CLEAR', 'APPROVED']])
        total_tasks = len(task_executions)

        # 4. Combine into a single response object
        response_data = {
            "id": tld_data['id'],
            "tld_string": tld_data['tld_string'],
            "use_case": tld_data['use_case'],
            "created_at": tld_data['created_at'],
            "updated_at": tld_data['updated_at'],
            "status": tld_data.get('overall_status', 'not_started'),  # Add status field for frontend compatibility
            "overall_status": tld_data.get('overall_status', 'not_started'),
            "has_feasibility_study": bool(tld_data.get('generated_report')),
            "generated_report": tld_data.get('generated_report'),  # Include the generated report data
            "completed_tasks": completed_tasks,
            "total_tasks": total_tasks,
            "task_executions": task_executions,
            "workflow_executions": workflows
        }

        return JSONResponse(content=response_data)

    except APIError as e:
        logger.error(f"Database error fetching evaluation for {tld_string}: {e}")
        return JSONResponse(status_code=500, content={"message": f"Database error: {e.message}"})
    except Exception as e:
        logger.error(f"An unexpected error occurred while fetching evaluation for {tld_string}: {e}")
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"message": "An unexpected error occurred"})



# =====================================================
# REPORT GENERATION ENDPOINTS
# =====================================================

@app.post("/reports/generate", response_model=ReportGenerationResponse)
async def generate_comprehensive_report(request: ReportGenerationRequest):
    """
    Generate a comprehensive report for a TLD evaluation after all workflows complete.
    This endpoint is called automatically by the workflow queue system.
    """
    try:
        tld_string = request.tld_string
        evaluation_data = request.evaluation_data
        create_google_doc = request.create_google_doc
        
        logger.info(f"📊 Generating comprehensive report for .{tld_string}")
        
        # Extract task executions from evaluation data
        task_executions = evaluation_data.get('task_executions', [])
        
        if not task_executions:
            raise HTTPException(status_code=400, detail="No evaluation data found")
        
        # Generate report using the proper fallback mechanism
        response_text = await generate_report_content(tld_string, evaluation_data)
        
        if not response_text:
            logger.error("Both Gemini and OpenAI report generation failed")
            raise HTTPException(status_code=500, detail="Report generation failed - both Gemini and OpenAI unavailable")
        
        # Use model's markdown directly to avoid empty-template issues from JSON parsing
        formatted_report = response_text
        
        # Parse risk classification from the report
        risk_data = parse_html_risk_assessment(formatted_report)

        # Optionally create Google Doc (not configured)
        google_doc_url = None
        if create_google_doc:
            logger.info("Google Drive integration not configured - skipping document creation")
        
        # Save to database using unified helper
        try:
            await save_report_to_database(tld_string, formatted_report, 'gemini-2.5-pro', risk_data)
            
            # Auto-export to Google Drive after saving to database
            try:
                google_doc_url = export_report_to_google_drive(tld_string)
                if google_doc_url:
                    logger.info(f"✅ Auto-exported .{tld_string} report to Google Drive: {google_doc_url}")
                else:
                    logger.warning(f"⚠️ Failed to auto-export .{tld_string} to Google Drive")
            except Exception as export_error:
                logger.warning(f"⚠️ Google Drive auto-export failed for .{tld_string}: {export_error}")
                # Don't fail the whole request if Drive export fails
                
        except Exception as e:
            logger.error(f"Failed to save report to database: {e}")
        
        return ReportGenerationResponse(
            success=True,
            report=formatted_report,
            google_doc_url=google_doc_url,
            google_docs_enabled=False,
            risk_score=risk_data.get('risk_score'),
            risk_classification=risk_data.get('risk_classification'),
            risk_level=risk_data.get('risk_level'),
            recommendation=risk_data.get('recommendation')
        )
        
    except Exception as e:
        logger.error(f"Error generating report for {request.tld_string}: {e}")
        logger.error(traceback.format_exc())
        return ReportGenerationResponse(
            success=False,
            report="",
            error=str(e)
        )

@app.post("/reports/batch-export-to-drive")
async def batch_export_reports_to_drive():
    """
    Batch export all existing TLD reports to Google Drive.
    This is a one-time setup endpoint for initial sync.
    """
    try:
        logger.info("🚀 Starting batch export of all reports to Google Drive...")
        
        results = batch_export_all_reports()
        
        success_count = len(results)
        
        return {
            "success": True,
            "exported_count": success_count,
            "exported_reports": results,
            "message": f"Successfully exported {success_count} reports to Google Drive"
        }
        
    except Exception as e:
        logger.error(f"Batch export failed: {e}")
        raise HTTPException(status_code=500, detail=f"Batch export failed: {str(e)}")

@app.delete("/api/evaluations/{evaluation_id}")
async def delete_evaluation(evaluation_id: str):
    """Delete an evaluation and all its associated data"""
    logger.info(f"Attempting to delete evaluation {evaluation_id}")
    app_store = TldApplicationStore()

    try:
        # 1. Verify the evaluation exists and get its data
        tld_string_result = app_store.supabase.table('tld_strings') \
            .select('id, tld_string') \
            .eq('id', evaluation_id) \
            .execute()

        if not tld_string_result.data:
            raise HTTPException(status_code=404, detail="Evaluation not found")

        tld_string_id = tld_string_result.data[0]['id']
        tld_string = tld_string_result.data[0]['tld_string']

        # The Supabase client raises an exception on failure, so we can rely on try/except.
        # By default, delete operations don't return data, so checking the result is not reliable.

        # 2. Delete associated task executions (cascades should handle this, but being explicit is safer)
        app_store.supabase.table('task_executions').delete().eq('tld_string_id', tld_string_id).execute()
        logger.info(f"Deleted task executions for TLD {tld_string_id}")

        # 3. Delete associated workflow executions
        app_store.supabase.table('workflow_executions').delete().eq('tld_string_id', tld_string_id).execute()
        logger.info(f"Deleted workflow executions for TLD {tld_string_id}")

        # 4. Delete the TLD string record itself
        app_store.supabase.table('tld_strings').delete().eq('id', tld_string_id).execute()
        
        # 5. Remove from existing strings JSON file
        try:
            _remove_string_from_json_file(tld_string)
        except Exception as e:
            logger.warning(f"Could not remove string from JSON file: {e}")
        
        logger.info(f"✅ Successfully deleted evaluation {evaluation_id}")
        return {"message": "Evaluation deleted successfully"}

    except APIError as e:
        logger.error(f"APIError deleting evaluation {evaluation_id}: {e.code} - {e.message}")
        raise HTTPException(status_code=e.status or 500, detail=str(e.message))
    except Exception as e:
        logger.error(f"Unexpected error deleting evaluation {evaluation_id}: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="An unexpected error occurred while deleting the evaluation.")

@app.get("/api/evaluations")
async def get_evaluations():
    """Get all TLD evaluations with their latest status"""
    try:
        app_store = TldApplicationStore()
        
        # Get TLD strings from the correct table (tld_strings) - only fields that exist
        result = app_store.supabase.table("tld_strings").select("*").order("created_at", desc=True).execute()
        
        tld_strings = result.data or []
        
        # Transform to match the frontend's expected format
        evaluations = []
        for tld_string in tld_strings:
            evaluation = {
                "id": tld_string["id"],
                "tld_string": tld_string["tld_string"],
                "status": tld_string.get("status", "PENDING"),
                "created_at": tld_string["created_at"],
                "updated_at": tld_string.get("updated_at", tld_string["created_at"]),
                "workflow_type": tld_string.get("workflow_type", "technical_risk_assessment"),
                "use_case": tld_string.get("use_case"),
                "confidence_score": tld_string.get("confidence_score"),
                "execution_time_minutes": tld_string.get("execution_time_minutes"),
                "recommendation": tld_string.get("recommendation"),
                "confidence_level": tld_string.get("confidence_level"),
                "gemini_report_generated_at": tld_string.get("gemini_report_generated_at"),
                "gemini_report": tld_string.get("gemini_report"),
                "string_type": tld_string.get("string_type", "primary"),
                "task_executions": []
            }
            
            # Get task executions for this TLD string
            try:
                task_result = app_store.supabase.table("task_executions").select("*").eq(
                    "tld_string_id", tld_string["id"]
                ).execute()

                task_executions = task_result.data or []
                evaluation["task_executions"] = task_executions

                # Calculate completed and total tasks from actual task executions
                completed_tasks = len([task for task in task_executions if task.get('result_status') in ['SUCCESS', 'CLEAR', 'APPROVED']])
                total_tasks = len(task_executions)

                evaluation["completed_tasks"] = completed_tasks
                evaluation["total_tasks"] = total_tasks

            except Exception as e:
                logger.warning(f"Could not get task executions for TLD {tld_string['id']}: {e}")
                evaluation["task_executions"] = []
                evaluation["completed_tasks"] = 0
                evaluation["total_tasks"] = 0
            
            evaluations.append(evaluation)
        
        logger.info(f"Retrieved {len(evaluations)} TLD strings")
        return evaluations

    except Exception as e:
        logger.error(f"Error fetching evaluations: {e}")
        logger.error(traceback.format_exc())
        # Return empty list instead of error to prevent dashboard crash
        return []

@app.get("/api/evaluations/search")
async def search_evaluations(q: str = "", limit: int = 100):
    """Search TLD evaluations by string or use case"""
    try:
        app_store = TldApplicationStore()

        # Build query with search filters
        query = app_store.supabase.table("tld_strings").select("*")

        if q.strip():
            # Search in tld_string and use_case fields (case-insensitive)
            search_term = f"%{q.strip()}%"
            query = query.or_(f"tld_string.ilike.{search_term},use_case.ilike.{search_term}")

        # Order by most recent and limit results
        result = query.order("updated_at", desc=True).limit(limit).execute()

        tld_strings = result.data or []

        # Transform to match the frontend's expected format (same as /api/evaluations)
        evaluations = []
        for tld_string in tld_strings:
            evaluation = {
                "id": tld_string["id"],
                "tld_string": tld_string["tld_string"],
                "status": tld_string.get("status", "PENDING"),
                "created_at": tld_string["created_at"],
                "updated_at": tld_string.get("updated_at", tld_string["created_at"]),
                "workflow_type": tld_string.get("workflow_type", "technical_risk_assessment"),
                "use_case": tld_string.get("use_case"),
                "confidence_score": tld_string.get("confidence_score"),
                "execution_time_minutes": tld_string.get("execution_time_minutes"),
                "recommendation": tld_string.get("recommendation"),
                "confidence_level": tld_string.get("confidence_level"),
                "gemini_report_generated_at": tld_string.get("gemini_report_generated_at"),
                "generated_report": tld_string.get("generated_report"),
                "overall_status": tld_string.get("overall_status"),
            }

            # Add task executions if available
            try:
                task_result = app_store.supabase.table("task_executions").select("*").eq("tld_string_id", tld_string["id"]).execute()
                evaluation["task_executions"] = task_result.data or []
            except Exception as e:
                logger.warning(f"Could not get task executions for TLD {tld_string['id']}: {e}")
                evaluation["task_executions"] = []

            evaluations.append(evaluation)

        logger.info(f"Search for '{q}' returned {len(evaluations)} results")
        return evaluations

    except Exception as e:
        logger.error(f"Error searching evaluations: {e}")
        logger.error(traceback.format_exc())
        return []

# =====================================================
# AUDIT LOG ENDPOINTS
# =====================================================

@app.post("/api/evaluations/{tld_string_id}/audit")
async def generate_evaluation_audit(tld_string_id: str):
    """Generate a narrative audit log for an evaluation."""
    from crewai_service.utils.audit_log_generator import (
        generate_evaluation_audit_log,
        format_audit_log_markdown
    )

    try:
        app_store = TldApplicationStore()

        # Get TLD string info
        tld_response = app_store.supabase.table("tld_strings").select("tld_string").eq("id", tld_string_id).execute()
        if not tld_response.data:
            raise HTTPException(status_code=404, detail=f"TLD string not found: {tld_string_id}")

        tld_string = tld_response.data[0]["tld_string"]

        # Fetch all task executions for this TLD string
        task_response = app_store.supabase.table("task_executions").select(
            "task_name, result_data, result_status, execution_time_seconds, agent_name, workflow_id, started_at, completed_at"
        ).eq("tld_string_id", tld_string_id).execute()

        if not task_response.data:
            raise HTTPException(status_code=404, detail=f"No task executions found for TLD: {tld_string}")

        # Generate audit log
        audit_log = generate_evaluation_audit_log(tld_string, task_response.data)
        markdown_content = format_audit_log_markdown(audit_log)

        # Try to save to database (may fail if table doesn't exist yet)
        import uuid
        audit_id = str(uuid.uuid4())
        saved = False
        save_warning = None

        try:
            audit_record = {
                "id": audit_id,
                "evaluation_id": task_response.data[0].get("workflow_id"),
                "tld_string_id": tld_string_id,
                "generated_at": audit_log["generated_at"],
                "audit_data": audit_log,
                "markdown_content": markdown_content,
                "total_tasks": audit_log["total_tasks"],
                "workflow_summaries": audit_log.get("workflow_summaries", {})
            }
            save_response = app_store.supabase.table("audit_logs").insert(audit_record).execute()
            if save_response.data:
                saved = True
                logger.info(f"✅ Generated and saved audit log for {tld_string}")
        except Exception as save_error:
            save_warning = f"Audit generated but not saved: {str(save_error)}"
            logger.warning(f"Could not save audit log (table may not exist): {save_error}")

        return {
            "success": True,
            "audit_id": audit_id if saved else None,
            "tld_string": tld_string,
            "total_tasks": audit_log["total_tasks"],
            "audit_health": audit_log.get("audit_health", "UNKNOWN"),
            "integrity_issues": audit_log.get("integrity_issues", []),
            "workflow_summaries": audit_log.get("workflow_summaries", {}),
            "workflows": list(audit_log.get("workflow_summaries", {}).keys()),
            "audit_log": audit_log,
            "markdown": markdown_content,
            "saved": saved,
            "warning": save_warning
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating audit log: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to generate audit log: {str(e)}")


@app.get("/api/evaluations/{tld_string_id}/audit")
async def get_evaluation_audit(tld_string_id: str):
    """Get the most recent audit log for an evaluation."""
    try:
        app_store = TldApplicationStore()

        # Fetch the most recent audit log for this TLD string
        response = app_store.supabase.table("audit_logs").select("*").eq(
            "tld_string_id", tld_string_id
        ).order("generated_at", desc=True).limit(1).execute()

        if not response.data:
            raise HTTPException(status_code=404, detail=f"No audit log found for TLD string: {tld_string_id}")

        audit_record = response.data[0]

        audit_data = audit_record.get("audit_data", {})
        return {
            "success": True,
            "audit_id": audit_record["id"],
            "generated_at": audit_record["generated_at"],
            "total_tasks": audit_record["total_tasks"],
            "audit_health": audit_data.get("audit_health", "UNKNOWN"),
            "integrity_issues": audit_data.get("integrity_issues", []),
            "workflow_summaries": audit_record.get("workflow_summaries", {}),
            "audit_log": audit_data,
            "markdown": audit_record.get("markdown_content", "")
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching audit log: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch audit log: {str(e)}")


@app.get("/api/evaluations/{tld_string_id}/audit/markdown")
async def get_evaluation_audit_markdown(tld_string_id: str):
    """Get just the markdown content of the audit log (for display)."""
    try:
        app_store = TldApplicationStore()

        # Fetch the most recent audit log for this TLD string
        response = app_store.supabase.table("audit_logs").select(
            "markdown_content, generated_at"
        ).eq("tld_string_id", tld_string_id).order("generated_at", desc=True).limit(1).execute()

        if not response.data:
            raise HTTPException(status_code=404, detail=f"No audit log found for TLD string: {tld_string_id}")

        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(
            content=response.data[0].get("markdown_content", ""),
            media_type="text/markdown"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching audit markdown: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch audit markdown: {str(e)}")


# =====================================================
# APPLICANT MANAGEMENT ENDPOINTS
# =====================================================

def validate_uuid(uuid_string: str) -> bool:
    """Validate if a string is a valid UUID"""
    try:
        uuid.UUID(uuid_string)
        return True
    except ValueError:
        return False

@app.get("/api/applicants/default")
async def get_default_applicant():
    """Get the default Example Registry applicant"""
    try:
        app_store = TldApplicationStore()
        applicant = app_store.get_default_applicant()
        
        if not applicant:
            raise HTTPException(status_code=404, detail="Default applicant not found")
        
        return {
            "success": True,
            "applicant": applicant,
            "message": "Default applicant retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error getting default applicant: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve default applicant: {str(e)}")

@app.get("/api/applicants/{applicant_id}")
async def get_applicant_by_id(applicant_id: str):
    """Get a specific applicant by ID"""
    try:
        # Validate UUID format
        if not validate_uuid(applicant_id):
            raise HTTPException(status_code=400, detail="Invalid applicant ID format")
        
        app_store = TldApplicationStore()
        
        # Get applicant from database
        response = app_store.supabase.table('applicants').select('*').eq('id', applicant_id).execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Applicant not found")

        return {
            "success": True,
            "applicant": response.data[0],
            "message": "Applicant retrieved successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting applicant {applicant_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve applicant: {str(e)}")

@app.get("/api/applicants")
async def list_all_applicants():
    """Get all applicants"""
    try:
        app_store = TldApplicationStore()
        
        # Get all applicants from database using the working client
        response = app_store.supabase.table('applicants').select('*').order('created_at', desc=True).execute()
        
        applicants = response.data or []
        
        return {
            "success": True,
            "applicants": applicants,
            "count": len(applicants),
            "message": f"Retrieved {len(applicants)} applicants"
        }
        
    except Exception as e:
        logger.error(f"Error listing applicants: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list applicants: {str(e)}")

@app.post("/api/applicants", status_code=201)
async def create_applicant(applicant_data: ApplicantCreate):
    """Create a new applicant"""
    try:
        app_store = TldApplicationStore()
        
        # Check for duplicate legal name
        existing_response = app_store.supabase.table('applicants').select('id').eq('legal_name', applicant_data.legal_name).execute()
        if existing_response.data:
            raise HTTPException(status_code=409, detail=f"Applicant with legal name '{applicant_data.legal_name}' already exists")
        
        # Convert Pydantic model to dict and prepare for database
        applicant_dict = applicant_data.dict()
        
        # Convert key_personnel to JSONB format
        if applicant_dict.get('key_personnel'):
            applicant_dict['key_personnel'] = [person.dict() if hasattr(person, 'dict') else person for person in applicant_dict['key_personnel']]
        
        # Add timestamps
        applicant_dict['created_at'] = datetime.utcnow().isoformat()
        applicant_dict['updated_at'] = datetime.utcnow().isoformat()
        
        # Insert into database
        response = app_store.supabase.table('applicants').insert(applicant_dict).execute()
        
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to create applicant")
        
        created_applicant = response.data[0]
        
        logger.info(f"Created new applicant: {created_applicant['legal_name']} (ID: {created_applicant['id']})")
        
        return {
            "success": True,
            "applicant_id": created_applicant['id'],
            "message": "Applicant created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating applicant: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create applicant: {str(e)}")

@app.put("/api/applicants/{applicant_id}")
async def update_applicant(applicant_id: str, applicant_data: ApplicantUpdate):
    """Update an existing applicant (full update)"""
    try:
        # Validate UUID format
        if not validate_uuid(applicant_id):
            raise HTTPException(status_code=400, detail="Invalid applicant ID format")
        
        app_store = TldApplicationStore()
        
        # Check if applicant exists
        existing_response = app_store.supabase.table('applicants').select('id').eq('id', applicant_id).execute()
        if not existing_response.data:
            raise HTTPException(status_code=404, detail="Applicant not found")
        
        # Convert Pydantic model to dict, excluding None values
        update_dict = applicant_data.dict(exclude_unset=True, exclude_none=True)
        
        if not update_dict:
            raise HTTPException(status_code=400, detail="No valid fields provided for update")
        
        # Convert key_personnel to JSONB format if present
        if 'key_personnel' in update_dict and update_dict['key_personnel']:
            update_dict['key_personnel'] = [person.dict() if hasattr(person, 'dict') else person for person in update_dict['key_personnel']]
        
        # Add updated timestamp
        update_dict['updated_at'] = datetime.utcnow().isoformat()
        
        # Update in database
        response = app_store.supabase.table('applicants').update(update_dict).eq('id', applicant_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to update applicant")
        
        updated_applicant = response.data[0]
        
        logger.info(f"Updated applicant: {updated_applicant['legal_name']} (ID: {applicant_id})")
        
        return {
            "success": True,
            "applicant": updated_applicant,
            "message": "Applicant updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating applicant {applicant_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update applicant: {str(e)}")

@app.patch("/api/applicants/{applicant_id}")
async def partial_update_applicant(applicant_id: str, applicant_data: ApplicantUpdate):
    """Partially update an existing applicant (PATCH - same as PUT for this implementation)"""
    return await update_applicant(applicant_id, applicant_data)

@app.delete("/api/applicants/{applicant_id}")
async def delete_applicant(applicant_id: str):
    """Delete an applicant"""
    try:
        # Validate UUID format
        if not validate_uuid(applicant_id):
            raise HTTPException(status_code=400, detail="Invalid applicant ID format")
        
        app_store = TldApplicationStore()
        
        # Check if applicant exists
        existing_response = app_store.supabase.table('applicants').select('id, legal_name').eq('id', applicant_id).execute()
        if not existing_response.data:
            raise HTTPException(status_code=404, detail="Applicant not found")
        
        applicant_name = existing_response.data[0]['legal_name']
        
        # Delete from database
        response = app_store.supabase.table('applicants').delete().eq('id', applicant_id).execute()
        
        logger.info(f"Deleted applicant: {applicant_name} (ID: {applicant_id})")
        
        return {
            "success": True,
            "message": "Applicant deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting applicant {applicant_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete applicant: {str(e)}")

# =====================================================
# FILE UPLOAD ENDPOINTS
# =====================================================

@app.post("/api/applications/{application_id}/files/upload")
async def upload_application_files(
    application_id: str,
    files: List[UploadFile] = File(...),
    question_id: str = Form(...),
    document_type: Optional[str] = Form(None),
    uploaded_by: Optional[str] = Form(None)
):
    """
    Upload files for a specific application question
    """
    try:
        logger.info(f"📁 Uploading {len(files)} files for application {application_id}, question {question_id}")
        
        uploaded_files = await file_upload_service.upload_files(
            application_id=application_id,
            question_id=question_id,
            files=files,
            document_type=document_type,
            uploaded_by=uploaded_by
        )
        
        logger.info(f"✅ Successfully uploaded {len(uploaded_files)} files")
        
        return {
            "success": True,
            "message": f"Successfully uploaded {len(uploaded_files)} files",
            "files": uploaded_files
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error uploading files: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to upload files: {str(e)}")

@app.get("/api/applications/{application_id}/files")
async def get_application_files(application_id: str):
    """
    Get all files for an application
    """
    try:
        logger.info(f"📁 Getting files for application {application_id}")
        
        files = await file_upload_service.get_application_files(application_id)
        
        logger.info(f"✅ Found {len(files)} files for application")
        
        return {
            "success": True,
            "files": files,
            "count": len(files)
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting application files: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to get application files: {str(e)}")

@app.delete("/api/files/{file_id}")
async def delete_application_file(file_id: str):
    """
    Delete a specific file
    """
    try:
        logger.info(f"🗑️ Deleting file {file_id}")
        
        success = await file_upload_service.delete_file(file_id)
        
        if success:
            logger.info(f"✅ Successfully deleted file {file_id}")
            return {
                "success": True,
                "message": "File deleted successfully"
            }
        else:
            raise HTTPException(status_code=404, detail="File not found or could not be deleted")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting file: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")

# Report Generation Endpoints


async def generate_comprehensive_report_with_fallback(tld_string: str, evaluation_data: dict) -> str:
    """Generate report with Gemini 2.5 Pro and GPT-4o fallback"""
    
    # First try Gemini 2.5 Pro
    try:
        logger.info(f"🤖 Attempting Gemini 2.5 Pro report generation for {tld_string}")
        report_content = await generate_report_content(tld_string, evaluation_data)
        
        if report_content and len(report_content.strip()) > 100:  # Basic validation
            logger.info(f"✅ Gemini 2.5 Pro report generated successfully for {tld_string}")
            return report_content
        else:
            logger.warning(f"⚠️ Gemini report too short or empty for {tld_string}, trying GPT-4o")
            
    except Exception as e:
        logger.warning(f"⚠️ Gemini 2.5 Pro failed for {tld_string}: {e}, trying GPT-4o fallback")
    
    # Fallback to GPT-4o
    try:
        logger.info(f"🔄 Attempting GPT-4o fallback for {tld_string}")
        report_content = await generate_gpt4o_report(tld_string, evaluation_data)
        
        if report_content and len(report_content.strip()) > 100:
            logger.info(f"✅ GPT-4o fallback report generated successfully for {tld_string}")
            return report_content
        else:
            logger.error(f"❌ GPT-4o fallback also failed for {tld_string}")
            
    except Exception as e:
        logger.error(f"❌ GPT-4o fallback failed for {tld_string}: {e}")
    
    raise Exception("Both Gemini 2.5 Pro and GPT-4o failed to generate report")

async def generate_gpt4o_report(tld_string: str, evaluation_data: dict) -> str:
    """Generate report using GPT-4o as fallback"""
    import httpx
    import os
    
    try:
        # Load OpenAI API key from the environment
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise Exception("OPENAI_API_KEY not set")
        
        # Prepare the prompt using the same logic as Gemini
        task_executions = evaluation_data.get('task_executions', [])
        report_prompt = create_personalized_gemini_prompt(tld_string, task_executions)
        
        # Call OpenAI GPT-4o API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o",
                    "messages": [
                        {
                            "role": "system", 
                            "content": "You are an expert TLD evaluation analyst. Generate a comprehensive, professional report based on the provided evaluation data."
                        },
                        {
                            "role": "user",
                            "content": report_prompt
                        }
                    ],
                    "temperature": 0.3,
                    "max_tokens": 4000
                },
                timeout=120.0
            )
        
        if response.status_code != 200:
            raise Exception(f"OpenAI API error: {response.status_code}")
        
        result = response.json()
        report_content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
        
        if not report_content:
            raise Exception("Empty response from OpenAI")
        
        logger.info(f"✅ GPT-4o report generated: {len(report_content)} characters")
        return report_content
        
    except Exception as e:
        logger.error(f"❌ GPT-4o generation failed: {e}")
        raise

async def save_report_to_database(tld_string: str, report_content: str, model_used: str = 'gemini-2.5-pro', risk_data: Dict[str, Any] = None):
    """Save the generated report to the tld_strings.generated_report field"""
    try:
        app_store = TldApplicationStore()
        supabase = app_store.supabase
        
        if not supabase:
            logger.warning("Supabase client not available - skipping report save")
            return
        
        # Store the report in the generated_report field
        from datetime import timezone
        report_data = {
            'generated_report': {
                'type': 'ai_generated',
                'report_content': report_content,
                'generated_at': datetime.now().isoformat(),
                'model_used': model_used,
                'status': 'completed',
                'content_length': len(report_content)
            }
        }
        
        # Add risk classification data if available - use proper risk assessment format
        if risk_data and risk_data.get('risk_classification'):
            # Import risk categorization from add_risk_flags
            try:
                from scripts.maintenance.add_risk_flags import categorize_risk_level
                
                # Create comprehensive risk assessment using the same logic as add_risk_flags.py
                overall_risk = risk_data.get('risk_classification', 'Unknown')
                risk_info = categorize_risk_level(overall_risk)
                
                # Create risk assessment structure that frontend expects
                risk_assessment = {
                    'risk_level': risk_info['risk_level'],
                    'risk_score': risk_info['risk_score'], 
                    'risk_color': risk_info['risk_color'],
                    'display_text': risk_info['display_text'],
                    'description': risk_info['description'],
                    'risk_classification': risk_data.get('risk_classification'),
                    'recommendation': risk_data.get('recommendation'),
                    'data_confidence': 'AI Generated',
                    'generated_at': datetime.now().isoformat()
                }
                
                # Add risk assessment to the report structure
                report_data['generated_report']['risk_assessment'] = risk_assessment
                
                # Risk data stored in generated_report.risk_assessment only —
                # overall_status is managed by run_sequential_workflows and must
                # not be overwritten with risk classification values (MEDIUM/HIGH/etc.)
                logger.info(f"📊 Saving risk assessment for {tld_string}: {risk_info['risk_level']} ({risk_info['display_text']})")

            except ImportError as e:
                logger.warning(f"Could not import risk categorization: {e}")
                # Fallback: store raw risk data in the report without overwriting overall_status
                report_data['generated_report']['risk_classification'] = risk_data.get('risk_classification')
                report_data['generated_report']['recommendation'] = risk_data.get('recommendation')
                logger.info(f"📊 Fallback: Saving risk classification in report for {tld_string}: {risk_data.get('risk_classification')}")
        
        result = supabase.table('tld_strings').update(report_data).eq('tld_string', tld_string).execute()
        
        if result.data:
            logger.info(f"✅ Report saved to tld_strings.generated_report for {tld_string}")
            
            # Auto-export to Google Drive
            try:
                logger.info(f"📤 Attempting auto-export to Google Drive for {tld_string}...")
                doc_url = export_report_to_google_drive(tld_string)
                
                if doc_url:
                    logger.info(f"✅ Auto-exported {tld_string} to Google Drive: {doc_url}")
                else:
                    logger.warning(f"⚠️ Auto-export failed for {tld_string} - check Google Drive configuration")
                    
            except Exception as export_error:
                logger.error(f"❌ Auto-export error for {tld_string}: {export_error}")
                # Don't fail the report save if export fails
                
        else:
            logger.warning(f"❌ No rows updated for {tld_string} report save")
        
    except Exception as e:
        logger.error(f"❌ Failed to save report to database: {e}")

# Application Generation Models
class ApplicationGenerationRequest(BaseModel):
    tld_string: str
    tld_string_id: Optional[str] = None
    applicant_id: str
    application_type: Optional[str] = "standard"
    secondary_string_id: Optional[str] = None
    secondary_tld_string: Optional[str] = None
    generate_answers: bool = True
    store_in_database: bool = True

class ApplicationGenerationResponse(BaseModel):
    success: bool
    tld_string: str
    application_id: Optional[str] = None
    answers_generated: Optional[List[Dict[str, Any]]] = None  # List of answer results
    status: str = "Generating"
    message: str
    completion_percentage: Optional[float] = None
    error: Optional[str] = None

# Database inspection endpoints (temporary)
@app.get("/api/database/tables")
async def check_database_tables():
    """Check what application-related tables exist in the database"""
    try:
        app_store = TldApplicationStore()
        tables_to_check = [
            'application_questions_enhanced',
            'application_answers_enhanced', 
            'application_questions',
            'application_answers'
        ]
        
        results = {}
        for table in tables_to_check:
            try:
                # Try to get count of records
                result = app_store.supabase.table(table).select('id', count='exact').limit(1).execute()
                results[table] = {
                    "exists": True,
                    "count": result.count,
                    "error": None
                }
            except Exception as e:
                results[table] = {
                    "exists": False, 
                    "count": 0,
                    "error": str(e)
                }
        
        return {
            "success": True,
            "tables": results
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# Application endpoints
@app.get("/api/applications/{application_id}/questions")
async def get_application_questions_and_answers(application_id: str):
    """Get all questions and answers for a specific application by parsing generated output files"""
    try:
        # First get the application to find the TLD string, applicant, and type
        app_store = TldApplicationStore()
        result = app_store.supabase.table('tld_applications').select(
            'tld_string, applicant_id, application_type, applicants(*)'
        ).eq('id', application_id).execute()

        if not result.data:
            return {
                "success": False,
                "error": "Application not found",
                "questions": []
            }

        app_row = result.data[0]
        tld_string = app_row['tld_string']
        applicant_data = app_row.get('applicants')  # Will be populated if applicant_id exists
        application_type = app_row.get('application_type', 'standard')
        
        # Filter questions by applicability from the DB column.
        # If applicability hasn't been populated yet, fall back to hardcoded ranges.
        def is_applicable_by_db(q, app_type: str) -> bool:
            """Check if a question is applicable using the DB applicability column."""
            applicability = q.get('applicability')
            if not applicability:
                return True  # No applicability data yet — include by default
            return 'ALL' in applicability or app_type in applicability

        # Fallback: hardcoded question set mapping (used when DB column not populated)
        def get_question_set(q_num: int) -> str:
            """Map question number to ICANN Question Set name (fallback)"""
            QUESTION_SET_RANGES = [
                ((1, 48),    "1. Applying Entity Information"),
                ((49, 64),   "2. Users"),
                ((65, 103),  "3. Payments"),
                ((104, 115), "4. Applicant Background and Organization"),
                ((116, 121), "5. Applied-for String"),
                ((122, 130), "6. Variant Strings"),
                ((131, 157), "7. Community gTLDs"),
                ((158, 161), "8. Geographic Names"),
                ((162, 163), "9. Reserved Names"),
                ((164, 171), "10. Safeguard Assessment"),
                ((172, 175), "11. Registry Voluntary Commitments"),
                ((176, 178), "12. Registry Services"),
                ((179, 188), "13. Brand TLD and Code of Conduct"),
                ((189, 191), "14. Financial Profile Determination"),
                ((192, 194), "15. Government Financial Profile"),
                ((195, 201), "16. Registry Operator Financial Profile"),
                ((202, 207), "17. Top 25 Financial Profile"),
                ((208, 219), "18. Standard Financial Profile"),
                ((220, 221), "19. Operational Questions"),
                ((222, 222), "20. Additional Information"),
                ((223, 224), "21. Bona Fide Intent"),
                ((225, 225), "22. Volume Refund"),
                ((226, 237), "23. Variant Strings (Supplementary)"),
            ]
            for (lo, hi), name in QUESTION_SET_RANGES:
                if lo <= q_num <= hi:
                    return name
            return "Other"
        
        # First try to load questions and answers from database
        try:
            # Load questions from enhanced table
            # Note: We filter out Financial, Bank, Payor, and Billing sections
            # and filter by application type
            questions_result = app_store.supabase.table('application_questions_enhanced').select('*').execute()
            questions = []
            
            # Sections to exclude (financial partner handles these)
            EXCLUDED_SECTION_PREFIXES = ('Financial', 'Bank', 'Payor', 'Billing', 'Volume')
            # Question Set 3: Payments (Q65-103) is handled by financial partner
            EXCLUDED_PAYMENT_QUESTIONS = set(range(65, 104))  # 65-103 inclusive
            
            if questions_result.data:
                # Filter by applicability (DB-driven) and exclude payments/financial sections
                def should_include_question(q):
                    # Get question number
                    try:
                        qn = q.get('question_number', '0')
                        match = re.match(r'(\d+)', str(qn))
                        q_num = int(match.group(1)) if match else 0
                    except Exception:
                        q_num = 0

                    # Exclude Payments questions (Q65-104) - financial partner handles these
                    if q_num in EXCLUDED_PAYMENT_QUESTIONS:
                        return False

                    # Also exclude by section name for any stragglers
                    if any(q.get('section_name', '').startswith(prefix) for prefix in EXCLUDED_SECTION_PREFIXES):
                        return False

                    # Use DB applicability column if populated
                    if not is_applicable_by_db(q, application_type):
                        return False

                    return True

                filtered_data = [q for q in questions_result.data if should_include_question(q)]

                logger.info(f"Questions for {application_type} app: {len(questions_result.data)} total, {len(filtered_data)} after applicability filtering")
                
                # Sort by question_number numerically (handle formats like "7", "18a", "Q1.2-1")
                def sort_key(q):
                    qn = q.get('question_number', '0')
                    # Extract leading numeric part for primary sort
                    import re
                    match = re.match(r'(\d+)', str(qn))
                    return int(match.group(1)) if match else 0
                
                sorted_questions = sorted(filtered_data, key=sort_key)
                
                for q in sorted_questions:
                    # Handle column names from enhanced schema
                    section = q.get('section_name') or q.get('section', '')
                    subsection = q.get('sub_section') or q.get('subsection', '')
                    
                    # Get question set from question number
                    q_num = sort_key(q)  # Reuse the numeric extraction
                    question_set = get_question_set(q_num)
                    
                    # Use DB question_set_name if available, fall back to computed
                    db_question_set_name = q.get('question_set_name')
                    if db_question_set_name:
                        db_set_num = q.get('question_set')
                        display_set = f"{db_set_num}. {db_question_set_name}" if db_set_num else db_question_set_name
                    else:
                        display_set = question_set

                    questions.append({
                        "id": q['id'],
                        "question_number": str(q['question_number']),
                        "question_set": display_set,
                        "section": section,
                        "subsection": subsection,
                        "question_text": q['question_text'],
                        "notes_instructions": q.get('notes_instructions', ''),
                        "field_type": q.get('input_type') or q.get('field_type', 'textarea'),
                        "character_limit": q.get('character_limit'),
                        "input_field_requirements": q.get('input_field_requirements', ''),
                        "required": q.get('is_required') or q.get('required', True),
                        "public_posting": q.get('is_public') or q.get('public_posting', False),
                        "question_category": q.get('question_category'),
                        "applicant_field_mapping": q.get('applicant_field_mapping'),
                        "relevant_task_names": q.get('relevant_task_names'),
                        "generation_hint": q.get('generation_hint'),
                    })

            # Load answers from database - try enhanced table first, then fallback to basic
            answers = []
            
            # Try enhanced answers table first (used by RAG generation)
            answers_result = app_store.supabase.table('application_answers_enhanced').select('*').eq('tld_application_id', application_id).execute()
            
            if answers_result.data:
                for a in answers_result.data:
                    answers.append({
                        "id": a['id'],
                        "question_id": a['question_id'],
                        "application_id": a['tld_application_id'],
                        "answer_text": a.get('answer_text') or '',
                        "answer_files": a.get('uploaded_files', []),
                        "status": a.get('review_status', 'draft'),
                        "ai_generated": a.get('generation_method') == 'ai_generated',
                        "last_modified": a.get('updated_at')
                    })
            else:
                # Fallback to basic answers table
                answers_result = app_store.supabase.table('application_answers').select('*').eq('application_id', application_id).execute()
                if answers_result.data:
                    for a in answers_result.data:
                        answers.append({
                            "id": a['id'],
                            "question_id": a['question_id'],
                            "application_id": a['application_id'],
                            "answer_text": a['answer_text'] or '',
                            "answer_files": a.get('answer_files', []),
                            "status": a.get('status', 'draft'),
                            "ai_generated": a.get('ai_generated', False),
                            "last_modified": a.get('last_modified')
                        })

            # If we have questions from database, return them (even if no answers yet)
            if questions:
                logger.info(f"Returning {len(questions)} questions and {len(answers)} answers from database")
                return {
                    "success": True,
                    "application_id": application_id,
                    "tld_string": tld_string,
                    "string_meaning": app_row.get('string_meaning'),
                    "string_rationale": app_row.get('string_rationale'),
                    "intended_use": app_row.get('intended_use'),
                    "questions": questions,
                    "answers": answers,
                    "applicant": applicant_data,  # Include applicant data for populating applicant questions
                    "source": "database"
                }

        except Exception as db_error:
            logger.error(f"Database error loading Q&A: {db_error}")

        # Fallback to file-only parsing
        from crewai_service.application_parser import ApplicationResponseParser
        parser = ApplicationResponseParser()

        questions_and_answers = parser.get_questions_and_answers(tld_string)
        application_data = parser.parse_application_responses(tld_string)

        return {
            "success": True,
            "application_id": application_id,
            "tld_string": tld_string,
            "summary": application_data["summary"],
            "questions": questions_and_answers,
            "sections": list(application_data["sections"].keys()),
            "source": "file_only"
        }
        
    except Exception as e:
        logger.error(f"Error getting application Q&A for {application_id}: {e}")
        return {
            "success": False,
            "error": str(e),
            "questions": []
        }

@app.get("/api/applications")
async def get_applications():
    """Get all applications from the database"""
    try:
        app_store = TldApplicationStore()
        result = app_store.supabase.table('tld_applications').select(
            'id, tld_string, tld_string_id, status, completion_percentage, created_at, updated_at, internal_reference, applicant_id, application_type, applicants(legal_name, business_name)'
        ).order('created_at', desc=True).execute()
        
        if result.data:
            return {
                "success": True,
                "applications": result.data
            }
        else:
            return {
                "success": True,
                "applications": []
            }
    except Exception as e:
        logger.error(f"Error fetching applications: {e}")
        return {
            "success": False,
            "error": str(e),
            "applications": []
        }

@app.get("/api/applications/{application_id}")
async def get_application(application_id: str):
    """Get a single application by ID."""
    try:
        app_store = TldApplicationStore()
        result = app_store.supabase.table('tld_applications').select(
            '*, applicants(legal_name, business_name)'
        ).eq('id', application_id).execute()

        if not result.data:
            return {"success": False, "error": "Application not found"}

        return {"success": True, "application": result.data[0]}
    except Exception as e:
        logger.error(f"Error fetching application {application_id}: {e}")
        return {"success": False, "error": str(e)}


@app.post("/api/applications/generate-full", response_model=ApplicationGenerationResponse)
async def generate_full_application(request: ApplicationGenerationRequest):
    """
    Create a TLD application and kick off answer generation in the background.

    Returns immediately with status "Generating" so the frontend can poll
    for incremental progress via the application's completion_percentage.
    """
    try:
        logger.info(f"Starting full application generation for TLD: {request.tld_string}")

        app_store = TldApplicationStore()

        # Create or get existing application
        application_id = None
        if request.store_in_database:
            try:
                existing_app = app_store.supabase.table('tld_applications').select('*').eq('tld_string', request.tld_string).eq('applicant_id', request.applicant_id).execute()

                if existing_app.data:
                    application_id = existing_app.data[0]['id']
                    logger.info(f"Found existing application: {application_id}")
                else:
                    if not request.tld_string_id:
                        # tld_string_id is NOT NULL in DB — look it up from tld_strings
                        lookup = app_store.supabase.table('tld_strings').select('id').eq('tld_string', request.tld_string).limit(1).execute()
                        if lookup.data:
                            request.tld_string_id = lookup.data[0]['id']
                        else:
                            logger.error(f"No tld_strings record found for '{request.tld_string}'")

                    # Pull use_case from tld_strings to seed application context
                    string_context = {}
                    if request.tld_string_id:
                        ctx_lookup = app_store.supabase.table('tld_strings').select(
                            'use_case, generated_report'
                        ).eq('id', request.tld_string_id).limit(1).execute()
                        if ctx_lookup.data:
                            use_case = ctx_lookup.data[0].get('use_case') or ''
                            report = ctx_lookup.data[0].get('generated_report') or {}
                            string_context = {
                                'intended_use': use_case,
                                'string_meaning': report.get('string_meaning') or '',
                                'string_rationale': report.get('string_rationale') or '',
                            }

                    app_data = {
                        'tld_string': request.tld_string,
                        'tld_string_id': request.tld_string_id,
                        'applicant_id': request.applicant_id,
                        'application_type': request.application_type or 'standard',
                        'internal_reference': f"APP-{request.tld_string.upper()}-{datetime.utcnow().strftime('%Y%m%d')}",
                        'status': 'In_Progress',
                        'completion_percentage': 0,
                        'string_meaning': string_context.get('string_meaning', ''),
                        'string_rationale': string_context.get('string_rationale', ''),
                        'intended_use': string_context.get('intended_use', ''),
                        'created_at': datetime.utcnow().isoformat(),
                        'updated_at': datetime.utcnow().isoformat()
                    }

                    if request.secondary_string_id:
                        app_data['secondary_string_id'] = request.secondary_string_id
                    if request.secondary_tld_string:
                        app_data['secondary_tld_string'] = request.secondary_tld_string

                    create_response = app_store.supabase.table('tld_applications').insert(app_data).execute()
                    if create_response.data:
                        application_id = create_response.data[0]['id']
                        logger.info(f"Created new application: {application_id}")
                    else:
                        logger.warning("Failed to create application in database — insert returned no data")

            except Exception as db_error:
                logger.error(f"Database error creating application: {db_error}")

        if not application_id:
            return ApplicationGenerationResponse(
                success=False,
                tld_string=request.tld_string,
                application_id=None,
                answers_generated=None,
                status="Failed",
                message=f"Failed to create application record for .{request.tld_string}",
            )

        # Fire off generation in the background — return immediately
        if request.generate_answers:
            asyncio.create_task(
                _run_background_generation(application_id, request.tld_string)
            )

        return ApplicationGenerationResponse(
            success=True,
            tld_string=request.tld_string,
            application_id=application_id,
            answers_generated=[],
            status="Generating",
            message=f"Application created for .{request.tld_string} — answer generation started in background",
        )

    except Exception as e:
        logger.error(f"Error generating full application for {request.tld_string}: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")

        return ApplicationGenerationResponse(
            success=False,
            tld_string=request.tld_string,
            application_id=None,
            answers_generated=None,
            status="Failed",
            message=f"Failed to generate application for .{request.tld_string}",
            error=str(e)
        )


async def _run_background_generation(application_id: str, tld_string: str):
    """Background task: generate all answers and update application status."""
    try:
        logger.info(f"Background generation started for .{tld_string} (app {application_id})")

        from crewai_service.answer_generation_service import answer_generation_service

        generation_result = await answer_generation_service.generate_multiple(
            application_id=application_id,
            question_ids=None,
            store_in_database=True,
        )

        if generation_result.get("success"):
            logger.info(
                f"Background generation completed for .{tld_string}: "
                f"{generation_result.get('successful_answers', 0)}/{generation_result.get('total_questions', 0)} answers"
            )
        else:
            logger.error(f"Background generation failed for .{tld_string}: {generation_result.get('error')}")
            app_store = TldApplicationStore()
            app_store.supabase.table('tld_applications').update({
                'status': 'Draft',
                'updated_at': datetime.utcnow().isoformat(),
            }).eq('id', application_id).execute()

    except Exception as e:
        logger.error(f"Background generation error for .{tld_string}: {e}")
        logger.error(traceback.format_exc())
        try:
            app_store = TldApplicationStore()
            app_store.supabase.table('tld_applications').update({
                'status': 'Draft',
                'updated_at': datetime.utcnow().isoformat(),
            }).eq('id', application_id).execute()
        except Exception:
            pass

# Answer Generation Endpoints (3-tier: entity / selection / substantive)
from crewai_service.answer_generation_service import answer_generation_service

class RAGAnswerRequest(BaseModel):
    question_id: str
    question_text: str
    tld_string: Optional[str] = None
    applicant_id: Optional[str] = None
    application_id: Optional[str] = None
    question_category: Optional[str] = None  # entity_field, selection_field, substantive_field, file_upload
    user_prompt: Optional[str] = None        # User-provided direction for generation

class RAGAnswerResponse(BaseModel):
    success: bool
    response: str
    data_source: str
    confidence: float
    question_id: str
    generated_at: str
    tip: Optional[str] = None      # Contextual hint for entity/selection fields
    question_category: Optional[str] = None
    generation_status: Optional[str] = None  # insufficient_data, generated, etc.
    error: Optional[str] = None

class QuestionGuidanceRequest(BaseModel):
    question_id: str
    question_text: str

class ApplicationRAGGenerationRequest(BaseModel):
    application_id: str
    question_ids: Optional[List[str]] = None
    store_in_database: bool = True

@app.post("/api/applications/generate-answer", response_model=RAGAnswerResponse)
async def generate_answer(request: RAGAnswerRequest):
    """
    Generate an answer for a specific ICANN application question.

    Routes through the 3-tier handler based on question_category:
    - entity_field: instant DB lookup from applicant data
    - selection_field: returns options + contextual tip
    - substantive_field: single Gemini call with evaluation context
    - file_upload: returns requirements info
    """
    try:
        logger.info(f"Generating answer for question {request.question_id} (category={request.question_category})")

        result = await answer_generation_service.generate_answer(
            question_id=request.question_id,
            question_text=request.question_text,
            tld_string=request.tld_string,
            applicant_id=request.applicant_id,
            application_id=request.application_id,
            question_category=request.question_category,
            user_prompt=request.user_prompt,
        )

        return RAGAnswerResponse(
            success=result.get('success', False),
            response=result.get('response', ''),
            data_source=result.get('data_source', 'unknown'),
            confidence=result.get('confidence', 0.0),
            question_id=request.question_id,
            generated_at=result.get('generated_at', datetime.utcnow().isoformat()),
            tip=result.get('tip'),
            question_category=result.get('question_category'),
            generation_status=result.get('data_source') if result.get('data_source') == 'insufficient_data' else None,
            error=result.get('error')
        )

    except Exception as e:
        logger.error(f"Error generating answer for {request.question_id}: {e}")
        return RAGAnswerResponse(
            success=False,
            response=f"Error generating answer: {str(e)}",
            data_source='error',
            confidence=0.0,
            question_id=request.question_id,
            generated_at=datetime.utcnow().isoformat(),
            error=str(e)
        )

@app.post("/api/applications/question-guidance", response_model=RAGAnswerResponse)
async def get_question_guidance(request: QuestionGuidanceRequest):
    """
    Get lightweight guidance for a specific ICANN application question.
    Returns tips based on question category.
    """
    try:
        logger.info(f"Getting guidance for question {request.question_id}")

        result = await answer_generation_service.get_question_guidance(
            question_id=request.question_id,
            question_text=request.question_text
        )

        return RAGAnswerResponse(
            success=result.get('success', False),
            response=result.get('response', ''),
            data_source=result.get('data_source', 'question_guidance'),
            confidence=result.get('confidence', 0.0),
            question_id=request.question_id,
            generated_at=result.get('generated_at', datetime.utcnow().isoformat()),
            tip=result.get('tip'),
            error=result.get('error')
        )

    except Exception as e:
        logger.error(f"Error getting guidance for {request.question_id}: {e}")
        return RAGAnswerResponse(
            success=False,
            response=f"Error getting guidance: {str(e)}",
            data_source='error',
            confidence=0.0,
            question_id=request.question_id,
            generated_at=datetime.utcnow().isoformat(),
            error=str(e)
        )

@app.post("/api/applications/generate-multiple", response_model=ApplicationGenerationResponse)
async def generate_multiple_answers(request: ApplicationRAGGenerationRequest):
    """
    Generate answers for multiple questions using the 3-tier handler.

    Smart batch flow:
    1. Instant: fill entity_field questions from applicant data
    2. Instant: set defaults for selection_field questions
    3. Skip: file_upload questions
    4. AI batch: generate substantive_field answers (semaphore-limited)
    """
    try:
        logger.info(f"Batch generating answers for application {request.application_id}")

        result = await answer_generation_service.generate_multiple(
            application_id=request.application_id,
            question_ids=request.question_ids,
            store_in_database=request.store_in_database
        )

        return ApplicationGenerationResponse(
            success=result.get('success', False),
            tld_string=result.get('tld_string', ''),
            application_id=request.application_id,
            answers_generated=result.get('results', []),
            status='Completed' if result.get('success') else 'Failed',
            message=f"Generated {result.get('successful_answers', 0)} of {result.get('total_questions', 0)} answers",
            completion_percentage=result.get('completion_percentage', 0.0),
            error=result.get('error')
        )

    except Exception as e:
        logger.error(f"Error generating multiple answers for {request.application_id}: {e}")
        return ApplicationGenerationResponse(
            success=False,
            tld_string='',
            application_id=request.application_id,
            answers_generated=[],
            status='Failed',
            message=f"Failed to generate answers",
            error=str(e)
        )

# Chat endpoint
@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_assistant(request: ChatMessage):
    """
    Chat with TLD Assistant using RAG-powered semantic search

    Provides intelligent responses using:
    - Semantic vector search across TLD evaluations and risk assessments
    - ICANN Guidebook content and requirements
    - Application questions and guidance
    - Intelligent content chunking based on guidebook sections
    """
    try:
        logger.info(f"Processing chat request: {request.message[:100]}...")

        # Use RAG chat agent for semantic search-powered responses
        response_data = await rag_chat_agent.process_query(
            request.message,
            request.context
        )
        
        logger.info(f"Chat response generated, success: {response_data.get('success')}")
        
        return ChatResponse(
            success=response_data.get("success", True),
            response=response_data.get("response", ""),
            sources=response_data.get("sources", []),
            metadata=response_data.get("metadata", {}),
            error=response_data.get("error")
        )
        
    except Exception as e:
        logger.error(f"Chat request failed: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        return ChatResponse(
            success=False,
            response="I apologize, but I encountered an error processing your question. Please try again or rephrase your question.",
            sources=[],
            metadata={
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            },
            error=str(e)
        )

@app.get("/api/chat/health")
async def chat_health_check():
    """Health check for RAG chat service"""
    try:
        # Quick test of the RAG chat service
        test_response = await rag_chat_agent.process_query("What is ICANN?")

        return {
            "status": "healthy",
            "chat_service_available": test_response.get("success", False),
            "rag_agent_ready": hasattr(rag_chat_agent, 'agent') and rag_chat_agent.agent is not None,
            "model_available": getattr(rag_chat_agent, 'model_available', False),
            "rag_tool_ready": hasattr(rag_chat_agent, 'agent') and rag_chat_agent.agent is not None,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Chat health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


# RAG Pipeline Management Endpoints
@app.post("/api/rag/setup-schema")
async def setup_rag_schema():
    """Set up pgvector schema and tables for RAG pipeline"""
    try:
        from crewai_service.rag_embedder import rag_embedder

        if not rag_embedder.supabase:
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": "Supabase not available"}
            )

        # Read the schema setup SQL
        schema_file = os.path.join(os.path.dirname(__file__), "..", "setup_rag_pipeline.sql")
        with open(schema_file, 'r') as f:
            sql_content = f.read()

        # Execute SQL via RPC (assuming there's a custom function)
        # For now, we'll provide the SQL for manual execution
        return {
            "success": True,
            "message": "Schema SQL ready - execute in Supabase SQL Editor",
            "sql": sql_content,
            "instructions": "Copy the SQL content and execute it in the Supabase SQL Editor to set up pgvector and RAG tables"
        }

    except Exception as e:
        logger.error(f"RAG schema setup error: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@app.post("/api/rag/embed-content")
async def embed_all_content():
    """Generate and store embeddings for all TLD evaluations and application questions"""
    try:
        from crewai_service.rag_embedder import rag_embedder

        logger.info("Starting RAG content embedding pipeline...")
        success = await rag_embedder.embed_all_content()

        if success:
            return {"success": True, "message": "All content embedded successfully"}
        else:
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": "Embedding pipeline failed"}
            )

    except Exception as e:
        logger.error(f"RAG embedding error: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@app.get("/api/rag/status")
async def rag_status():
    """Check RAG pipeline status and readiness"""
    try:
        from crewai_service.rag_embedder import rag_embedder
        from crewai_service.rag_search_tool import rag_search_tool

        # Check embedder status
        embedder_ready = rag_embedder.supabase is not None

        # Check search tool status
        search_ready = (getattr(rag_search_tool, '_openai_available', False) and
                       getattr(rag_search_tool, '_supabase_available', False))

        # Check if embeddings table exists
        table_exists = False
        embedding_count = 0
        try:
            result = rag_embedder.supabase.table('rag_embeddings').select('id').limit(1).execute()
            table_exists = True
            count_result = rag_embedder.supabase.table('rag_embeddings').select('id', count='exact').execute()
            embedding_count = count_result.count
        except Exception as e:
            table_exists = False

        return {
            "embedder_ready": embedder_ready,
            "search_tool_ready": search_ready,
            "table_exists": table_exists,
            "embedding_count": embedding_count,
            "openai_available": getattr(rag_search_tool, '_openai_available', False),
            "supabase_available": getattr(rag_search_tool, '_supabase_available', False),
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"RAG status check error: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


# Mount static files AFTER API routes but handle React Router properly
client_dist_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "client", "dist")
if os.path.exists(client_dist_path):
    logger.info(f"Mounting static files from {client_dist_path}")
    # Mount the entire dist directory to serve all static files with correct MIME types
    app.mount("/", StaticFiles(directory=client_dist_path, html=True), name="static")
else:
    logger.warning(f"Frontend dist directory not found at {client_dist_path}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))  # Default to 8000 for local development
    logger.info(f"Starting CrewAI TLD Evaluation Service on host 0.0.0.0 port {port}")
    logger.info(f"Frontend available at: http://0.0.0.0:{port}/")
    logger.info(f"API docs available at: http://0.0.0.0:{port}/docs")
    uvicorn.run(app, host="0.0.0.0", port=port) 