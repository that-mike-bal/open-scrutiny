"""
TLD Application Store - Database operations for ICANN gTLD application management
Handles applicants, TLD applications, questions, and responses
"""

import logging
from typing import Dict, List, Optional, Any
from uuid import UUID
import json
from datetime import datetime

from .supabase_client import get_supabase

logger = logging.getLogger(__name__)

class TldApplicationStore:
    def __init__(self):
        self.supabase = get_supabase()

    # =====================================================
    # APPLICANT OPERATIONS
    # =====================================================
    
    def get_default_applicant(self) -> Optional[Dict[str, Any]]:
        """Get the first available applicant (used as default)"""
        try:
            response = self.supabase.table('applicants').select('*').limit(1).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error fetching default applicant: {e}")
            return None
    
    def get_applicant_by_id(self, applicant_id: str) -> Optional[Dict[str, Any]]:
        """Get an applicant by ID"""
        try:
            response = self.supabase.table('applicants').select('*').eq('id', applicant_id).single().execute()
            return response.data if response.data else None
        except Exception as e:
            logger.error(f"Error fetching applicant {applicant_id}: {e}")
            return None

    def create_applicant(self, applicant_data: Dict[str, Any]) -> Optional[str]:
        """Create a new applicant"""
        try:
            response = self.supabase.table('applicants').insert(applicant_data).execute()
            return response.data[0]['id'] if response.data else None
        except Exception as e:
            logger.error(f"Error creating applicant: {e}")
            return None

    # =====================================================
    # APPLICATION OPERATIONS
    # =====================================================
    
    def create_application(self, tld_string_id: str, applicant_id: str, application_data: Dict[str, Any]) -> Optional[str]:
        """Create a new TLD application"""
        try:
            # Build the application record
            app_record = {
                'applicant_id': applicant_id,
                'tld_string_id': tld_string_id,
                'internal_reference': application_data.get('internal_reference'),
                'tld_string': application_data.get('tld_string'),
                'application_type': application_data.get('application_type', 'standard'),
                'string_meaning': application_data.get('string_meaning'),
                'string_rationale': application_data.get('string_rationale'),
                'intended_use': application_data.get('intended_use'),
                'status': application_data.get('status', 'Draft')
            }
            
            response = self.supabase.table('tld_applications').insert(app_record).execute()
            return response.data[0]['id'] if response.data else None
        except Exception as e:
            logger.error(f"Error creating application: {e}")
            return None
    
    def get_application_by_string_id(self, tld_string_id: str) -> Optional[Dict[str, Any]]:
        """Get application for a specific TLD string"""
        try:
            response = self.supabase.table('tld_applications').select('*').eq('tld_string_id', tld_string_id).single().execute()
            return response.data if response.data else None
        except Exception as e:
            logger.error(f"Error fetching application for string {tld_string_id}: {e}")
            return None
    
    def get_application_with_details(self, application_id: str) -> Optional[Dict[str, Any]]:
        """Get full application details including applicant info"""
        try:
            response = self.supabase.table('tld_applications').select('''
                *,
                applicants!inner(legal_name, business_name, email),
                tld_strings!inner(tld_string, overall_status)
            ''').eq('id', application_id).single().execute()
            return response.data if response.data else None
        except Exception as e:
            logger.error(f"Error fetching application details: {e}")
            return None

    def update_application_status(self, application_id: str, status: str, completion_percentage: Optional[float] = None) -> bool:
        """Update application status and completion percentage"""
        try:
            update_data = {'status': status, 'updated_at': datetime.utcnow().isoformat()}
            if completion_percentage is not None:
                update_data['completion_percentage'] = completion_percentage
            
            response = self.supabase.table('tld_applications').update(update_data).eq('id', application_id).execute()
            return len(response.data) > 0
        except Exception as e:
            logger.error(f"Error updating application status: {e}")
            return False

    # =====================================================
    # QUESTION OPERATIONS
    # =====================================================
    
    def get_all_questions(self) -> List[Dict[str, Any]]:
        """Get all active application questions"""
        try:
            response = self.supabase.table('application_questions_enhanced').select('*').eq('is_active', True).order('question_number').execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Error fetching questions: {e}")
            return []
    
    def get_questions_by_section(self, section_name: str) -> List[Dict[str, Any]]:
        """Get questions for a specific section"""
        try:
            response = self.supabase.table('application_questions_enhanced').select('*').eq('section_name', section_name).eq('is_active', True).order('question_number').execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Error fetching questions for section {section_name}: {e}")
            return []
    
    def get_question_by_number(self, question_number: str) -> Optional[Dict[str, Any]]:
        """Get a specific question by its number"""
        try:
            response = self.supabase.table('application_questions_enhanced').select('*').eq('question_number', question_number).single().execute()
            return response.data if response.data else None
        except Exception as e:
            logger.error(f"Error fetching question {question_number}: {e}")
            return None

    # =====================================================
    # RESPONSE OPERATIONS
    # =====================================================
    
    def save_response(self, application_id: str, question_id: str, response_data: Dict[str, Any], source_task_executions: List[str] = None) -> Optional[str]:
        """Save an AI-generated or human-written response"""
        try:
            # Prepare the answer record (application_answers_enhanced schema)
            response_record = {
                'tld_application_id': application_id,
                'question_id': question_id,
                'answer_text': response_data.get('response_text') or response_data.get('answer_text'),
                'answer_html': response_data.get('response_html') or response_data.get('answer_html'),
                'answer_markdown': response_data.get('response_markdown') or response_data.get('answer_markdown'),
                'word_count': response_data.get('word_count'),
                'character_count': response_data.get('character_count'),
                'confidence_score': response_data.get('confidence_score'),
                'generation_method': response_data.get('generation_method', 'ai_generated'),
                'ai_model_used': response_data.get('ai_model_used'),
                'generated_at': response_data.get('generated_at', datetime.utcnow().isoformat()),
                'source_data_summary': response_data.get('source_description') or response_data.get('source_data_summary'),
                'review_status': response_data.get('review_status', 'draft')
            }

            # Add source evaluations if provided
            if source_task_executions:
                response_record['source_evaluations'] = json.dumps(source_task_executions)

            response = self.supabase.table('application_answers_enhanced').insert(response_record).execute()
            return response.data[0]['id'] if response.data else None
        except Exception as e:
            logger.error(f"Error saving response: {e}")
            return None
    
    def get_response(self, application_id: str, question_id: str, version: int = None) -> Optional[Dict[str, Any]]:
        """Get a specific response, optionally by version"""
        try:
            query = self.supabase.table('application_answers_enhanced').select('*').eq('tld_application_id', application_id).eq('question_id', question_id)
            
            if version:
                query = query.eq('version', version)
            else:
                query = query.order('version', desc=True).limit(1)
            
            response = query.execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error fetching response: {e}")
            return None
    
    def get_all_responses_for_application(self, application_id: str) -> List[Dict[str, Any]]:
        """Get all responses for an application with question details"""
        try:
            response = self.supabase.table('application_answers_enhanced').select('''
                *,
                application_questions_enhanced!inner(question_number, section_name, question_text, character_limit)
            ''').eq('tld_application_id', application_id).order('application_questions_enhanced.question_number').execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Error fetching responses for application: {e}")
            return []
    
    def update_response_status(self, response_id: str, review_status: str, review_notes: str = None, reviewed_by: str = None) -> bool:
        """Update response review status"""
        try:
            update_data = {
                'review_status': review_status,
                'reviewed_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            if review_notes:
                update_data['review_notes'] = review_notes
            if reviewed_by:
                update_data['reviewed_by'] = reviewed_by
            
            response = self.supabase.table('application_answers_enhanced').update(update_data).eq('id', response_id).execute()
            return len(response.data) > 0
        except Exception as e:
            logger.error(f"Error updating response status: {e}")
            return False

    # =====================================================
    # WORKFLOW INTEGRATION
    # =====================================================
    
    def get_source_evaluation_data(self, tld_string_id: str) -> Dict[str, Any]:
        """Get all evaluation data for a TLD string to inform response generation"""
        try:
            # Get the basic string info
            string_response = self.supabase.table('tld_strings').select('*').eq('id', tld_string_id).single().execute()
            string_data = string_response.data if string_response.data else {}
            
            # Get all task executions for this string
            tasks_response = self.supabase.table('task_executions').select('*').eq('tld_string_id', tld_string_id).eq('result_status', 'VERIFIED').execute()
            task_executions = tasks_response.data or []
            
            # Get Gemini reports if available
            gemini_tasks = [task for task in task_executions if task.get('task_name') == 'gemini_report_generation']
            
            return {
                'string_info': string_data,
                'task_executions': task_executions,
                'gemini_reports': gemini_tasks,
                'total_tasks': len(task_executions),
                'task_types': list(set(task.get('task_name', 'unknown') for task in task_executions))
            }
        except Exception as e:
            logger.error(f"Error fetching source evaluation data: {e}")
            return {}
    
    def create_response_generation_execution(self, application_id: str, workflow_data: Dict[str, Any]) -> Optional[str]:
        """Track a response generation workflow execution"""
        try:
            execution_record = {
                'tld_application_id': application_id,
                'workflow_type': workflow_data.get('workflow_type', 'application_response_generation'),
                'questions_targeted': workflow_data.get('questions_targeted', []),
                'input_data': json.dumps(workflow_data.get('input_data', {})),
                'prompt_template': workflow_data.get('prompt_template'),
                'status': workflow_data.get('status', 'PENDING'),
                'started_at': datetime.utcnow().isoformat()
            }
            
            response = self.supabase.table('response_generation_executions').insert(execution_record).execute()
            return response.data[0]['id'] if response.data else None
        except Exception as e:
            logger.error(f"Error creating response generation execution: {e}")
            return None
    
    def update_response_generation_execution(self, execution_id: str, update_data: Dict[str, Any]) -> bool:
        """Update a response generation execution with results"""
        try:
            update_record = {
                'updated_at': datetime.utcnow().isoformat(),
                **update_data
            }
            
            if update_data.get('status') == 'COMPLETED':
                update_record['completed_at'] = datetime.utcnow().isoformat()
            
            response = self.supabase.table('response_generation_executions').update(update_record).eq('id', execution_id).execute()
            return len(response.data) > 0
        except Exception as e:
            logger.error(f"Error updating response generation execution: {e}")
            return False

    # =====================================================
    # OVERVIEW AND REPORTING
    # =====================================================
    
    def get_application_overview(self, application_id: str = None) -> List[Dict[str, Any]]:
        """Get application overview using the database view"""
        try:
            query = self.supabase.table('application_overview').select('*')
            if application_id:
                query = query.eq('id', application_id)
            
            response = query.execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Error fetching application overview: {e}")
            return []
    
    def get_completion_status(self, application_id: str) -> Optional[Dict[str, Any]]:
        """Get completion status for an application"""
        try:
            response = self.supabase.table('application_completion_status').select('*').eq('application_id', application_id).single().execute()
            return response.data if response.data else None
        except Exception as e:
            logger.error(f"Error fetching completion status: {e}")
            return None