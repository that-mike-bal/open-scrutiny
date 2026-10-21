"""
Brave Web Search Tool - General purpose web search using Brave Search API.

Provides web search capabilities for GAC risk analysis and policy evaluation,
with full API call logging for audit trails.  Uses the shared Brave rate
limiter so it cooperates with other Brave-consuming tools.

Fallback chain: Brave Search → Firecrawl search → model-knowledge disclosure.
"""

import logging
from typing import Any, Type, Dict, Optional

import requests
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from crewai_service.utils.config import load_api_key
from crewai_service.utils.brave_rate_limiter import get_brave_rate_limiter
from crewai_service.utils.logged_requests import brave_get_with_retry, logged_post

logger = logging.getLogger(__name__)


class BraveWebSearchSchema(BaseModel):
    """Input schema for Brave Web Search."""
    search_query: str = Field(
        ...,
        description="The search query to execute"
    )
    search_type: Optional[str] = Field(
        default="web",
        description="Type of search: 'web' (default) or 'news'"
    )


class BraveWebSearchTool(BaseTool):
    """
    General-purpose web search tool using Brave Search API.

    Used for GAC risk analysis, policy evaluation, and general
    web research with full API call logging.
    """

    name: str = "Brave Web Search"
    description: str = (
        "Search the web for recent information, news, political developments, "
        "cultural context, and other relevant data using Brave Search API. "
        "Use this for researching TLD strings, checking for controversies, "
        "finding relevant news, and gathering context for policy evaluation."
    )
    args_schema: Type[BaseModel] = BraveWebSearchSchema

    # API configuration
    brave_api_key: str = ""
    n_results: int = 10

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        object.__setattr__(self, 'brave_api_key', load_api_key("brave") or "")
        object.__setattr__(self, 'firecrawl_api_key', load_api_key("firecrawl") or "")
        object.__setattr__(self, '_brave_limiter', get_brave_rate_limiter())

    def _run(self, **kwargs: Any) -> Any:
        """Execute the web search with Brave → Firecrawl → model-knowledge fallback."""
        search_query = kwargs.get("search_query") or kwargs.get("query", "")
        search_type = kwargs.get("search_type", "web")

        if not search_query:
            return {"error": "No search query provided"}

        # --- 1. Try Brave Search ---
        brave_available = bool(self.brave_api_key) and not self._brave_limiter.quota_exhausted
        if brave_available:
            try:
                results = self._execute_brave_search(search_query, search_type)
                if not results.get("search_bypassed"):
                    return results
                # Brave returned a bypass (quota hit mid-request) — fall through
                logger.info(f"Brave degraded for '{search_query}', trying Firecrawl fallback")
            except Exception as e:
                logger.warning(f"Brave search error for '{search_query}': {e}")
        else:
            reason = "quota exhausted" if self.brave_api_key else "API key not configured"
            logger.info(f"Brave unavailable ({reason}), trying Firecrawl fallback")

        # --- 2. Try Firecrawl Search fallback ---
        if self.firecrawl_api_key:
            try:
                results = self._execute_firecrawl_search(search_query)
                if results.get("results"):
                    results["query"] = search_query
                    results["search_type"] = search_type
                    results["search_bypassed"] = False
                    results["data_source"] = "firecrawl"
                    return results
                logger.info(f"Firecrawl returned 0 results for '{search_query}'")
            except Exception as e:
                logger.warning(f"Firecrawl search error for '{search_query}': {e}")

        # --- 3. Model-knowledge fallback ---
        bypass_parts = []
        if not self.brave_api_key:
            bypass_parts.append("Brave API key not configured")
        elif self._brave_limiter.quota_exhausted:
            bypass_parts.append("Brave API quota exhausted")
        else:
            bypass_parts.append("Brave Search failed")
        if not self.firecrawl_api_key:
            bypass_parts.append("Firecrawl API key not configured")
        else:
            bypass_parts.append("Firecrawl search returned no results")

        bypass_reason = "; ".join(bypass_parts)
        logger.warning(f"All search fallbacks exhausted for '{search_query}': {bypass_reason}")

        return {
            "error": "All search sources unavailable — search intentionally bypassed",
            "results": [],
            "query": search_query,
            "search_bypassed": True,
            "bypass_reason": bypass_reason,
            "model_knowledge_only": True,
            "search_summary": {
                "brave_search_used": False,
                "brave_degraded": True,
                "firecrawl_used": bool(self.firecrawl_api_key),
                "model_knowledge_only": True,
                "search_bypass_reason": bypass_reason,
                "data_sources": [],
            },
        }

    def _execute_brave_search(self, query: str, search_type: str = "web") -> Dict:
        """Execute a Brave Search API request with shared rate limiting."""

        headers = {
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip',
            'X-Subscription-Token': self.brave_api_key,
        }

        params = {
            'q': query,
            'count': self.n_results,
            'text_decorations': False,
            'search_lang': 'en',
            'safesearch': 'off',
        }

        # Use news endpoint for news searches
        if search_type == "news":
            url = 'https://api.search.brave.com/res/v1/news/search'
        else:
            url = 'https://api.search.brave.com/res/v1/web/search'

        response, status = brave_get_with_retry(
            "BraveWebSearchTool",
            url,
            rate_limiter=self._brave_limiter,
            max_retries=2,
            headers=headers,
            params=params,
            timeout=15,
        )

        if status == "quota_exhausted":
            return {
                "error": "Brave API quota exhausted — search intentionally bypassed",
                "results": [],
                "query": query,
                "search_bypassed": True,
                "bypass_reason": "API quota exhausted for current billing period",
            }

        if status == "rate_limited":
            return {
                "error": "Brave API rate limited after retries",
                "results": [],
                "query": query,
                "search_bypassed": True,
                "bypass_reason": "Rate limited after retry attempts",
            }

        if status == "success" and response is not None:
            data = response.json()
            processed = self._process_results(data, search_type)
            processed["query"] = query
            processed["search_type"] = search_type
            processed["search_bypassed"] = False
            logger.info(f"Brave search for '{query}' returned {len(processed.get('results', []))} results")
            return processed

        # Generic error fallback
        error_detail = (
            f"HTTP {response.status_code}" if response is not None
            else "no response"
        )
        error_msg = f"Brave API error: {error_detail}"
        logger.error(f"{error_msg} for query '{query}'")
        return {"error": error_msg, "results": [], "query": query}

    def _execute_firecrawl_search(self, query: str) -> Dict:
        """Fallback web search using Firecrawl's /v1/search endpoint."""
        headers = {
            'Authorization': f'Bearer {self.firecrawl_api_key}',
            'Content-Type': 'application/json',
        }
        payload = {
            "query": query,
            "limit": self.n_results,
            "lang": "en",
        }

        response = logged_post(
            "BraveWebSearchTool/FirecrawlFallback",
            "https://api.firecrawl.dev/v1/search",
            headers=headers,
            json=payload,
            timeout=30,
        )

        if response.status_code != 200:
            logger.warning(f"Firecrawl search returned HTTP {response.status_code}")
            return {"results": []}

        data = response.json()
        raw_results = data.get("data", [])
        processed = []
        for item in raw_results[:self.n_results]:
            metadata = item.get("metadata", {})
            processed.append({
                "title": metadata.get("title") or item.get("title", ""),
                "url": item.get("url", ""),
                "description": metadata.get("description") or item.get("markdown", "")[:300],
                "source": metadata.get("sourceURL", ""),
                "type": "web",
            })

        logger.info(f"Firecrawl fallback for '{query}' returned {len(processed)} results")
        return {
            "results": processed,
            "total_results": len(processed),
            "data_source": "firecrawl",
        }

    def _process_results(self, data: Dict, search_type: str) -> Dict:
        """Process Brave API response into structured results."""
        processed = {
            "results": [],
            "total_results": 0,
        }

        if search_type == "news":
            # Process news results
            news_results = data.get("results", [])
            for item in news_results[:self.n_results]:
                processed["results"].append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "description": item.get("description", ""),
                    "source": item.get("meta_url", {}).get("hostname", ""),
                    "date": item.get("age", ""),
                    "type": "news"
                })
        else:
            # Process web results
            web_results = data.get("web", {}).get("results", [])
            for item in web_results[:self.n_results]:
                processed["results"].append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "description": item.get("description", ""),
                    "source": item.get("meta_url", {}).get("hostname", ""),
                    "type": "web"
                })

            # Include knowledge graph if available
            if "knowledge_graph" in data:
                kg = data["knowledge_graph"]
                processed["knowledge_graph"] = {
                    "title": kg.get("title", ""),
                    "description": kg.get("description", ""),
                    "url": kg.get("url", ""),
                }

        processed["total_results"] = len(processed["results"])
        return processed
