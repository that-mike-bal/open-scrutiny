#!/usr/bin/env python3
"""
Populate Application Question and External Resource Embeddings

This script creates embeddings for ICANN application questions and external resources
to enhance AI context and response generation.

Usage:
    python populate_application_embeddings.py --questions-only
    python populate_application_embeddings.py --resources-only  
    python populate_application_embeddings.py --all
"""

import os
import sys
import json
import argparse
import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import requests
from urllib.parse import urlparse

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import openai
from db.supabase_client import get_supabase

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ApplicationEmbeddingsPopulator:
    def __init__(self):
        self.supabase = get_supabase()
        self.openai_client = self._setup_openai()
        
    def _setup_openai(self):
        """Setup OpenAI client for embeddings"""
        try:
            api_key = self._load_secret("openai_api_key")
            if not api_key:
                api_key = os.getenv("OPENAI_API_KEY")
            
            if not api_key:
                logger.warning("OpenAI API key not found - embeddings will not be generated")
                return None
                
            return openai.OpenAI(api_key=api_key)
        except Exception as e:
            logger.error(f"Failed to setup OpenAI client: {e}")
            return None
    
    def _load_secret(self, secret_name: str) -> Optional[str]:
        """Read a credential from the environment (``SECRET_NAME`` upper-cased)."""
        value = os.getenv(secret_name.upper())
        return value.strip() if value and value.strip() else None
    
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text using OpenAI"""
        if not self.openai_client:
            return None
        
        try:
            # Truncate text if too long
            if len(text) > 8000:
                text = text[:8000] + "..."
            
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None
    
    def get_application_questions(self) -> List[Dict[str, Any]]:
        """Fetch all application questions from database"""
        try:
            response = self.supabase.table('application_questions').select('*').eq('is_active', True).execute()
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Failed to fetch application questions: {e}")
            return []
    
    def enhance_question_content(self, question: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance question with AI-friendly context and metadata"""
        
        question_text = question.get('question_text', '')
        section_name = question.get('section_name', '')
        question_number = question.get('question_number', '')
        
        # Generate enhanced content
        enhanced = {
            'question_context': self._generate_question_context(question_text, section_name, question_number),
            'expected_answer_type': self._classify_answer_type(question_text, section_name),
            'evaluation_criteria': self._generate_evaluation_criteria(question_text, section_name),
            'common_mistakes': self._generate_common_mistakes(question_text, section_name),
            'best_practices': self._generate_best_practices(question_text, section_name),
            'complexity_score': self._calculate_complexity_score(question_text, section_name),
            'topic_tags': self._classify_question_topics(question_text, section_name),
            'related_guidebook_sections': self._find_related_guidebook_sections(question_text, section_name),
            'reference_urls': self._extract_reference_urls(question_text, section_name),
            'completeness_score': 1.0,  # We'll calculate this based on available data
            'ai_readiness_score': 0.85   # Base score, can be improved
        }
        
        return enhanced
    
    def _generate_question_context(self, question_text: str, section_name: str, question_number: str) -> str:
        """Generate AI-friendly context for the question"""
        context_parts = [
            f"This is ICANN gTLD application question {question_number} from the {section_name} section."
        ]
        
        # Add context based on section
        section_contexts = {
            'Registry Services': 'This question evaluates the technical registry services and infrastructure capabilities.',
            'Technical Capability': 'This question assesses technical infrastructure, architecture, and operational capabilities.',
            'Operational Capability': 'This question examines operational procedures, processes, and management capabilities.',
            'Financial Capability': 'This question evaluates financial stability, projections, and business viability.',
            'Applicant Information': 'This question gathers basic information about the applicant organization.',
            'String Information': 'This question relates to the proposed TLD string and its characteristics.',
            'Mission/Purpose': 'This question explores the intended mission and purpose of the TLD.',
            'Community': 'This question assesses community-based applications and community support.',
            'Geographic Names': 'This question addresses geographic TLD applications and government support.',
            'Trademark Protection': 'This question covers trademark rights protection mechanisms.',
            'Continuing Operations': 'This question addresses business continuity and ongoing operations planning.'
        }
        
        if section_name in section_contexts:
            context_parts.append(section_contexts[section_name])
        
        # Add specific context based on question content
        if 'technical' in question_text.lower():
            context_parts.append("Requires detailed technical specifications and implementation plans.")
        if 'financial' in question_text.lower():
            context_parts.append("Requires financial documentation and business projections.")
        if 'describe' in question_text.lower():
            context_parts.append("Expects a comprehensive descriptive response.")
        if 'provide' in question_text.lower():
            context_parts.append("Requires specific documentation or detailed information.")
        
        return ' '.join(context_parts)
    
    def _classify_answer_type(self, question_text: str, section_name: str) -> str:
        """Classify the expected type of answer"""
        question_lower = question_text.lower()
        
        if 'financial' in question_lower or 'budget' in question_lower or 'cost' in question_lower:
            return 'financial_projection'
        elif 'technical' in question_lower or 'architecture' in question_lower or 'infrastructure' in question_lower:
            return 'technical_description'
        elif 'operational' in question_lower or 'procedure' in question_lower or 'process' in question_lower:
            return 'operational_plan'
        elif 'legal' in question_lower or 'policy' in question_lower or 'compliance' in question_lower:
            return 'legal_compliance'
        elif 'describe' in question_lower:
            return 'descriptive_response'
        elif 'provide' in question_lower or 'submit' in question_lower:
            return 'documentation'
        elif 'explain' in question_lower:
            return 'explanatory_response'
        else:
            return 'general_response'
    
    def _generate_evaluation_criteria(self, question_text: str, section_name: str) -> str:
        """Generate evaluation criteria based on question type"""
        criteria_templates = {
            'Registry Services': 'ICANN evaluates completeness of service descriptions, technical feasibility, compliance with standards, and operational readiness.',
            'Technical Capability': 'ICANN assesses technical architecture soundness, scalability, security measures, performance specifications, and implementation timeline.',
            'Operational Capability': 'ICANN reviews operational procedures, staffing plans, service level commitments, incident response capabilities, and business continuity planning.',
            'Financial Capability': 'ICANN evaluates financial stability, revenue projections, cost estimates, funding sources, and long-term viability.',
            'String Information': 'ICANN assesses string meaning, rationale, intended use, and potential for confusion or controversy.',
            'Community': 'ICANN evaluates community definition, support demonstration, policy development processes, and community benefit.',
            'Geographic Names': 'ICANN reviews government endorsement, geographic accuracy, cultural sensitivity, and public interest considerations.'
        }
        
        return criteria_templates.get(section_name, 'ICANN evaluates completeness, accuracy, feasibility, and compliance with application requirements.')
    
    def _generate_common_mistakes(self, question_text: str, section_name: str) -> str:
        """Generate common mistakes for this type of question"""
        mistake_templates = {
            'Registry Services': 'Common mistakes include vague service descriptions, unrealistic timelines, insufficient technical details, and lack of standards compliance.',
            'Technical Capability': 'Common mistakes include inadequate technical specifications, unrealistic performance claims, insufficient security measures, and poor scalability planning.',
            'Operational Capability': 'Common mistakes include vague operational procedures, inadequate staffing plans, unrealistic SLAs, and insufficient contingency planning.',
            'Financial Capability': 'Common mistakes include unrealistic financial projections, insufficient funding sources, inadequate cost estimates, and poor business model validation.',
            'String Information': 'Common mistakes include unclear string meaning, weak rationale, potential trademark conflicts, and insufficient community consultation.',
            'Community': 'Common mistakes include poorly defined community, insufficient support demonstration, weak governance structures, and unclear community benefit.',
            'Geographic Names': 'Common mistakes include insufficient government support, cultural insensitivity, unclear geographic scope, and inadequate public consultation.'
        }
        
        return mistake_templates.get(section_name, 'Common mistakes include insufficient detail, unrealistic claims, poor documentation, and failure to address evaluation criteria.')
    
    def _generate_best_practices(self, question_text: str, section_name: str) -> str:
        """Generate best practices for answering this question"""
        practice_templates = {
            'Registry Services': 'Best practices include detailed service specifications, clear implementation timelines, compliance documentation, and operational readiness demonstration.',
            'Technical Capability': 'Best practices include comprehensive technical architecture, realistic performance specifications, robust security measures, and scalability planning.',
            'Operational Capability': 'Best practices include detailed operational procedures, qualified staffing plans, realistic SLAs, and comprehensive contingency planning.',
            'Financial Capability': 'Best practices include conservative financial projections, diversified funding sources, detailed cost analysis, and validated business models.',
            'String Information': 'Best practices include clear string meaning, strong rationale, community consultation, and trademark clearance.',
            'Community': 'Best practices include precise community definition, broad support demonstration, transparent governance, and clear community benefit.',
            'Geographic Names': 'Best practices include strong government endorsement, cultural consultation, clear geographic boundaries, and public interest demonstration.'
        }
        
        return practice_templates.get(section_name, 'Best practices include thorough preparation, detailed responses, supporting documentation, and professional presentation.')
    
    def _calculate_complexity_score(self, question_text: str, section_name: str) -> float:
        """Calculate complexity score (0.0 to 1.0)"""
        complexity_factors = 0.0
        
        # Base complexity by section
        section_complexity = {
            'Applicant Information': 0.2,
            'String Information': 0.4,
            'Mission/Purpose': 0.3,
            'Registry Services': 0.8,
            'Technical Capability': 0.9,
            'Operational Capability': 0.7,
            'Financial Capability': 0.8,
            'Community': 0.6,
            'Geographic Names': 0.7,
            'Trademark Protection': 0.6,
            'Continuing Operations': 0.7
        }
        
        complexity_factors += section_complexity.get(section_name, 0.5)
        
        # Adjust based on question content
        question_lower = question_text.lower()
        if 'technical' in question_lower or 'architecture' in question_lower:
            complexity_factors += 0.2
        if 'financial' in question_lower or 'projection' in question_lower:
            complexity_factors += 0.2
        if 'detailed' in question_lower or 'comprehensive' in question_lower:
            complexity_factors += 0.1
        if 'provide' in question_lower and 'document' in question_lower:
            complexity_factors += 0.1
        
        return min(1.0, complexity_factors)
    
    def _classify_question_topics(self, question_text: str, section_name: str) -> List[str]:
        """Classify question topics"""
        topics = []
        question_lower = question_text.lower()
        
        # Section-based topics
        section_topics = {
            'Registry Services': ['registry-operations', 'technical'],
            'Technical Capability': ['technical', 'infrastructure', 'architecture'],
            'Operational Capability': ['operations', 'procedures', 'management'],
            'Financial Capability': ['financial', 'business', 'projections'],
            'String Information': ['string', 'naming'],
            'Community': ['community', 'governance'],
            'Geographic Names': ['geographic', 'government'],
            'Trademark Protection': ['trademark', 'legal', 'rights-protection'],
            'Continuing Operations': ['continuity', 'operations']
        }
        
        topics.extend(section_topics.get(section_name, []))
        
        # Content-based topics
        if 'dns' in question_lower:
            topics.append('dns')
        if 'security' in question_lower:
            topics.append('security')
        if 'performance' in question_lower:
            topics.append('performance')
        if 'policy' in question_lower:
            topics.append('policy')
        if 'legal' in question_lower:
            topics.append('legal')
        if 'compliance' in question_lower:
            topics.append('compliance')
        if 'service' in question_lower:
            topics.append('services')
        
        return list(set(topics))  # Remove duplicates
    
    def _find_related_guidebook_sections(self, question_text: str, section_name: str) -> List[str]:
        """Find related guidebook sections"""
        # This would ideally use semantic search on guidebook embeddings
        # For now, use section-based mapping
        
        section_mappings = {
            'Registry Services': ['1.1.1', '2.1', '2.2'],
            'Technical Capability': ['2.1', '2.2', '2.3'],
            'Operational Capability': ['2.1', '2.2', '3.1'],
            'Financial Capability': ['4.1', '4.2'],
            'String Information': ['1.1.2', '1.2'],
            'Community': ['1.2.3', '3.1'],
            'Geographic Names': ['1.2.1', '3.2.2'],
            'Trademark Protection': ['1.1.2', '3.3']
        }
        
        return section_mappings.get(section_name, [])
    
    def _extract_reference_urls(self, question_text: str, section_name: str) -> List[str]:
        """Extract or suggest reference URLs"""
        # Extract URLs from question text
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        urls = re.findall(url_pattern, question_text)
        
        # Add standard reference URLs based on section
        standard_references = {
            'Registry Services': [
                'https://www.icann.org/resources/pages/registry-services-2012-02-25-en',
                'https://www.iana.org/domains/special-use'
            ],
            'Technical Capability': [
                'https://tools.ietf.org/rfc/rfc1035.txt',
                'https://tools.ietf.org/rfc/rfc2181.txt',
                'https://www.icann.org/resources/pages/technical-requirements-2012-02-25-en'
            ],
            'Financial Capability': [
                'https://www.icann.org/resources/pages/financial-requirements-2012-02-25-en'
            ]
        }
        
        urls.extend(standard_references.get(section_name, []))
        return list(set(urls))  # Remove duplicates
    
    def create_question_embeddings(self, questions: List[Dict[str, Any]]) -> int:
        """Create embeddings for application questions"""
        logger.info(f"Creating embeddings for {len(questions)} application questions")
        created_count = 0
        
        for question in questions:
            try:
                # Check if embeddings already exist
                existing = self.supabase.table('application_question_embeddings').select('id').eq('application_question_id', question['id']).execute()
                if existing.data:
                    logger.info(f"Skipping question {question['question_number']} - embeddings already exist")
                    continue
                
                # Enhance question content
                enhanced = self.enhance_question_content(question)
                
                # Generate embeddings
                question_text_full = f"{question['question_text']} {question.get('question_description', '')} {enhanced['question_context']}"
                context_text_full = f"{enhanced['evaluation_criteria']} {enhanced['best_practices']} {enhanced['common_mistakes']}"
                
                question_embedding = self.generate_embedding(question_text_full)
                context_embedding = self.generate_embedding(context_text_full)
                
                if not question_embedding or not context_embedding:
                    logger.warning(f"Failed to generate embeddings for question {question['question_number']}")
                    continue
                
                # Prepare database record
                record = {
                    'application_question_id': question['id'],
                    'question_number': question['question_number'],
                    'section_number': question['section_number'],
                    'section_name': question['section_name'],
                    'sub_section': question.get('sub_section'),
                    'question_text': question['question_text'],
                    'question_description': question.get('question_description'),
                    'question_embedding': question_embedding,
                    'context_embedding': context_embedding,
                    **enhanced
                }
                
                # Insert into database
                response = self.supabase.table('application_question_embeddings').insert(record).execute()
                if response.data:
                    created_count += 1
                    logger.info(f"Created embeddings for question {question['question_number']}: {question.get('section_name', 'Unknown Section')}")
                else:
                    logger.error(f"Failed to save embeddings for question {question['question_number']}")
                    
            except Exception as e:
                logger.error(f"Error processing question {question.get('question_number', 'Unknown')}: {e}")
                continue
        
        logger.info(f"Successfully created embeddings for {created_count} questions")
        return created_count
    
    def create_sample_external_resources(self) -> int:
        """Create sample external resource embeddings"""
        sample_resources = [
            {
                'resource_url': 'https://tools.ietf.org/rfc/rfc1035.txt',
                'resource_title': 'RFC 1035 - Domain Names - Implementation and Specification',
                'resource_type': 'rfc',
                'resource_source': 'IETF',
                'resource_description': 'The foundational RFC defining the Domain Name System (DNS) implementation and specification.',
                'relevance_to_applications': 'Essential for understanding DNS technical requirements in gTLD applications.',
                'relevant_questions': ['19.1', '18a'],
                'application_sections': [18, 19, 20],
                'topic_tags': ['dns', 'technical', 'rfc', 'standards'],
                'authority_level': 5,
                'complexity_level': 4,
                'publication_date': '1987-11-01',
                'version': 'RFC 1035'
            },
            {
                'resource_url': 'https://www.icann.org/resources/pages/applicant-guidebook-2012-02-25-en',
                'resource_title': 'ICANN New gTLD Applicant Guidebook',
                'resource_type': 'icann_policy',
                'resource_source': 'ICANN',
                'resource_description': 'The official guidebook for new gTLD applications, containing all requirements and procedures.',
                'relevance_to_applications': 'The primary reference document for all gTLD application requirements.',
                'relevant_questions': ['18a', '19.1', '20.1', '21.1'],
                'application_sections': [18, 19, 20, 21],
                'topic_tags': ['icann', 'policy', 'applications', 'guidebook'],
                'authority_level': 5,
                'complexity_level': 3,
                'publication_date': '2012-02-25',
                'version': '2012'
            },
            {
                'resource_url': 'https://www.iana.org/domains/special-use',
                'resource_title': 'IANA Special Use Domain Names',
                'resource_type': 'technical_spec',
                'resource_source': 'IANA',
                'resource_description': 'Registry of special-use domain names that have specific technical or policy implications.',
                'relevance_to_applications': 'Important for understanding reserved names and string evaluation criteria.',
                'relevant_questions': ['18a'],
                'application_sections': [13, 14],
                'topic_tags': ['iana', 'reserved-names', 'dns', 'special-use'],
                'authority_level': 5,
                'complexity_level': 2,
                'publication_date': '2013-02-01',
                'version': 'Current'
            }
        ]
        
        logger.info(f"Creating {len(sample_resources)} sample external resource embeddings")
        created_count = 0
        
        for resource in sample_resources:
            try:
                # Check if resource already exists
                existing = self.supabase.table('external_resource_embeddings').select('id').eq('resource_url', resource['resource_url']).execute()
                if existing.data:
                    logger.info(f"Skipping resource {resource['resource_title']} - already exists")
                    continue
                
                # Generate embeddings
                title_text = f"{resource['resource_title']} {resource['resource_description']}"
                content_text = f"{resource['resource_description']} {resource['relevance_to_applications']}"
                relevance_text = f"{resource['relevance_to_applications']} Questions: {', '.join(resource['relevant_questions'])}"
                
                title_embedding = self.generate_embedding(title_text)
                content_embedding = self.generate_embedding(content_text)
                relevance_embedding = self.generate_embedding(relevance_text)
                
                if not all([title_embedding, content_embedding, relevance_embedding]):
                    logger.warning(f"Failed to generate embeddings for resource {resource['resource_title']}")
                    continue
                
                # Prepare database record
                record = {
                    **resource,
                    'title_embedding': title_embedding,
                    'content_embedding': content_embedding,
                    'relevance_embedding': relevance_embedding,
                    'content_quality_score': 0.9,
                    'relevance_score': 0.85,
                    'freshness_score': 0.8,
                    'extraction_status': 'manual',
                    'is_publicly_accessible': True
                }
                
                # Insert into database
                response = self.supabase.table('external_resource_embeddings').insert(record).execute()
                if response.data:
                    created_count += 1
                    logger.info(f"Created embeddings for resource: {resource['resource_title']}")
                else:
                    logger.error(f"Failed to save embeddings for resource {resource['resource_title']}")
                    
            except Exception as e:
                logger.error(f"Error processing resource {resource.get('resource_title', 'Unknown')}: {e}")
                continue
        
        logger.info(f"Successfully created embeddings for {created_count} external resources")
        return created_count

def main():
    parser = argparse.ArgumentParser(description='Populate application question and resource embeddings')
    parser.add_argument('--questions-only', action='store_true', help='Only process application questions')
    parser.add_argument('--resources-only', action='store_true', help='Only process external resources')
    parser.add_argument('--all', action='store_true', help='Process both questions and resources')
    
    args = parser.parse_args()
    
    if not any([args.questions_only, args.resources_only, args.all]):
        args.all = True  # Default to processing everything
    
    populator = ApplicationEmbeddingsPopulator()
    
    total_created = 0
    
    if args.questions_only or args.all:
        logger.info("Processing application questions...")
        questions = populator.get_application_questions()
        if questions:
            created = populator.create_question_embeddings(questions)
            total_created += created
        else:
            logger.warning("No application questions found")
    
    if args.resources_only or args.all:
        logger.info("Processing external resources...")
        created = populator.create_sample_external_resources()
        total_created += created
    
    logger.info(f"Total embeddings created: {total_created}")
    return 0 if total_created > 0 else 1

if __name__ == "__main__":
    exit(main())
