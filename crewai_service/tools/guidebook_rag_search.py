"""
ICANN Guidebook RAG Search Tool

Semantic search over the ICANN New gTLD Program Applicant Guidebook
using vector embeddings stored in the rag_content table.

Replaces the local-PDF-based GuidebookSearchTool for production use
where the PDF file is not available on the server filesystem.
"""

import json
import logging
import os
from typing import List, Optional

from crewai.tools import BaseTool
from openai import OpenAI
from supabase import create_client

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "text-embedding-3-small"


class GuidebookRAGSearchTool(BaseTool):
    name: str = "ICANN Guidebook RAG Search"
    description: str = (
        "Searches the ICANN New gTLD Program Applicant Guidebook using semantic "
        "vector search. Returns authoritative guidance on evaluation criteria, "
        "policy requirements, compliance rules, and precedent. Use this for any "
        "question about ICANN gTLD program policies or evaluation standards."
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        object.__setattr__(self, '_openai_client', None)
        object.__setattr__(self, '_supabase_client', None)
        self._setup_clients()

    def _setup_clients(self):
        """Initialize OpenAI and Supabase clients."""
        # OpenAI
        try:
            api_key = os.getenv("OPENAI_API_KEY")

            if api_key:
                object.__setattr__(self, '_openai_client', OpenAI(api_key=api_key))
                logger.info("GuidebookRAGSearch: OpenAI client initialized")
            else:
                logger.warning("GuidebookRAGSearch: OpenAI API key not found")
        except Exception as e:
            logger.error(f"GuidebookRAGSearch: Failed to init OpenAI: {e}")

        # Supabase
        try:
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY")

            if url and key:
                object.__setattr__(self, '_supabase_client', create_client(url, key))
                logger.info("GuidebookRAGSearch: Supabase client initialized")
            else:
                logger.warning("GuidebookRAGSearch: Supabase credentials not found")
        except Exception as e:
            logger.error(f"GuidebookRAGSearch: Failed to init Supabase: {e}")

    def _run(self, search_query: str) -> str:
        """
        Search the ICANN guidebook for content relevant to the query.

        Args:
            search_query: Natural-language question or topic to search for.

        Returns:
            Formatted string with matching guidebook sections and similarity scores,
            or a clear error message on failure.
        """
        search_query = search_query.strip()
        if not search_query:
            return "Error: No search query provided. Please supply a specific question or topic."

        openai_client = getattr(self, '_openai_client', None)
        supabase_client = getattr(self, '_supabase_client', None)

        if not openai_client:
            return ("Error: OpenAI client unavailable — cannot generate query embedding. "
                    "Ensure OPENAI_API_KEY is set.")
        if not supabase_client:
            return ("Error: Supabase client unavailable — cannot search guidebook embeddings. "
                    "Ensure SUPABASE_URL and SUPABASE_SERVICE_KEY are set.")

        # Generate query embedding
        try:
            response = openai_client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=search_query,
            )
            query_embedding = response.data[0].embedding
        except Exception as e:
            logger.error(f"GuidebookRAGSearch: Embedding generation failed: {e}")
            return f"Error: Failed to generate query embedding — {e}"

        # Call similarity_search RPC
        try:
            result = supabase_client.rpc('similarity_search', {
                'query_embedding': query_embedding,
                'match_threshold': 0.3,
                'match_count': 5,
                'filter_content_type': 'guidebook_section',
                'filter_metadata': {},
            }).execute()
        except Exception as e:
            logger.error(f"GuidebookRAGSearch: Similarity search failed: {e}")
            return f"Error: Guidebook vector search failed — {e}"

        if not result.data:
            return (f"No guidebook sections found matching: \"{search_query}\". "
                    "Try rephrasing with different ICANN terminology.")

        return self._format_results(result.data, search_query)

    def _format_results(self, results: List[dict], query: str) -> str:
        """Format search results for agent consumption."""
        lines = [
            f"ICANN Guidebook Search Results for: \"{query}\"",
            f"Found {len(results)} relevant section(s).\n",
        ]

        for i, item in enumerate(results, 1):
            similarity_pct = round(item.get('similarity', 0) * 100, 1)
            title = item.get('title', 'Untitled')
            content = item.get('content', '')
            source_id = item.get('source_id', '')
            metadata = item.get('metadata', {})

            lines.append(f"--- Result {i} (Relevance: {similarity_pct}%) ---")
            lines.append(f"Section: {title}")
            if source_id:
                lines.append(f"Reference: Section {source_id}")
            if metadata.get('page_number'):
                lines.append(f"Page: {metadata['page_number']}")

            # Include full content (agents need complete context)
            lines.append(f"\n{content}\n")

        lines.append("Source: ICANN New gTLD Program Applicant Guidebook (2026)")
        lines.append("Authority: Official ICANN guidance — authoritative for evaluation.")

        return '\n'.join(lines)
