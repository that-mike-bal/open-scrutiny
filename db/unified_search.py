"""
Unified Search Module

Provides comprehensive semantic search across ICANN guidebook content,
application questions, and external resources.
"""

import os
import sys
import logging
from typing import List, Dict, Any, Optional, Tuple, Union
import json
from dataclasses import dataclass
from enum import Enum

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import openai
import numpy as np
from db.supabase_client import get_supabase

logger = logging.getLogger(__name__)

class SearchResultType(Enum):
    GUIDEBOOK = "guidebook"
    QUESTION = "question"
    RESOURCE = "resource"

@dataclass
class SearchResult:
    """Unified search result structure"""
    id: str
    type: SearchResultType
    title: str
    content: str
    similarity_score: float
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'type': self.type.value,
            'title': self.title,
            'content': self.content,
            'similarity_score': self.similarity_score,
            'metadata': self.metadata
        }

class UnifiedSearcher:
    """Comprehensive search across all ICANN knowledge sources"""
    
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
                logger.warning("OpenAI API key not found - semantic search disabled")
                return None
                
            return openai.OpenAI(api_key=api_key)
        except Exception as e:
            logger.error(f"Failed to setup OpenAI client: {e}")
            return None
    
    def _load_secret(self, secret_name: str) -> Optional[str]:
        """Read a credential from the environment (``SECRET_NAME`` upper-cased)."""
        value = os.getenv(secret_name.upper())
        return value.strip() if value and value.strip() else None
    
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
    
    def search_all(
        self,
        query: str,
        similarity_threshold: float = 0.50,
        max_results: int = 10,
        result_types: Optional[List[SearchResultType]] = None,
        section_filter: Optional[List[int]] = None,
        topic_filter: Optional[List[str]] = None
    ) -> List[SearchResult]:
        """
        Search across all knowledge sources
        
        Args:
            query: Natural language search query
            similarity_threshold: Minimum cosine similarity (0.0 to 1.0)
            max_results: Maximum number of results to return
            result_types: Filter by result types (guidebook, question, resource)
            section_filter: Filter by ICANN section numbers
            topic_filter: Filter by topic tags
            
        Returns:
            List of unified search results sorted by relevance
        """
        if not self.openai_client:
            logger.warning("Semantic search unavailable - no OpenAI client")
            return []
        
        # Default to searching all types
        if result_types is None:
            result_types = [SearchResultType.GUIDEBOOK, SearchResultType.QUESTION, SearchResultType.RESOURCE]
        
        try:
            # Generate query embedding
            query_embedding = self.generate_query_embedding(query)
            if not query_embedding:
                return []
            
            all_results = []
            
            # Search guidebook content
            if SearchResultType.GUIDEBOOK in result_types:
                guidebook_results = self._search_guidebook(query_embedding, similarity_threshold, max_results, topic_filter)
                all_results.extend(guidebook_results)
            
            # Search application questions
            if SearchResultType.QUESTION in result_types:
                question_results = self._search_questions(query_embedding, similarity_threshold, max_results, section_filter, topic_filter)
                all_results.extend(question_results)
            
            # Search external resources
            if SearchResultType.RESOURCE in result_types:
                resource_results = self._search_resources(query_embedding, similarity_threshold, max_results, section_filter, topic_filter)
                all_results.extend(resource_results)
            
            # Sort by similarity score and limit results
            all_results.sort(key=lambda x: x.similarity_score, reverse=True)
            return all_results[:max_results]
            
        except Exception as e:
            logger.error(f"Unified search failed: {e}")
            return []
    
    def _search_guidebook(
        self, 
        query_embedding: List[float], 
        similarity_threshold: float,
        max_results: int,
        topic_filter: Optional[List[str]] = None
    ) -> List[SearchResult]:
        """Search guidebook embeddings"""
        try:
            response = self.supabase.table('guidebook_embeddings').select('*').execute()
            
            if not response.data:
                return []
            
            results = []
            for row in response.data:
                if not row.get('embedding'):
                    continue
                
                # Parse embedding
                embedding_data = row['embedding']
                if isinstance(embedding_data, str):
                    embedding_str = embedding_data.strip()
                    if embedding_str.startswith('[') and embedding_str.endswith(']'):
                        embedding_str = embedding_str[1:-1]
                    stored_embedding = np.array([float(x.strip()) for x in embedding_str.split(',')])
                else:
                    stored_embedding = np.array(embedding_data)
                
                query_embedding_np = np.array(query_embedding)
                
                # Calculate cosine similarity
                similarity = np.dot(stored_embedding, query_embedding_np) / (
                    np.linalg.norm(stored_embedding) * np.linalg.norm(query_embedding_np)
                )
                
                # Filter by threshold
                if similarity < similarity_threshold:
                    continue
                
                # Apply topic filter
                if topic_filter:
                    row_topics = row.get('topic_tags', [])
                    if not any(tag in row_topics for tag in topic_filter):
                        continue
                
                # Create search result
                result = SearchResult(
                    id=row['id'],
                    type=SearchResultType.GUIDEBOOK,
                    title=f"[{row['section_number']}] {row['section_title']}",
                    content=row['content_text'][:500] + "..." if len(row['content_text']) > 500 else row['content_text'],
                    similarity_score=round(float(similarity), 4),
                    metadata={
                        'section_number': row['section_number'],
                        'page_number': row.get('page_number'),
                        'topic_tags': row.get('topic_tags', []),
                        'context_summary': row.get('context_summary'),
                        'policy_implications': row.get('policy_implications')
                    }
                )
                results.append(result)
            
            # Sort by similarity and limit
            results.sort(key=lambda x: x.similarity_score, reverse=True)
            return results[:max_results]
            
        except Exception as e:
            logger.error(f"Guidebook search failed: {e}")
            return []
    
    def _search_questions(
        self, 
        query_embedding: List[float], 
        similarity_threshold: float,
        max_results: int,
        section_filter: Optional[List[int]] = None,
        topic_filter: Optional[List[str]] = None
    ) -> List[SearchResult]:
        """Search application question embeddings"""
        try:
            response = self.supabase.table('application_question_embeddings').select('*').execute()
            
            if not response.data:
                return []
            
            results = []
            for row in response.data:
                if not row.get('question_embedding'):
                    continue
                
                # Apply section filter
                if section_filter and row.get('section_number') not in section_filter:
                    continue
                
                # Parse embedding
                embedding_data = row['question_embedding']
                if isinstance(embedding_data, str):
                    embedding_str = embedding_data.strip()
                    if embedding_str.startswith('[') and embedding_str.endswith(']'):
                        embedding_str = embedding_str[1:-1]
                    stored_embedding = np.array([float(x.strip()) for x in embedding_str.split(',')])
                else:
                    stored_embedding = np.array(embedding_data)
                
                query_embedding_np = np.array(query_embedding)
                
                # Calculate cosine similarity
                similarity = np.dot(stored_embedding, query_embedding_np) / (
                    np.linalg.norm(stored_embedding) * np.linalg.norm(query_embedding_np)
                )
                
                # Filter by threshold
                if similarity < similarity_threshold:
                    continue
                
                # Apply topic filter
                if topic_filter:
                    row_topics = row.get('topic_tags', [])
                    if not any(tag in row_topics for tag in topic_filter):
                        continue
                
                # Create search result
                result = SearchResult(
                    id=row['id'],
                    type=SearchResultType.QUESTION,
                    title=f"Question {row['question_number']}: {row['section_name']}",
                    content=row['question_text'],
                    similarity_score=round(float(similarity), 4),
                    metadata={
                        'question_number': row['question_number'],
                        'section_number': row.get('section_number'),
                        'section_name': row.get('section_name'),
                        'expected_answer_type': row.get('expected_answer_type'),
                        'complexity_score': row.get('complexity_score'),
                        'topic_tags': row.get('topic_tags', []),
                        'evaluation_criteria': row.get('evaluation_criteria'),
                        'best_practices': row.get('best_practices'),
                        'reference_urls': row.get('reference_urls', [])
                    }
                )
                results.append(result)
            
            # Sort by similarity and limit
            results.sort(key=lambda x: x.similarity_score, reverse=True)
            return results[:max_results]
            
        except Exception as e:
            logger.error(f"Question search failed: {e}")
            return []
    
    def _search_resources(
        self, 
        query_embedding: List[float], 
        similarity_threshold: float,
        max_results: int,
        section_filter: Optional[List[int]] = None,
        topic_filter: Optional[List[str]] = None
    ) -> List[SearchResult]:
        """Search external resource embeddings"""
        try:
            response = self.supabase.table('external_resource_embeddings').select('*').execute()
            
            if not response.data:
                return []
            
            results = []
            for row in response.data:
                if not row.get('title_embedding'):
                    continue
                
                # Apply section filter
                if section_filter:
                    row_sections = row.get('application_sections', [])
                    if not any(section in row_sections for section in section_filter):
                        continue
                
                # Parse embedding (using title_embedding for primary search)
                embedding_data = row['title_embedding']
                if isinstance(embedding_data, str):
                    embedding_str = embedding_data.strip()
                    if embedding_str.startswith('[') and embedding_str.endswith(']'):
                        embedding_str = embedding_str[1:-1]
                    stored_embedding = np.array([float(x.strip()) for x in embedding_str.split(',')])
                else:
                    stored_embedding = np.array(embedding_data)
                
                query_embedding_np = np.array(query_embedding)
                
                # Calculate cosine similarity
                similarity = np.dot(stored_embedding, query_embedding_np) / (
                    np.linalg.norm(stored_embedding) * np.linalg.norm(query_embedding_np)
                )
                
                # Filter by threshold
                if similarity < similarity_threshold:
                    continue
                
                # Apply topic filter
                if topic_filter:
                    row_topics = row.get('topic_tags', [])
                    if not any(tag in row_topics for tag in topic_filter):
                        continue
                
                # Create search result
                result = SearchResult(
                    id=row['id'],
                    type=SearchResultType.RESOURCE,
                    title=row['resource_title'],
                    content=row.get('resource_description', ''),
                    similarity_score=round(float(similarity), 4),
                    metadata={
                        'resource_url': row['resource_url'],
                        'resource_type': row.get('resource_type'),
                        'resource_source': row.get('resource_source'),
                        'authority_level': row.get('authority_level'),
                        'complexity_level': row.get('complexity_level'),
                        'topic_tags': row.get('topic_tags', []),
                        'relevant_questions': row.get('relevant_questions', []),
                        'application_sections': row.get('application_sections', []),
                        'relevance_to_applications': row.get('relevance_to_applications')
                    }
                )
                results.append(result)
            
            # Sort by similarity and limit
            results.sort(key=lambda x: x.similarity_score, reverse=True)
            return results[:max_results]
            
        except Exception as e:
            logger.error(f"Resource search failed: {e}")
            return []
    
    def search_for_question_context(
        self,
        question_number: str,
        max_results: int = 5
    ) -> Dict[str, List[SearchResult]]:
        """
        Get comprehensive context for a specific ICANN application question
        
        Args:
            question_number: ICANN question number (e.g., "18a", "19.1")
            max_results: Maximum results per category
            
        Returns:
            Dictionary with guidebook, resources, and related questions
        """
        try:
            # Get the question details
            question_response = self.supabase.table('application_question_embeddings').select('*').eq('question_number', question_number).execute()
            
            if not question_response.data:
                logger.warning(f"Question {question_number} not found")
                return {}
            
            question = question_response.data[0]
            
            # Build comprehensive search query
            search_query = f"{question['question_text']} {question.get('section_name', '')} {question.get('question_context', '')}"
            
            # Get topic tags for filtering
            topic_tags = question.get('topic_tags', [])
            section_number = question.get('section_number')
            
            # Search different sources
            results = {
                'guidebook': [],
                'resources': [],
                'related_questions': []
            }
            
            # Search guidebook for relevant policy
            guidebook_results = self.search_all(
                query=search_query,
                similarity_threshold=0.45,
                max_results=max_results,
                result_types=[SearchResultType.GUIDEBOOK],
                topic_filter=topic_tags
            )
            results['guidebook'] = guidebook_results
            
            # Search external resources
            resource_results = self.search_all(
                query=search_query,
                similarity_threshold=0.40,
                max_results=max_results,
                result_types=[SearchResultType.RESOURCE],
                section_filter=[section_number] if section_number else None
            )
            results['resources'] = resource_results
            
            # Search for related questions in same section
            related_query = f"{question.get('section_name', '')} {' '.join(topic_tags[:3])}"
            related_results = self.search_all(
                query=related_query,
                similarity_threshold=0.35,
                max_results=max_results,
                result_types=[SearchResultType.QUESTION],
                section_filter=[section_number] if section_number else None
            )
            # Filter out the original question
            results['related_questions'] = [r for r in related_results if r.metadata.get('question_number') != question_number]
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to get question context for {question_number}: {e}")
            return {}
    
    def search_for_tld_evaluation(
        self,
        tld_string: str,
        intended_use: str,
        evaluation_areas: List[str],
        max_results: int = 8
    ) -> Dict[str, List[SearchResult]]:
        """
        Get comprehensive context for TLD string evaluation
        
        Args:
            tld_string: The TLD being evaluated (e.g., "example")
            intended_use: Intended use case for the TLD
            evaluation_areas: Areas of evaluation (e.g., ["string similarity", "dns stability"])
            max_results: Maximum results per category
            
        Returns:
            Dictionary with relevant content from all sources
        """
        try:
            # Build comprehensive search query
            search_query = f"TLD .{tld_string} {intended_use} {' '.join(evaluation_areas)}"
            
            # Map evaluation areas to topic tags
            topic_mapping = {
                'string similarity': ['string-similarity', 'evaluation'],
                'dns stability': ['dns-stability', 'technical-review'],
                'reserved names': ['reserved-names', 'policy'],
                'trademark': ['trademark', 'legal-review'],
                'geographic': ['geographic', 'government'],
                'idn': ['idn', 'internationalization'],
                'technical': ['technical', 'dns']
            }
            
            relevant_topics = []
            for area in evaluation_areas:
                area_lower = area.lower()
                for key, topics in topic_mapping.items():
                    if key in area_lower:
                        relevant_topics.extend(topics)
            
            relevant_topics = list(set(relevant_topics))  # Remove duplicates
            
            results = {
                'guidebook_policy': [],
                'evaluation_questions': [],
                'technical_resources': [],
                'all_results': []
            }
            
            # Search all sources
            all_results = self.search_all(
                query=search_query,
                similarity_threshold=0.40,
                max_results=max_results * 3,
                topic_filter=relevant_topics if relevant_topics else None
            )
            
            # Categorize results
            for result in all_results:
                if result.type == SearchResultType.GUIDEBOOK:
                    results['guidebook_policy'].append(result)
                elif result.type == SearchResultType.QUESTION:
                    results['evaluation_questions'].append(result)
                elif result.type == SearchResultType.RESOURCE:
                    results['technical_resources'].append(result)
                
                results['all_results'].append(result)
            
            # Limit each category
            for key in ['guidebook_policy', 'evaluation_questions', 'technical_resources']:
                results[key] = results[key][:max_results]
            
            results['all_results'] = results['all_results'][:max_results * 2]
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to get TLD evaluation context for .{tld_string}: {e}")
            return {}

# Convenience functions for easy import
def search_all_sources(query: str, max_results: int = 10) -> List[SearchResult]:
    """Quick search across all sources"""
    searcher = UnifiedSearcher()
    return searcher.search_all(query, max_results=max_results)

def get_question_context(question_number: str) -> Dict[str, List[SearchResult]]:
    """Quick function to get comprehensive question context"""
    searcher = UnifiedSearcher()
    return searcher.search_for_question_context(question_number)

def get_tld_evaluation_context(tld_string: str, intended_use: str, areas: List[str]) -> Dict[str, List[SearchResult]]:
    """Quick function to get TLD evaluation context"""
    searcher = UnifiedSearcher()
    return searcher.search_for_tld_evaluation(tld_string, intended_use, areas)
