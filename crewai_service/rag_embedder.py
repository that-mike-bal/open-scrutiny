"""
RAG Embedding Pipeline for TLD Assistant
Chunks and embeds content based on guidebook sections and application questions
"""

import os
import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import openai
from supabase import create_client
import json
import re
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class ContentChunk:
    """Represents a chunk of content to be embedded"""
    content_type: str  # 'tld_evaluation', 'guidebook_section', 'application_qa', 'risk_analysis'
    source_id: str     # Reference to original record
    title: str         # Human readable title
    content: str       # The actual content to embed
    chunk_index: int   # For multi-chunk content
    metadata: Dict[str, Any]  # Additional metadata for filtering

class RAGEmbedder:
    """Handles chunking and embedding of content for RAG pipeline"""

    def __init__(self):
        self.setup_openai()
        self.setup_supabase()

    def setup_openai(self):
        """Initialize OpenAI client for embeddings"""
        try:
            api_key = os.getenv("OPENAI_API_KEY")

            if api_key:
                openai.api_key = api_key
                logger.info("OpenAI client initialized for embeddings")
            else:
                logger.error("OpenAI API key not found")
                self.openai_client = None
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI: {e}")
            self.openai_client = None

    def setup_supabase(self):
        """Initialize Supabase client"""
        try:
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_SERVICE_KEY")  # Need service key for embeddings

            if url and key:
                self.supabase = create_client(url, key)
                logger.info("Supabase client initialized for embeddings")
            else:
                logger.error("Supabase credentials not found")
                self.supabase = None
        except Exception as e:
            logger.error(f"Failed to initialize Supabase: {e}")
            self.supabase = None

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI"""
        try:
            response = await asyncio.to_thread(
                openai.Embedding.create,
                input=text,
                model="text-embedding-ada-002"
            )
            return response['data'][0]['embedding']
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return []

    def chunk_tld_evaluation(self, tld_data: Dict[str, Any]) -> List[ContentChunk]:
        """Chunk TLD evaluation data by risk categories and sections"""
        chunks = []
        tld_string = tld_data.get('tld_string', 'unknown')

        # Main evaluation summary
        if tld_data.get('generated_report'):
            report = tld_data['generated_report']
            if isinstance(report, dict):
                summary_content = f"""
TLD Evaluation Summary for .{tld_string}

Overall Status: {tld_data.get('status', 'Unknown')}
Risk Level: {report.get('risk_assessment', {}).get('risk_level', 'Not assessed')}
Use Case: {tld_data.get('use_case', 'General')}

Risk Assessment:
{json.dumps(report.get('risk_assessment', {}), indent=2)}

Evaluation Summary:
{report.get('report_content', 'No detailed report available')}
                """.strip()

                chunks.append(ContentChunk(
                    content_type='tld_evaluation',
                    source_id=tld_string,
                    title=f"TLD Evaluation Summary: .{tld_string}",
                    content=summary_content,
                    chunk_index=0,
                    metadata={
                        'tld_string': tld_string,
                        'risk_level': report.get('risk_assessment', {}).get('risk_level', 'UNKNOWN'),
                        'status': tld_data.get('status', 'UNKNOWN'),
                        'use_case': tld_data.get('use_case', 'general')
                    }
                ))

        # Individual task executions by category
        task_categories = {
            'technical': ['dns_stability_review', 'comprehensive_similarity_analysis', 'name_collision_assessment'],
            'legal': ['deep_research_legal_assessment', 'global_trademark_assessment', 'patent_conflict_assessment', 'legal_gut_check'],
            'policy': ['geographic_name_assessment', 'safeguard_assessment', 'gac_risk_analysis', 'cultural_linguistic_assessment']
        }

        for category, task_names in task_categories.items():
            category_tasks = [
                task for task in tld_data.get('task_executions', [])
                if task.get('task_name') in task_names
            ]

            if category_tasks:
                category_content = f"""
{category.title()} Risk Analysis for .{tld_string}

Tasks Completed: {len(category_tasks)}
Status: {', '.join([task.get('result_status', 'Unknown') for task in category_tasks])}

Detailed Results:
                """.strip()

                for task in category_tasks:
                    category_content += f"""

