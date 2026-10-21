"""
Logged Serper Tool - SerperDevTool with API call logging.

Wraps the CrewAI SerperDevTool to log all API requests/responses
for audit trail purposes.
"""

import json
import os
import time
import logging
from typing import Any

import requests
from crewai_tools import SerperDevTool

from crewai_service.utils.api_call_logger import log_api_call

logger = logging.getLogger(__name__)


class LoggedSerperDevTool(SerperDevTool):
    """
    SerperDevTool with API call logging for audit trails.

    Overrides _make_api_request to log all calls to the Serper API.
    """

    name: str = "Search the internet with Serper (Logged)"

    def _make_api_request(self, search_query: str, search_type: str) -> dict:
        """Make API request to Serper with logging."""
        search_url = self._get_search_url(search_type)
        payload = {"q": search_query, "num": self.n_results}

        if self.country != "":
            payload["gl"] = self.country
        if self.location != "":
            payload["location"] = self.location
        if self.locale != "":
            payload["hl"] = self.locale

        headers = {
            "X-API-KEY": os.environ.get("SERPER_API_KEY", ""),
            "content-type": "application/json",
        }

        # Start timing
        start_time = time.time()
        response = None
        status_code = None
        success = False
        error_msg = None

        try:
            response = requests.post(
                search_url,
                headers=headers,
                json=payload,
                timeout=10
            )
            status_code = response.status_code
            response.raise_for_status()
            results = response.json()

            if not results:
                error_msg = "Empty response from Serper API"
                logger.error(error_msg)
                raise ValueError(error_msg)

            success = True
            logger.info(f"Serper search for '{search_query}' returned {len(results.get('organic', []))} results")
            return results

        except requests.exceptions.RequestException as e:
            error_msg = f"Error making request to Serper API: {e}"
            if response is not None and hasattr(response, "content"):
                error_msg += f" - Response: {response.content[:200]}"
            logger.error(error_msg)
            raise

        except json.JSONDecodeError as e:
            error_msg = f"Error decoding JSON response: {e}"
            logger.error(error_msg)
            raise

        finally:
            # Log the API call regardless of success/failure
            elapsed_ms = (time.time() - start_time) * 1000
            log_api_call(
                tool_name="SerperDevTool",
                endpoint=search_url,
                method="POST",
                status_code=status_code,
                response_time_ms=elapsed_ms,
                success=success,
                error=error_msg
            )
