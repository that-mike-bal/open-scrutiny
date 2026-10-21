"""
Logged HTTP / SDK wrappers.

Drop-in replacements that time calls, log to the context-var API call log,
and return original results.  On exception the failure is logged and the
exception is re-raised so existing tool error handling is preserved.
"""

import logging
import time
from typing import Any, Callable, Optional, Tuple

import requests

from crewai_service.utils.api_call_logger import log_api_call

logger = logging.getLogger(__name__)


def logged_get(tool_name: str, url: str, **kwargs: Any) -> requests.Response:
    """Wrap ``requests.get`` with timing and logging."""
    start = time.monotonic()
    try:
        response = requests.get(url, **kwargs)
        elapsed_ms = (time.monotonic() - start) * 1000
        log_api_call(
            tool_name=tool_name,
            endpoint=url,
            method="GET",
            status_code=response.status_code,
            response_time_ms=elapsed_ms,
            success=response.ok,
            error=None if response.ok else f"HTTP {response.status_code}",
        )
        return response
    except Exception as exc:
        elapsed_ms = (time.monotonic() - start) * 1000
        log_api_call(
            tool_name=tool_name,
            endpoint=url,
            method="GET",
            status_code=None,
            response_time_ms=elapsed_ms,
            success=False,
            error=str(exc),
        )
        raise


def brave_get_with_retry(
    tool_name: str,
    url: str,
    rate_limiter: Any,
    max_retries: int = 2,
    **kwargs: Any,
) -> Tuple[Optional[requests.Response], str]:
    """Brave-specific GET with shared rate limiting and 429 retry.

    Uses :func:`logged_get` internally so every attempt is audit-logged.

    Args:
        tool_name: Tool name for audit logging.
        url: Request URL.
        rate_limiter: :class:`BraveRateLimiter` instance.
        max_retries: Maximum retries on HTTP 429 (default 2).
        **kwargs: Forwarded to ``requests.get``.

    Returns:
        ``(response_or_None, status)`` where *status* is one of
        ``"success"``, ``"rate_limited"``, ``"quota_exhausted"``, ``"error"``.
    """
    for attempt in range(1 + max_retries):
        if not rate_limiter.wait_for_slot():
            return None, "quota_exhausted"

        try:
            response = logged_get(tool_name, url, **kwargs)

            if response.status_code == 200:
                rate_limiter.record_success()
                return response, "success"

            if response.status_code == 429:
                retry_after_raw = response.headers.get("Retry-After")
                retry_after = (
                    float(retry_after_raw) if retry_after_raw else None
                )
                wait_time = rate_limiter.record_429(retry_after)

                if attempt < max_retries:
                    logger.warning(
                        "Brave 429 on attempt %d/%d, waiting %.1fs before retry",
                        attempt + 1,
                        1 + max_retries,
                        wait_time,
                    )
                    time.sleep(wait_time)
                    continue

                # All retries exhausted
                rate_limiter.mark_quota_exhausted()
                return response, "rate_limited"

            # Non-429 error — don't retry
            return response, "error"

        except requests.exceptions.RequestException as exc:
            logger.warning("Request exception for %s: %s", tool_name, exc)
            if attempt < max_retries:
                time.sleep(2 ** (attempt + 1))
                continue
            return None, "error"

    return None, "error"


def logged_post(tool_name: str, url: str, **kwargs: Any) -> requests.Response:
    """Wrap ``requests.post`` with timing and logging."""
    start = time.monotonic()
    try:
        response = requests.post(url, **kwargs)
        elapsed_ms = (time.monotonic() - start) * 1000
        log_api_call(
            tool_name=tool_name,
            endpoint=url,
            method="POST",
            status_code=response.status_code,
            response_time_ms=elapsed_ms,
            success=response.ok,
            error=None if response.ok else f"HTTP {response.status_code}",
        )
        return response
    except Exception as exc:
        elapsed_ms = (time.monotonic() - start) * 1000
        log_api_call(
            tool_name=tool_name,
            endpoint=url,
            method="POST",
            status_code=None,
            response_time_ms=elapsed_ms,
            success=False,
            error=str(exc),
        )
        raise


def logged_openai_call(
    tool_name: str, callable_fn: Callable[..., Any], *args: Any, **kwargs: Any
) -> Any:
    """Wrap an OpenAI SDK call (e.g. ``client.chat.completions.create``)."""
    # Best-effort endpoint description
    endpoint = getattr(callable_fn, "__qualname__", "openai")
    start = time.monotonic()
    try:
        result = callable_fn(*args, **kwargs)
        elapsed_ms = (time.monotonic() - start) * 1000
        log_api_call(
            tool_name=tool_name,
            endpoint=endpoint,
            method="POST",
            status_code=200,
            response_time_ms=elapsed_ms,
            success=True,
        )
        return result
    except Exception as exc:
        elapsed_ms = (time.monotonic() - start) * 1000
        log_api_call(
            tool_name=tool_name,
            endpoint=endpoint,
            method="POST",
            status_code=None,
            response_time_ms=elapsed_ms,
            success=False,
            error=str(exc),
        )
        raise


def logged_serper_call(
    tool_name: str, serper_tool: Any, query: str
) -> Any:
    """Wrap ``SerperDevTool.run()`` with timing and logging.

    We can't see the internal HTTP status so ``status_code`` is ``None``.
    """
    start = time.monotonic()
    try:
        result = serper_tool.run(query)
        elapsed_ms = (time.monotonic() - start) * 1000
        log_api_call(
            tool_name=tool_name,
            endpoint="serper.dev",
            method="POST",
            status_code=None,
            response_time_ms=elapsed_ms,
            success=True,
        )
        return result
    except Exception as exc:
        elapsed_ms = (time.monotonic() - start) * 1000
        log_api_call(
            tool_name=tool_name,
            endpoint="serper.dev",
            method="POST",
            status_code=None,
            response_time_ms=elapsed_ms,
            success=False,
            error=str(exc),
        )
        raise


def logged_supabase_rpc(
    tool_name: str, client: Any, rpc_name: str, params: dict
) -> Any:
    """Wrap ``supabase.rpc(name, params).execute()``."""
    endpoint = f"supabase.rpc({rpc_name})"
    start = time.monotonic()
    try:
        result = client.rpc(rpc_name, params).execute()
        elapsed_ms = (time.monotonic() - start) * 1000
        log_api_call(
            tool_name=tool_name,
            endpoint=endpoint,
            method="POST",
            status_code=200,
            response_time_ms=elapsed_ms,
            success=True,
        )
        return result
    except Exception as exc:
        elapsed_ms = (time.monotonic() - start) * 1000
        log_api_call(
            tool_name=tool_name,
            endpoint=endpoint,
            method="POST",
            status_code=None,
            response_time_ms=elapsed_ms,
            success=False,
            error=str(exc),
        )
        raise