Task: {task.get('task_name', 'Unknown')}
Status: {task.get('result_status', 'Unknown')}
Result: {task.get('result_data', 'No result data')}
                    """.strip()

                chunks.append(ContentChunk(
                    content_type='risk_analysis',
                    source_id=f"{tld_string}_{category}",
                    title=f"{category.title()} Analysis: .{tld_string}",
                    content=category_content,
                    chunk_index=len(chunks),
                    metadata={
                        'tld_string': tld_string,
                        'risk_category': category,
                        'task_count': len(category_tasks),
                        'assessment_type': 'detailed_analysis'
                    }
                ))

        return chunks

    def chunk_application_questions(self, questions_data: List[Dict[str, Any]]) -> List[ContentChunk]:
        """Chunk application questions by guidebook sections"""
        chunks = []

        # Group questions by section
        sections = {}
        for question in questions_data:
            section_name = question.get('section_name', 'Unknown Section')
            if section_name not in sections:
                sections[section_name] = []
            sections[section_name].append(question)

        # Create chunks for each section
        for section_name, section_questions in sections.items():
            section_content = f"""
ICANN Guidebook Section: {section_name}

This section contains {len(section_questions)} application questions and requirements.

Questions and Requirements:
            """.strip()

            for i, question in enumerate(section_questions, 1):
                section_content += f"""

Q{i}: {question.get('question_text', 'No question text')}

Sub-section: {question.get('sub_section', 'General')}
Question Type: {question.get('question_type', 'Standard')}
                """.strip()

                if question.get('guidance_text'):
                    section_content += f"\nGuidance: {question['guidance_text']}"

                if question.get('example_answer'):
                    section_content += f"\nExample: {question['example_answer']}"

            chunks.append(ContentChunk(
                content_type='application_qa',
                source_id=section_name,
                title=f"ICANN Application Section: {section_name}",
                content=section_content,
                chunk_index=0,
                metadata={
                    'section_name': section_name,
                    'question_count': len(section_questions),
                    'question_types': list(set([q.get('question_type', 'standard') for q in section_questions]))
                }
            ))

        return chunks

    async def store_embeddings(self, chunks: List[ContentChunk]) -> bool:
        """Store content chunks and their embeddings in Supabase"""
        if not self.supabase:
            logger.error("Supabase not initialized")
            return False

        try:
            for chunk in chunks:
                # Generate embedding
                embedding = await self.generate_embedding(chunk.content)
                if not embedding:
                    logger.warning(f"Failed to generate embedding for {chunk.title}")
                    continue

                # Store in database
                result = self.supabase.table('rag_embeddings').insert({
                    'content_type': chunk.content_type,
                    'source_id': chunk.source_id,
                    'title': chunk.title,
                    'content': chunk.content,
                    'chunk_index': chunk.chunk_index,
                    'metadata': chunk.metadata,
                    'embedding': embedding
                }).execute()

                if result.data:
                    logger.info(f"Stored embedding for: {chunk.title}")
                else:
                    logger.error(f"Failed to store embedding for: {chunk.title}")

            return True
        except Exception as e:
            logger.error(f"Error storing embeddings: {e}")
            return False

    async def embed_all_evaluations(self) -> bool:
        """Embed all TLD evaluations from the database"""
        if not self.supabase:
            return False

        try:
            # Get all TLD evaluations
            result = self.supabase.table('tld_strings').select('*').execute()

            all_chunks = []
            for tld_data in result.data:
                chunks = self.chunk_tld_evaluation(tld_data)
                all_chunks.extend(chunks)

            logger.info(f"Generated {len(all_chunks)} chunks from {len(result.data)} TLD evaluations")

            # Store embeddings
            success = await self.store_embeddings(all_chunks)
            return success

        except Exception as e:
            logger.error(f"Error embedding evaluations: {e}")
            return False

    async def embed_application_questions(self) -> bool:
        """Embed all application questions from the database"""
        if not self.supabase:
            return False

        try:
            # Get all application questions
            result = self.supabase.table('application_questions').select('*').execute()

            chunks = self.chunk_application_questions(result.data)
            logger.info(f"Generated {len(chunks)} chunks from application questions")

            # Store embeddings
            success = await self.store_embeddings(chunks)
            return success

        except Exception as e:
            logger.error(f"Error embedding application questions: {e}")
            return False

    async def embed_all_content(self) -> bool:
        """Embed all available content"""
        logger.info("Starting full content embedding pipeline...")

        # Clear existing embeddings
        if self.supabase:
            self.supabase.table('rag_embeddings').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()

        success = True

        # Embed TLD evaluations
        logger.info("Embedding TLD evaluations...")
        if not await self.embed_all_evaluations():
            success = False

        # Embed application questions
        logger.info("Embedding application questions...")
        if not await self.embed_application_questions():
            success = False

        logger.info(f"Content embedding pipeline {'completed successfully' if success else 'completed with errors'}")
        return success

# Global instance
rag_embedder = RAGEmbedder()