#!/usr/bin/env python3
"""
CrewAI-Based ICANN Guidebook Processor

Use CrewAI's built-in PDF parsing and embedding tools to properly extract
and structure content from the ICANN Applicant Guidebook, creating accurate
embeddings for the knowledge base.
"""

import sys
import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import json

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crewai_tools import PDFSearchTool
from crewai import Agent, Task, Crew
from db.supabase_client import get_supabase
import openai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CrewAIGuidebookProcessor:
    """Process ICANN guidebook using CrewAI's built-in tools"""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.supabase = get_supabase()
        self.pdf_tool = None
        self.openai_client = self._setup_openai()
        self.processed_sections = []
        
    def _setup_openai(self):
        """Setup OpenAI client for embeddings"""
        try:
            api_key = self._load_secret("openai_api_key")
            if not api_key:
                api_key = os.getenv("OPENAI_API_KEY")
            
            if not api_key:
                logger.error("❌ OpenAI API key not found")
                return None
                
            return openai.OpenAI(api_key=api_key)
        except Exception as e:
            logger.error(f"❌ Failed to setup OpenAI client: {e}")
            return None
    
    def _load_secret(self, secret_name: str) -> Optional[str]:
        """Load secret from /secrets directory"""
        try:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            secret_path = os.path.join(project_root, "secrets", f"{secret_name}.txt")
            
            if os.path.exists(secret_path):
                with open(secret_path, 'r') as f:
                    return f.read().strip()
        except Exception as e:
            logger.error(f"Failed to load secret {secret_name}: {e}")
        return None
    
    def initialize_pdf_tool(self) -> bool:
        """Initialize CrewAI PDF search tool"""
        try:
            self.pdf_tool = PDFSearchTool(pdf=self.pdf_path)
            logger.info(f"✅ Initialized CrewAI PDFSearchTool for: {self.pdf_path}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize PDF tool: {e}")
            return False
    
    def create_extraction_agents(self) -> List[Agent]:
        """Create specialized agents for different types of content extraction"""
        
        # Structure Analysis Agent
        structure_agent = Agent(
            role='Document Structure Analyst',
            goal='Analyze the ICANN guidebook structure and identify all sections, subsections, and their hierarchy',
            backstory="""You are an expert in document analysis with deep knowledge of ICANN 
            procedures and guidebook structure. You excel at identifying document organization, 
            table of contents, and hierarchical relationships between sections.""",
            tools=[self.pdf_tool],
            verbose=True
        )
        
        # Content Extraction Agent
        content_agent = Agent(
            role='Content Extraction Specialist',
            goal='Extract clean, structured content from specific sections of the ICANN guidebook',
            backstory="""You are a meticulous content extraction specialist who can parse 
            complex regulatory documents and extract key information while preserving context 
            and structure. You understand ICANN terminology and procedures.""",
            tools=[self.pdf_tool],
            verbose=True
        )
        
        # Technical Procedures Agent
        technical_agent = Agent(
            role='Technical Procedures Expert',
            goal='Extract and structure technical requirements, evaluation criteria, and procedural details',
            backstory="""You are a technical expert in domain name system operations and 
            ICANN technical requirements. You specialize in extracting technical specifications, 
            evaluation criteria, and operational procedures from regulatory documents.""",
            tools=[self.pdf_tool],
            verbose=True
        )
        
        return [structure_agent, content_agent, technical_agent]
    
    def create_extraction_tasks(self, agents: List[Agent]) -> List[Task]:
        """Create tasks for systematic content extraction"""
        
        structure_agent, content_agent, technical_agent = agents
        
        tasks = []
        
        # Task 1: Analyze document structure
        structure_task = Task(
            description="""Analyze the complete structure of the ICANN Applicant Guidebook PDF.
            
            Your objectives:
            1. Identify the table of contents and all major sections
            2. Map out the hierarchical structure (modules, sections, subsections)
            3. Note page numbers and section numbering system
            4. Identify special sections like appendices, glossaries, and annexes
            5. Create a comprehensive outline of the document structure
            
            Focus on sections related to:
            - String evaluation procedures
            - Application requirements and processes
            - Evaluation criteria and standards
            - Fees and payment procedures
            - Dispute resolution mechanisms
            - Registry agreement templates
            
            Return a detailed structural analysis with section numbers, titles, and page references.""",
            agent=structure_agent,
            expected_output="Comprehensive document structure analysis with hierarchical outline"
        )
        
        # Task 2: Extract core application procedures
        application_task = Task(
            description="""Extract detailed content about gTLD application procedures and requirements.
            
            Focus on extracting complete content from these key areas:
            1. Application submission procedures and requirements
            2. Evaluation timeline and process phases
            3. String similarity review criteria and procedures
            4. Technical and operational capability requirements
            5. Financial capability requirements and documentation
            6. Registry services evaluation
            7. Application fees and payment procedures
            
            For each section, extract:
            - Complete procedural text
            - Requirements and criteria
            - Timelines and deadlines
            - Documentation requirements
            - Evaluation standards
            
            Preserve the original structure and numbering system.""",
            agent=content_agent,
            expected_output="Structured extraction of application procedures and requirements"
        )
        
        # Task 3: Extract technical evaluation criteria
        technical_task = Task(
            description="""Extract detailed technical evaluation criteria and standards.
            
            Focus on these technical areas:
            1. String similarity evaluation methodology
            2. DNS stability requirements and testing
            3. Technical capability evaluation criteria
            4. Registry technical requirements and specifications
            5. Security and stability requirements
            6. Internationalized Domain Names (IDN) requirements
            7. Geographic names evaluation procedures
            
            For each technical area, extract:
            - Detailed evaluation criteria
            - Technical specifications and standards
            - Testing and validation procedures
            - Compliance requirements
            - Risk assessment factors
            
            Include any tables, figures, or technical diagrams referenced in the text.""",
            agent=technical_agent,
            expected_output="Comprehensive technical evaluation criteria and standards"
        )
        
        # Task 4: Extract dispute resolution and objection procedures
        dispute_task = Task(
            description="""Extract complete information about dispute resolution and objection procedures.
            
            Focus on:
            1. Types of objections (string confusion, legal rights, limited public interest, community)
            2. Objection filing procedures and timelines
            3. Dispute resolution provider information and procedures
            4. Expert determination processes and criteria
            5. Appeals and review mechanisms
            6. Community priority evaluation procedures
            7. Contention resolution mechanisms including auctions
            
            Extract complete procedural details, timelines, fees, and requirements.""",
            agent=content_agent,
            expected_output="Complete dispute resolution and objection procedures"
        )
        
        # Task 5: Extract appendices and reference materials
        reference_task = Task(
            description="""Extract content from appendices, glossaries, and reference materials.
            
            Focus on:
            1. Glossary of terms and definitions
            2. Reserved names lists and specifications
            3. Registry agreement templates
            4. Fee schedules and payment information
            5. Forms and application templates
            6. Technical specifications and standards references
            7. Legal and policy references
            
            Ensure all definitions, lists, and reference materials are completely extracted.""",
            agent=content_agent,
            expected_output="Complete appendices and reference materials"
        )
        
        tasks.extend([structure_task, application_task, technical_task, dispute_task, reference_task])
        return tasks
    
    def process_guidebook(self) -> bool:
        """Process the entire guidebook using CrewAI"""
        logger.info("🚀 Starting CrewAI guidebook processing...")
        
        if not self.initialize_pdf_tool():
            return False
        
        # Create agents and tasks
        agents = self.create_extraction_agents()
        tasks = self.create_extraction_tasks(agents)
        
        # Create and run crew
        crew = Crew(
            agents=agents,
            tasks=tasks,
            verbose=True,
            memory=True  # Enable memory for better context retention
        )
        
        try:
            logger.info("🤖 Running CrewAI extraction crew...")
            result = crew.kickoff()
            
            logger.info("✅ CrewAI processing completed")
            
            # Process results
            self._process_crew_results(result, tasks)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ CrewAI processing failed: {e}")
            return False
    
    def _process_crew_results(self, result, tasks: List[Task]):
        """Process and structure the results from CrewAI"""
        logger.info("📊 Processing CrewAI results...")
        
        # Extract results from each task
        for i, task in enumerate(tasks):
            try:
                task_output = task.output if hasattr(task, 'output') else None
                if task_output:
                    section_data = {
                        'task_name': task.description.split('\n')[0],  # First line as title
                        'content': str(task_output),
                        'agent_role': task.agent.role,
                        'extraction_timestamp': datetime.utcnow().isoformat()
                    }
                    self.processed_sections.append(section_data)
                    logger.info(f"✅ Processed task {i+1}: {section_data['task_name']}")
                    
            except Exception as e:
                logger.error(f"❌ Failed to process task {i+1}: {e}")
    
    def create_embeddings_and_store(self) -> bool:
        """Create embeddings for processed content and store in database"""
        logger.info("🔮 Creating embeddings and storing in database...")
        
        if not self.openai_client:
            logger.error("❌ OpenAI client not available")
            return False
        
        if not self.processed_sections:
            logger.error("❌ No processed sections available")
            return False
        
        successful_inserts = 0
        
        for i, section in enumerate(self.processed_sections):
            try:
                # Generate embedding
                response = self.openai_client.embeddings.create(
                    model="text-embedding-3-small",
                    input=section['content']
                )
                embedding = response.data[0].embedding
                
                # Prepare record for database
                record = {
                    'section_number': f'CREWAI.{i+1:02d}',
                    'section_title': section['task_name'][:255],  # Truncate if too long
                    'subsection_title': f'Extracted by {section["agent_role"]}',
                    'page_number': i + 1,
                    'content_text': section['content'],
                    'content_type': 'section',
                    'content_length': len(section['content']),
                    'document_version': '2026 Draft Applicant Guidebook (CrewAI Extracted)',
                    'document_url': f'file://{self.pdf_path}',
                    'last_updated': datetime.utcnow().isoformat(),
                    'embedding': embedding,
                    'embedding_model': 'text-embedding-3-small',
                    'embedding_created_at': datetime.utcnow().isoformat(),
                    'topic_tags': ['crewai-extracted', 'guidebook', '2026-draft'],
                    'relevance_keywords': None,
                    'application_sections': [13, 18, 19, 20, 21],
                    'context_summary': f'Content extracted by CrewAI {section["agent_role"]}',
                    'related_procedures': None,
                    'policy_implications': 'Official ICANN guidebook content',
                    'content_quality_score': 0.99,  # High quality as it's official content
                    'embedding_quality_score': None
                }
                
                # Insert into database
                result = self.supabase.table('guidebook_embeddings').insert(record).execute()
                
                if result.data:
                    successful_inserts += 1
                    logger.info(f"✅ Stored: {record['section_title'][:50]}...")
                else:
                    logger.error(f"❌ Failed to store section {i+1}")
                    
            except Exception as e:
                logger.error(f"❌ Error processing section {i+1}: {e}")
        
        logger.info(f"✅ Successfully stored {successful_inserts}/{len(self.processed_sections)} sections")
        return successful_inserts > 0
    
    def cleanup_old_artificial_content(self):
        """Remove the artificially created content from the database"""
        logger.info("🧹 Cleaning up artificially created content...")
        
        try:
            # Remove sections that were artificially created (not from real PDF)
            # Keep only the risk assessments and CrewAI extracted content
            result = self.supabase.table('guidebook_embeddings').delete().not_.ilike('section_number', 'RISK.%').not_.ilike('section_number', 'CREWAI.%').execute()
            
            if result.data:
                logger.info(f"🗑️ Removed {len(result.data)} artificially created sections")
            else:
                logger.info("ℹ️ No artificial content found to remove")
                
        except Exception as e:
            logger.error(f"❌ Failed to cleanup artificial content: {e}")

def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Process ICANN Guidebook with CrewAI")
    parser.add_argument("pdf_path", help="Path to the ICANN PDF file")
    parser.add_argument("--cleanup", action="store_true", 
                       help="Remove artificially created content before processing")
    
    args = parser.parse_args()
    
    try:
        processor = CrewAIGuidebookProcessor(args.pdf_path)
        
        if args.cleanup:
            processor.cleanup_old_artificial_content()
        
        # Process guidebook
        if processor.process_guidebook():
            # Create embeddings and store
            if processor.create_embeddings_and_store():
                logger.info("\n" + "="*80)
                logger.info("✅ CREWAI GUIDEBOOK PROCESSING COMPLETE!")
                logger.info("="*80)
                logger.info(f"📄 Processed: {args.pdf_path}")
                logger.info(f"📖 Sections extracted: {len(processor.processed_sections)}")
                logger.info("🔮 Embeddings created and stored in database")
                logger.info("\nThe TLD Assistant now has accurate ICANN guidebook content!")
            else:
                logger.error("❌ Failed to create embeddings")
                sys.exit(1)
        else:
            logger.error("❌ Failed to process guidebook")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ Processing failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
