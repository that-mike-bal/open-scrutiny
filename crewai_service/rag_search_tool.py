"""
RAG Vector Search Tool for TLD Assistant Chat Agent
Replaces direct database queries with intelligent semantic search
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from openai import OpenAI
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from supabase import create_client
import os
import json
from crewai_service.utils.logged_requests import logged_openai_call, logged_supabase_rpc

logger = logging.getLogger(__name__)

class RAGSearchInput(BaseModel):
    """Input schema for RAG search tool"""
    query: str = Field(..., description="User's question or search query")
    content_types: Optional[List[str]] = Field(
        default=None,
        description="Filter by content types: ['tld_evaluation', 'guidebook_section', 'application_qa', 'risk_analysis', 'applicant_data', 'question_guidance', 'answer_templates']"
    )
    tld_string: Optional[str] = Field(
        default=None,
        description="Filter results for specific TLD string (e.g., 'btc', 'dao')"
    )
    question_id: Optional[str] = Field(
        default=None,
        description="Filter results for specific ICANN application question ID (e.g., 'Q7', 'Q18a')"
    )
    application_id: Optional[str] = Field(
        default=None,
        description="Application ID for context-aware searches"
    )
    applicant_id: Optional[str] = Field(
        default=None,
        description="Applicant ID for Example Registry data searches"
    )
    format_for_icann: bool = Field(
        default=False,
        description="Format output for direct copy-paste into ICANN application tools"
    )
    limit: int = Field(default=5, description="Maximum number of results to return")

class RAGVectorSearchTool(BaseTool):
    """
    Semantic search tool using pgvector for intelligent content retrieval.

    This tool replaces manual SQL queries with semantic similarity search across:
    - TLD evaluations and risk assessments
    - ICANN Guidebook sections and requirements
    - Application questions and guidance
    - Risk analysis and compliance data

    Use this for ANY question about TLD evaluations, applications, or ICANN processes.
    """

    name: str = "RAG Vector Search"
    description: str = """
    Intelligent semantic search across TLD evaluation data, ICANN guidebook content, application requirements, and Example Registry applicant data.

    Use this tool for:
    - "What strings have high trademark risk?"
    - "How do I prepare for technical evaluation?"
    - "What are the requirements for geographic strings?"
    - "Show me similar risk assessments to .bitcoin"
    - "What ICANN policies apply to financial TLDs?"
    - "Get Example Registry entity information for applicant"
    - "Find question-specific guidance for Q18a"
    - "Generate answer template for financial capability questions"

    The tool automatically finds the most relevant content using semantic similarity,
    and can format results for direct copy-paste into ICANN application tools.
    """
    args_schema: type[BaseModel] = RAGSearchInput

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Use object.__setattr__ to bypass Pydantic validation for internal state
        object.__setattr__(self, '_clients_ready', False)
        self.setup_clients()

    def setup_clients(self):
        """Initialize OpenAI and Supabase clients"""
        # Setup OpenAI for embeddings
        try:
            api_key = os.getenv("OPENAI_API_KEY")

            if api_key:
                object.__setattr__(self, '_openai_client', OpenAI(api_key=api_key))
                object.__setattr__(self, '_openai_available', True)
                logger.info("OpenAI initialized for RAG search")
            else:
                object.__setattr__(self, '_openai_available', False)
                logger.error("OpenAI API key not found for RAG search")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI: {e}")
            object.__setattr__(self, '_openai_available', False)

        # Setup Supabase
        try:
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY")

            if url and key:
                object.__setattr__(self, '_supabase', create_client(url, key))
                object.__setattr__(self, '_supabase_available', True)
                logger.info("Supabase initialized for RAG search")
            else:
                object.__setattr__(self, '_supabase_available', False)
                logger.error("Supabase credentials not found for RAG search")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase: {e}")
            object.__setattr__(self, '_supabase_available', False)

    async def generate_query_embedding(self, query: str) -> List[float]:
        """Generate embedding for search query"""
        try:
            client = getattr(self, '_openai_client', None)
            if not client:
                return []
                
            response = await asyncio.to_thread(
                logged_openai_call,
                'RAGSearchTool',
                client.embeddings.create,
                input=query,
                model="text-embedding-ada-002"
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating query embedding: {e}")
            return []

    def _run(self, query: str, content_types: Optional[List[str]] = None,
             tld_string: Optional[str] = None, question_id: Optional[str] = None,
             application_id: Optional[str] = None, applicant_id: Optional[str] = None,
             format_for_icann: bool = False, limit: int = 5) -> str:
        """Synchronous wrapper for async search"""
        return asyncio.run(self._async_run(
            query=query,
            content_types=content_types,
            tld_string=tld_string,
            question_id=question_id,
            application_id=application_id,
            applicant_id=applicant_id,
            format_for_icann=format_for_icann,
            limit=limit
        ))

    async def _async_run(self, query: str, content_types: Optional[List[str]] = None,
                        tld_string: Optional[str] = None, question_id: Optional[str] = None,
                        application_id: Optional[str] = None, applicant_id: Optional[str] = None,
                        format_for_icann: bool = False, limit: int = 5) -> str:
        """Perform semantic search and return formatted results"""

        if not getattr(self, '_openai_available', False) or not getattr(self, '_supabase_available', False):
            return "RAG search unavailable - missing API keys or database connection"

        try:
            # Generate embedding for the query
            query_embedding = await self.generate_query_embedding(query)
            if not query_embedding:
                return "Failed to generate query embedding"

            # Build metadata filter
            metadata_filter = {}
            if tld_string:
                metadata_filter['tld_string'] = tld_string
            if question_id:
                metadata_filter['question_id'] = question_id
            if application_id:
                metadata_filter['application_id'] = application_id
            if applicant_id:
                metadata_filter['applicant_id'] = applicant_id

            # Auto-route content types based on query context
            if not content_types:
                content_types = self._auto_detect_content_types(query, question_id, applicant_id)

            # Prepare the similarity search
            search_params = {
                'query_embedding': query_embedding,
                'match_threshold': 0.7,
                'match_count': limit,
                'filter_content_type': content_types[0] if content_types and len(content_types) == 1 else None,
                'filter_metadata': metadata_filter if metadata_filter else {}
            }

            # Execute similarity search using the PostgreSQL function
            result = logged_supabase_rpc('RAGSearchTool', getattr(self, '_supabase'), 'similarity_search', search_params)

            if not result.data:
                return f"No relevant content found for: {query}"

            # Format results based on context
            if format_for_icann:
                return self._format_for_icann_application(result.data, query, question_id)
            else:
                return self._format_for_chat(result.data, query)

        except Exception as e:
            logger.error(f"RAG search error: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return f"Search error: {str(e)}"

    def _auto_detect_content_types(self, query: str, question_id: Optional[str] = None, 
                                  applicant_id: Optional[str] = None) -> List[str]:
        """Auto-detect appropriate content types based on query context"""
        query_lower = query.lower()
        detected_types = []

        # Entity/applicant data queries
        if applicant_id or any(term in query_lower for term in ['entity', 'applicant', 'company', 'contact', 'address', 'legal name']):
            detected_types.append('applicant_data')

        # Question-specific guidance
        if question_id or any(term in query_lower for term in ['question', 'guidance', 'how to answer', 'requirements']):
            detected_types.append('question_guidance')

        # Risk evaluation queries
        if any(term in query_lower for term in ['risk', 'evaluation', 'assessment', 'trademark', 'collision']):
            detected_types.extend(['tld_evaluation', 'risk_analysis'])

        # ICANN policy/guidebook queries
        if any(term in query_lower for term in ['icann', 'guidebook', 'policy', 'requirements', 'safeguard']):
            detected_types.append('guidebook_section')

        # Application process queries
        if any(term in query_lower for term in ['application', 'submit', 'process', 'step']):
            detected_types.append('application_qa')

        # Template requests
        if any(term in query_lower for term in ['template', 'example', 'format', 'sample']):
            detected_types.append('answer_templates')

        return detected_types if detected_types else ['tld_evaluation', 'guidebook_section', 'application_qa']

    def _format_for_chat(self, results: List[Dict], query: str) -> str:
        """Format results for chat display"""
        formatted_results = []
        formatted_results.append(f"🔍 Semantic Search Results for: \"{query}\"\n")

        for i, item in enumerate(results, 1):
            similarity_pct = round(item['similarity'] * 100, 1)
            content_type_emoji = {
                'tld_evaluation': '📊',
                'risk_analysis': '⚠️',
                'application_qa': '📋',
                'guidebook_section': '📚',
                'applicant_data': '🏢',
                'question_guidance': '📝',
                'answer_templates': '📄'
            }.get(item['content_type'], '📄')

            formatted_results.append(f"""
{i}. {content_type_emoji} {item['title']} (Similarity: {similarity_pct}%)
   Source: {item['source_id']} | Type: {item['content_type']}

   {item['content'][:500]}{'...' if len(item['content']) > 500 else ''}

   Metadata: {json.dumps(item['metadata'], indent=2) if item['metadata'] else 'None'}
            """.strip())

        return "\n\n".join(formatted_results)

    def _format_for_icann_application(self, results: List[Dict], query: str, question_id: Optional[str] = None) -> str:
        """Format results optimized for ICANN application copy-paste"""
        if not results:
            return f"No content found for ICANN application question: {query}"

        # For ICANN applications, prioritize direct, clean answers
        top_result = results[0]
        content = top_result['content']

        # Clean up content for ICANN format
        cleaned_content = self._clean_for_icann_format(content)

        # Add context header
        header = f"📋 ICANN Application Answer"
        if question_id:
            header += f" for {question_id}"
        header += ":\n\n"

        # Format for copy-paste
        formatted_answer = f"{header}{cleaned_content}"

        # Add source information as comment
        source_info = f"\n\n<!-- Generated from: {top_result['title']} (Similarity: {round(top_result['similarity'] * 100, 1)}%) -->"
        
        return formatted_answer + source_info

    def _clean_for_icann_format(self, content: str) -> str:
        """Clean content for ICANN application format"""
        # Remove markdown formatting
        import re
        
        # Remove markdown headers
        content = re.sub(r'^#+\s+', '', content, flags=re.MULTILINE)
        
        # Remove bold/italic formatting
        content = re.sub(r'\*\*(.*?)\*\*', r'\1', content)
        content = re.sub(r'\*(.*?)\*', r'\1', content)
        
        # Remove bullet points and convert to clean text
        content = re.sub(r'^\s*[-•*]\s+', '', content, flags=re.MULTILINE)
        
        # Clean up extra whitespace
        content = re.sub(r'\n\s*\n', '\n\n', content)
        content = content.strip()
        
        # Ensure professional tone
        if len(content) > 500:
            # For long content, take first few paragraphs
            paragraphs = content.split('\n\n')[:3]
            content = '\n\n'.join(paragraphs)
        
        return content

# Create the tool instance
rag_search_tool = RAGVectorSearchTool()