#!/usr/bin/env python3
"""
Setup RAG Database with Required Content Types
Creates the similarity_search function and populates RAG content for application generation
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from crewai_service.utils.supabase_client import get_supabase_client
from openai import OpenAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGDatabaseSetup:
    def __init__(self):
        self.supabase_wrapper = get_supabase_client()
        self.supabase = self.supabase_wrapper.client  # Access the underlying client for RPC calls
        self.setup_openai()
        
    def setup_openai(self):
        """Initialize OpenAI for generating embeddings"""
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                secrets_dir = project_root / "secrets"
                openai_key_file = secrets_dir / "openai_api_key.txt"
                if openai_key_file.exists():
                    with open(openai_key_file, 'r') as f:
                        api_key = f.read().strip()

            if api_key:
                self.openai_client = OpenAI(api_key=api_key)
                logger.info("OpenAI configured for embedding generation")
            else:
                raise ValueError("OpenAI API key not found")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI: {e}")
            raise

    async def create_similarity_search_function(self):
        """Create the PostgreSQL similarity_search function"""
        logger.info("Creating similarity_search PostgreSQL function...")
        
        function_sql = """
-- Enable pgvector extension if not exists
CREATE EXTENSION IF NOT EXISTS vector;

-- Drop existing function if it exists
DROP FUNCTION IF EXISTS similarity_search(vector, float, int, text, jsonb);

