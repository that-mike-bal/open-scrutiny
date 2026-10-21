"""
Guidebook Search Module

Provides semantic search capabilities for the ICANN gTLD Program Applicant Guidebook
embeddings to enhance AI responses with relevant policy context.
"""

import os
import sys
import logging
from typing import List, Dict, Any, Optional, Tuple
import json

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import openai
from db.supabase_client import get_supabase

logger = logging.getLogger(__name__)

class GuidebookSearcher:
    """Search ICANN guidebook embeddings for relevant context"""
    
    def __init__(self):
        self.supabase = get_supabase()
        self.openai_client = self._setup_openai()
    
    def _setup_openai(self):
        """Setup OpenAI client for embeddings"""
        try:
            # Try to load API key from secrets
            api_key = self._load_secret("openai_api_key")
            if not api_key:
                api_key = os.getenv("OPENAI_API_KEY")
            
            if not api_key:
                logger.warning("OpenAI API key not found - semantic search disabled")
                return None
                
            return openai.OpenAI(api_key=api_key)
        except Exception as e:
            logger.error(f"Failed to setup OpenAI client: {e}")
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
    
    def generate_query_embedding(self, query_text: str) -> Optional[List[float]]:
        """Generate embedding for search query"""
        if not self.openai_client:
            return None
        
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=query_text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Failed to generate query embedding: {e}")
            return None
    
    def semantic_search(
        self, 
        query: str, 
        similarity_threshold: float = 0.80,
        max_results: int = 5,
        content_types: Optional[List[str]] = None,
        topic_tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search on guidebook embeddings
        
        Args:
            query: Natural language search query
            similarity_threshold: Minimum cosine similarity (0.0 to 1.0)
            max_results: Maximum number of results to return
            content_types: Filter by content types ('section', 'paragraph', etc.)
            topic_tags: Filter by topic tags
            
        Returns:
            List of matching guidebook sections with similarity scores
        """
        if not self.openai_client:
            logger.warning("Semantic search unavailable - no OpenAI client")
            return []
        
        try:
            # Generate query embedding
            query_embedding = self.generate_query_embedding(query)
            if not query_embedding:
                return []
            
            # Log search query
            search_id = self._log_search_query(query, query_embedding, similarity_threshold, max_results)
            
            # Build SQL query for vector similarity search
            sql_conditions = [
                f"(1 - (embedding <=> '[{','.join(map(str, query_embedding))}]'::vector)) >= {similarity_threshold}"
            ]
            
            if content_types:
                content_types_str = "','".join(content_types)
                sql_conditions.append(f"content_type IN ('{content_types_str}')")
            
            if topic_tags:
                # Use array overlap operator
                tags_str = "','".join(topic_tags)
                sql_conditions.append(f"topic_tags && ARRAY['{tags_str}']")
            
            where_clause = " AND ".join(sql_conditions)
            
            # Get all embeddings and calculate similarity in Python
            response = self.supabase.table('guidebook_embeddings').select('*').execute()
            
            if response.data:
                import numpy as np
                
                # Calculate similarities and filter
                results = []
                for row in response.data:
                    if not row.get('embedding'):
                        continue
                    
                    # Parse embedding from string format if needed
                    embedding_data = row['embedding']
                    if isinstance(embedding_data, str):
                        # Parse vector format: "[0.1,0.2,0.3,...]" or "[-0.1,0.2,0.3,...]"
                        embedding_str = embedding_data.strip()
                        if embedding_str.startswith('[') and embedding_str.endswith(']'):
                            embedding_str = embedding_str[1:-1]  # Remove brackets
                        stored_embedding = np.array([float(x.strip()) for x in embedding_str.split(',')])
                    else:
                        stored_embedding = np.array(embedding_data)
                    
                    query_embedding_np = np.array(query_embedding)
                    
                    # Cosine similarity = dot product / (norm1 * norm2)
                    similarity = np.dot(stored_embedding, query_embedding_np) / (
                        np.linalg.norm(stored_embedding) * np.linalg.norm(query_embedding_np)
                    )
                    
                    # Filter by threshold
                    if similarity >= similarity_threshold:
                        # Apply content type filter
                        if content_types and row.get('content_type') not in content_types:
                            continue
                        
                        # Apply topic filter
                        if topic_tags:
                            row_topics = row.get('topic_tags', [])
                            if not any(tag in row_topics for tag in topic_tags):
                                continue
                        
                        # Add similarity score to result
                        result_row = dict(row)
                        result_row['similarity_score'] = round(float(similarity), 4)
                        results.append(result_row)
                
                # Sort by similarity (highest first) and limit
                results.sort(key=lambda x: x['similarity_score'], reverse=True)
                results = results[:max_results]
                
                # Log search results
                self._log_search_results(search_id, results)
                
                return results
            else:
                logger.warning("No embeddings found in database")
                return []
                
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []
    
    def keyword_search(
        self,
        keywords: List[str],
        max_results: int = 10,
        content_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform keyword-based full-text search
        
        Args:
            keywords: List of keywords to search for
            max_results: Maximum number of results
            content_types: Filter by content types
            
        Returns:
            List of matching sections
        """
        try:
            # Build full-text search query
            search_terms = " & ".join(keywords)
            
            conditions = [
                f"to_tsvector('english', content_text) @@ to_tsquery('english', '{search_terms}')"
            ]
            
            if content_types:
                content_types_str = "','".join(content_types)
                conditions.append(f"content_type IN ('{content_types_str}')")
            
            where_clause = " AND ".join(conditions)
            
            query_sql = f"""
                SELECT 
                    id,
                    section_number,
                    section_title,
                    content_text,
                    content_type,
                    topic_tags,
                    page_number,
                    context_summary,
                    ts_rank(to_tsvector('english', content_text), to_tsquery('english', '{search_terms}')) as relevance_score
                FROM guidebook_embeddings
                WHERE {where_clause}
                ORDER BY ts_rank(to_tsvector('english', content_text), to_tsquery('english', '{search_terms}')) DESC
                LIMIT {max_results}
            """
            
            response = self.supabase.rpc('exec_sql', {'query': query_sql}).execute()
            return response.data if response.data else []
            
        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return []
    
    def get_context_for_tld_evaluation(
        self,
        tld_string: str,
        use_case: str,
        evaluation_topics: List[str],
        max_results: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Get relevant guidebook context for a specific TLD evaluation
        
        Args:
            tld_string: The TLD being evaluated (e.g., "example")
            use_case: Intended use case for the TLD
            evaluation_topics: List of topics being evaluated
            max_results: Maximum results to return
            
        Returns:
            List of relevant guidebook sections
        """
        # Build comprehensive search query
        query_parts = [
            f"TLD evaluation for .{tld_string}",
            f"use case: {use_case}",
            f"topics: {', '.join(evaluation_topics)}"
        ]
        
        query = " ".join(query_parts)
        
        # Filter by relevant topic tags
        relevant_tags = []
        topic_mapping = {
            'string': ['string-similarity', 'evaluation'],
            'similarity': ['string-similarity', 'evaluation'],
            'dns': ['dns-stability', 'technical-review'],
            'technical': ['technical-review', 'registry-operations'],
            'legal': ['legal-review', 'trademark'],
            'trademark': ['legal-review', 'trademark'],
            'financial': ['financial', 'fees'],
            'policy': ['policy', 'governance']
        }
        
        for topic in evaluation_topics:
            topic_lower = topic.lower()
            for key, tags in topic_mapping.items():
                if key in topic_lower:
                    relevant_tags.extend(tags)
        
        # Remove duplicates
        relevant_tags = list(set(relevant_tags))
        
        return self.semantic_search(
            query=query,
            similarity_threshold=0.50,  # Lower threshold for broader context
            max_results=max_results,
            topic_tags=relevant_tags if relevant_tags else None
        )
    
    def get_context_for_icann_question(
        self,
        question_id: str,
        question_text: str,
        max_results: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Get guidebook context for a specific ICANN application question
        
        Args:
            question_id: ICANN question ID
            question_text: The actual question text
            max_results: Maximum results to return
            
        Returns:
            List of relevant guidebook sections
        """
        # Use the question text directly for semantic search
        return self.semantic_search(
            query=question_text,
            similarity_threshold=0.50,
            max_results=max_results
        )
    
    def _log_search_query(
        self,
        query_text: str,
        query_embedding: List[float],
        similarity_threshold: float,
        max_results: int
    ) -> Optional[str]:
        """Log search query for analytics"""
        try:
            record = {
                'query_text': query_text,
                'query_embedding': query_embedding,
                'query_type': 'semantic',
                'similarity_threshold': similarity_threshold,
                'max_results': max_results
            }
            
            response = self.supabase.table('guidebook_search_queries').insert(record).execute()
            return response.data[0]['id'] if response.data else None
        except Exception as e:
            logger.error(f"Failed to log search query: {e}")
            return None
    
    def _log_search_results(self, search_id: str, results: List[Dict[str, Any]]):
        """Log search results for analytics"""
        if not search_id or not results:
            return
        
        try:
            # Update search query with results count
            self.supabase.table('guidebook_search_queries').update({
                'results_count': len(results),
                'top_similarity_score': results[0].get('similarity_score', 0) if results else 0
            }).eq('id', search_id).execute()
            
            # Log individual results
            result_records = []
            for i, result in enumerate(results):
                result_records.append({
                    'search_query_id': search_id,
                    'guidebook_embedding_id': result['id'],
                    'similarity_score': result.get('similarity_score', 0),
                    'rank_position': i + 1,
                    'relevance_score': result.get('similarity_score', 0)
                })
            
            if result_records:
                self.supabase.table('guidebook_search_results').insert(result_records).execute()
                
        except Exception as e:
            logger.error(f"Failed to log search results: {e}")
    
    def get_section_by_number(self, section_number: str) -> Optional[Dict[str, Any]]:
        """Get a specific guidebook section by its number"""
        try:
            response = self.supabase.table('guidebook_embeddings').select('*').eq('section_number', section_number).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Failed to get section {section_number}: {e}")
            return None
    
    def get_sections_by_topic(self, topic_tag: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Get all sections with a specific topic tag"""
        try:
            response = self.supabase.table('guidebook_embeddings').select('*').contains('topic_tags', [topic_tag]).limit(max_results).execute()
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Failed to get sections for topic {topic_tag}: {e}")
            return []

# Convenience functions for easy import
def search_guidebook(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """Quick semantic search function"""
    searcher = GuidebookSearcher()
    return searcher.semantic_search(query, max_results=max_results)

def get_tld_context(tld_string: str, use_case: str, topics: List[str]) -> List[Dict[str, Any]]:
    """Quick function to get TLD evaluation context"""
    searcher = GuidebookSearcher()
    return searcher.get_context_for_tld_evaluation(tld_string, use_case, topics)

def get_question_context(question_text: str) -> List[Dict[str, Any]]:
    """Quick function to get context for ICANN question"""
    searcher = GuidebookSearcher()
    return searcher.get_context_for_icann_question("", question_text)