-- Create the similarity_search function
CREATE OR REPLACE FUNCTION similarity_search(
    query_embedding vector(1536),
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 5,
    filter_content_type text DEFAULT NULL,
    filter_metadata jsonb DEFAULT NULL
)
RETURNS TABLE (
    id uuid,
    content text,
    title text,
    content_type text,
    source_id text,
    metadata jsonb,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        rag_content.id,
        rag_content.content,
        rag_content.title,
        rag_content.content_type,
        rag_content.source_id,
        rag_content.metadata,
        1 - (rag_content.embedding <=> query_embedding) AS similarity
    FROM rag_content
    WHERE 
        (1 - (rag_content.embedding <=> query_embedding)) > match_threshold
        AND (filter_content_type IS NULL OR rag_content.content_type = filter_content_type)
        AND (filter_metadata IS NULL OR rag_content.metadata @> filter_metadata)
    ORDER BY rag_content.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
        """
        
        try:
            # Execute the function creation using raw SQL
            response = self.supabase.rpc('exec_sql', {'sql': function_sql}).execute()
            logger.info("✅ similarity_search function created successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Error creating similarity_search function: {e}")
            # Try alternative approach using direct SQL execution
            try:
                # Split into individual statements for better error handling
                statements = [stmt.strip() for stmt in function_sql.split(';') if stmt.strip()]
                for statement in statements:
                    if statement:
                        self.supabase.rpc('exec_sql', {'sql': statement + ';'}).execute()
                        logger.info(f"Executed: {statement[:50]}...")
                
                logger.info("✅ similarity_search function created successfully (alternative method)")
                return True
            except Exception as e2:
                logger.error(f"❌ Alternative method also failed: {e2}")
                return False

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text content"""
        try:
            response = await asyncio.to_thread(
                self.openai_client.embeddings.create,
                input=text,
                model="text-embedding-ada-002"
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return []

    async def create_rag_content_table(self):
        """Create the rag_content table if it doesn't exist"""
        logger.info("Creating rag_content table...")
        
        table_sql = """
CREATE TABLE IF NOT EXISTS rag_content (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    content text NOT NULL,
    title text NOT NULL,
    content_type text NOT NULL,
    source_id text,
    metadata jsonb DEFAULT '{}',
    embedding vector(1536),
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS rag_content_embedding_idx ON rag_content USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS rag_content_content_type_idx ON rag_content (content_type);
CREATE INDEX IF NOT EXISTS rag_content_source_id_idx ON rag_content (source_id);
CREATE INDEX IF NOT EXISTS rag_content_metadata_idx ON rag_content USING gin (metadata);
        """
        
        try:
            self.supabase.rpc('exec_sql', {'sql': table_sql}).execute()
            logger.info("✅ rag_content table created successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Error creating rag_content table: {e}")
            return False

    async def populate_applicant_data(self):
        """Populate Example Registry applicant data as RAG content"""
        logger.info("Populating Example Registry applicant data...")
        
        try:
            # Get all applicants from the database
            applicants_response = self.supabase_wrapper.table('applicants').select('*').execute()
            applicants = applicants_response.data or []
            
            logger.info(f"Found {len(applicants)} applicants to process")
            
            for applicant in applicants:
                # Format applicant data as searchable content
                content = self._format_applicant_for_rag(applicant)
                title = f"Example Registry Applicant: {applicant.get('legal_name', applicant['id'])}"
                
                # Generate embedding
                embedding = await self.generate_embedding(content)
                if not embedding:
                    logger.warning(f"Failed to generate embedding for applicant {applicant['id']}")
                    continue
                
                # Prepare metadata
                metadata = {
                    'applicant_id': applicant['id'],
                    'legal_name': applicant.get('legal_name', ''),
                    'business_name': applicant.get('business_name', ''),
                    'entity_type': applicant.get('entity_type', ''),
                    'jurisdiction': applicant.get('jurisdiction', '')
                }
                
                # Insert into rag_content
                rag_data = {
                    'content': content,
                    'title': title,
                    'content_type': 'applicant_data',
                    'source_id': applicant['id'],
                    'metadata': metadata,
                    'embedding': embedding
                }
                
                self.supabase_wrapper.table('rag_content').upsert(rag_data, on_conflict='source_id,content_type').execute()
                logger.info(f"✅ Added RAG content for applicant: {applicant.get('legal_name', applicant['id'])}")
            
            logger.info(f"✅ Successfully populated {len(applicants)} Example Registry entries")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error populating Example Registry data: {e}")
            return False

    def _format_applicant_for_rag(self, applicant: Dict[str, Any]) -> str:
        """Format applicant data for RAG search"""
        # Extract key information for searchable content
        sections = []
        
        # Basic information
        sections.append(f"Legal Name: {applicant.get('legal_name', 'N/A')}")
        sections.append(f"Business Name: {applicant.get('business_name', 'N/A')}")
        sections.append(f"Entity Type: {applicant.get('entity_type', 'N/A')}")
        sections.append(f"Jurisdiction: {applicant.get('jurisdiction', 'N/A')}")
        
        if applicant.get('incorporation_date'):
            sections.append(f"Incorporation Date: {applicant['incorporation_date']}")
        
        # Contact information
        if applicant.get('business_address'):
            sections.append(f"Business Address: {applicant['business_address']}")
        if applicant.get('mailing_address'):
            sections.append(f"Mailing Address: {applicant['mailing_address']}")
        if applicant.get('phone'):
            sections.append(f"Phone: {applicant['phone']}")
        if applicant.get('email'):
            sections.append(f"Email: {applicant['email']}")
        if applicant.get('website'):
            sections.append(f"Website: {applicant['website']}")
            
        # Financial information
        if applicant.get('funding_sources'):
            sections.append(f"Funding Sources: {applicant['funding_sources']}")
        if applicant.get('annual_revenue'):
            sections.append(f"Annual Revenue: {applicant['annual_revenue']}")
        if applicant.get('total_assets'):
            sections.append(f"Total Assets: {applicant['total_assets']}")
            
        # Key personnel
        if applicant.get('key_personnel'):
            personnel_text = "Key Personnel: "
            for person in applicant['key_personnel']:
                personnel_text += f"{person.get('name', 'N/A')} ({person.get('title', 'N/A')}) - {person.get('role', 'N/A')}; "
            sections.append(personnel_text.rstrip('; '))
            
        # Registry experience
        if applicant.get('current_tlds'):
            sections.append(f"Current TLDs: {', '.join(applicant['current_tlds'])}")
        if applicant.get('registry_experience_description'):
            sections.append(f"Registry Experience: {applicant['registry_experience_description']}")
            
        return "\n\n".join(sections)

    async def populate_question_guidance(self):
        """Populate ICANN application question guidance"""
        logger.info("Populating question guidance...")
        
        # Read application questions data
        questions_file = project_root / "data" / "application_questions.md"
        if not questions_file.exists():
            logger.warning("application_questions.md not found, skipping question guidance")
            return False
        
        try:
            with open(questions_file, 'r', encoding='utf-8') as f:
                questions_content = f.read()
            
            # Parse sections and create guidance entries
            sections = self._parse_questions_for_guidance(questions_content)
            
            for section in sections:
                embedding = await self.generate_embedding(section['content'])
                if not embedding:
                    continue
                
                rag_data = {
                    'content': section['content'],
                    'title': section['title'],
                    'content_type': 'question_guidance',
                    'source_id': section['question_id'],
                    'metadata': section['metadata'],
                    'embedding': embedding
                }
                
                self.supabase_wrapper.table('rag_content').upsert(rag_data, on_conflict='source_id,content_type').execute()
                logger.info(f"✅ Added guidance for {section['question_id']}")
            
            logger.info(f"✅ Successfully populated {len(sections)} question guidance entries")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error populating question guidance: {e}")
            return False

    def _parse_questions_for_guidance(self, content: str) -> List[Dict[str, Any]]:
        """Parse application questions content to create guidance entries"""
        sections = []
        lines = content.split('\n')
        current_section = None
        current_question = None
        
        for line in lines:
            line = line.strip()
            
            # Detect new sections
            if line.startswith('## ') and 'Question' in line:
                if current_section:
                    sections.append(current_section)
                    
                question_id = line.split(' ')[1] if len(line.split(' ')) > 1 else 'Unknown'
                current_section = {
                    'question_id': question_id,
                    'title': f"ICANN Application Question {question_id} Guidance",
                    'content': line + '\n',
                    'metadata': {
                        'question_id': question_id,
                        'section_type': 'application_question'
                    }
                }
            elif current_section:
                current_section['content'] += line + '\n'
        
        # Add final section
        if current_section:
            sections.append(current_section)
            
        # Clean up content and create comprehensive guidance
        for section in sections:
            section['content'] = self._create_question_guidance_content(section)
            
        return sections

    def _create_question_guidance_content(self, section: Dict[str, Any]) -> str:
        """Create comprehensive guidance content for a question"""
        original_content = section['content']
        question_id = section['question_id']
        
        # Extract key information
        guidance_content = f"""ICANN Application Question {question_id} - Complete Guidance

{original_content}

ANSWERING GUIDELINES:
- This question requires specific information based on your applicant entity
- Use Example Registry applicant data when available for entity-specific questions
- Ensure answers comply with ICANN requirements and character limits
- Professional tone and accurate information are essential
- Consider public posting requirements if applicable

DATA SOURCES:
- For entity information: Use Example Registry applicant database
- For technical capability: Reference TLD evaluation and risk assessments  
- For compliance: Reference ICANN Guidebook requirements
- For financial data: Use applicant financial records and projections

COMMON REQUIREMENTS:
- Legal entity details must be accurate and verifiable
- Contact information should be current and professional
- Technical specifications must meet ICANN standards
- Financial projections should be realistic and well-documented
        """
        
        return guidance_content

    async def populate_answer_templates(self):
        """Populate answer templates for common question types"""
        logger.info("Populating answer templates...")
        
        templates = [
            {
                'title': 'Legal Entity Information Template',
                'content': '''Legal Entity Name: [Full Legal Name]
Entity Type: [Corporation/LLC/Partnership/etc.]
Jurisdiction of Incorporation: [Country/State]
Incorporation Date: [Date]
Registration Number: [Company Registration Number]
Business Address: [Full Address]
Mailing Address: [If different from business address]

Primary Contact:
Name: [Contact Person]
Title: [Position]
Email: [Professional Email]
Phone: [Direct Phone Number]

Legal Entity Identifier (LEI): [LEI Number if applicable]
Website: [Company Website URL]''',
                'metadata': {
                    'question_types': ['entity_information', 'legal_structure', 'contact_details'],
                    'template_type': 'legal_entity',
                    'format': 'structured_list'
                }
            },
            {
                'title': 'Technical Capability Statement Template',
                'content': '''Technical Infrastructure Overview:
Our organization demonstrates comprehensive technical capability through:

1. DNS Infrastructure
   - Primary DNS Servers: [Details]
   - Secondary DNS Servers: [Details]
   - DNSSEC Implementation: [Yes/No with details]

2. Registry System Architecture
   - Registry Software: [Software platform]
   - Database Systems: [Database technology]
   - Redundancy and Backup: [Backup procedures]

3. Security Measures
   - Access Controls: [Security protocols]
   - Data Protection: [Encryption and security]
   - Monitoring Systems: [Security monitoring]

4. Operational Experience
   - Team Qualifications: [Experience summary]
   - Previous Registry Operations: [If applicable]
   - Technical Certifications: [Relevant certifications]''',
                'metadata': {
                    'question_types': ['technical_capability', 'infrastructure', 'security'],
                    'template_type': 'technical_overview',
                    'format': 'structured_sections'
                }
            },
            {
                'title': 'Financial Capability Statement Template',
                'content': '''Financial Capability and Projections:

Current Financial Position:
- Annual Revenue: [Amount in USD]
- Total Assets: [Amount in USD]  
- Operating Capital: [Available capital]
- Funding Sources: [Primary funding sources]

Registry Investment Plan:
- Initial Investment: [Amount for setup]
- Operating Costs (Year 1): [Projected costs]
- Projected Revenue (Year 1): [Revenue projections]
- Break-even Analysis: [When break-even expected]

Financial Commitments:
- Registry Operations: [Long-term funding commitment]
- Technical Infrastructure: [Infrastructure investment]
- Compliance and Legal: [Compliance costs]

Supporting Documentation:
- Audited Financial Statements: [Available/Attached]
- Banking Relationships: [Primary banking institutions]
- Insurance Coverage: [Relevant insurance policies]''',
                'metadata': {
                    'question_types': ['financial_capability', 'business_model', 'projections'],
                    'template_type': 'financial_overview',
                    'format': 'structured_sections'
                }
            }
        ]
        
        try:
            for template in templates:
                embedding = await self.generate_embedding(template['content'])
                if not embedding:
                    continue
                
                rag_data = {
                    'content': template['content'],
                    'title': template['title'],
                    'content_type': 'answer_templates',
                    'source_id': template['title'].lower().replace(' ', '_'),
                    'metadata': template['metadata'],
                    'embedding': embedding
                }
                
                self.supabase_wrapper.table('rag_content').upsert(rag_data, on_conflict='source_id,content_type').execute()
                logger.info(f"✅ Added template: {template['title']}")
            
            logger.info(f"✅ Successfully populated {len(templates)} answer templates")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error populating answer templates: {e}")
            return False

    async def verify_setup(self):
        """Verify RAG database setup is working correctly"""
        logger.info("Verifying RAG database setup...")
        
        try:
            # Test similarity search function
            test_embedding = [0.1] * 1536  # Dummy embedding for testing
            
            result = self.supabase.rpc('similarity_search', {
                'query_embedding': test_embedding,
                'match_threshold': 0.1,
                'match_count': 3
            }).execute()
            
            if result.data is not None:
                logger.info("✅ similarity_search function is working")
                
                # Count content by type
                for content_type in ['applicant_data', 'question_guidance', 'answer_templates']:
                    count_response = self.supabase.table('rag_content').select('id', count='exact').eq('content_type', content_type).execute()
                    count = count_response.count or 0
                    logger.info(f"✅ {content_type}: {count} entries")
                
                return True
            else:
                logger.error("❌ similarity_search function returned no data")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error verifying RAG setup: {e}")
            return False

async def main():
    """Main setup function"""
    logger.info("Starting RAG Database Setup...")
    
    setup = RAGDatabaseSetup()
    
    # Step 1: Create rag_content table
    if not await setup.create_rag_content_table():
        logger.error("Failed to create rag_content table")
        return
    
    # Step 2: Create similarity_search function
    if not await setup.create_similarity_search_function():
        logger.error("Failed to create similarity_search function")
        return
    
    # Step 3: Populate content
    logger.info("Populating RAG content...")
    
    await setup.populate_applicant_data()
    await setup.populate_question_guidance()
    await setup.populate_answer_templates()
    
    # Step 4: Verify setup
    if await setup.verify_setup():
        logger.info("🎉 RAG Database Setup Complete!")
        logger.info("The application generation system is now fully functional with vector search capabilities.")
    else:
        logger.error("Setup verification failed")

if __name__ == "__main__":
    asyncio.run(main())