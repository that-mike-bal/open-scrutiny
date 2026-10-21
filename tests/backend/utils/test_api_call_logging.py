"""
Unit tests for the API call logging infrastructure.

Tests:
  - log_api_call appends records correctly
  - clear_api_call_log resets the log
  - compute_tool_execution_summary aggregates and computes data_reliability
  - logged_get logs on success and failure, re-raises exceptions
  - Context var isolation between sequential clear/log cycles
"""

import time
from unittest.mock import MagicMock, patch

import pytest
import requests

from crewai_service.utils.api_call_logger import (
    clear_api_call_log,
    compute_tool_execution_summary,
    get_api_call_log,
    log_api_call,
)
from crewai_service.utils.logged_requests import (
    logged_get,
    logged_openai_call,
    logged_post,
    logged_serper_call,
    logged_supabase_rpc,
)


# ---------------------------------------------------------------------------
# api_call_logger core
# ---------------------------------------------------------------------------


class TestLogApiCall:
    def setup_method(self):
        clear_api_call_log()

    def test_appends_record(self):
        log_api_call(
            tool_name="TestTool",
            endpoint="https://example.com/api",
            method="GET",
            status_code=200,
            response_time_ms=42.5,
            success=True,
        )
        log = get_api_call_log()
        assert len(log) == 1
        rec = log[0]
        assert rec["tool_name"] == "TestTool"
        assert rec["api_endpoint"] == "https://example.com/api"
        assert rec["http_method"] == "GET"
        assert rec["status_code"] == 200
        assert rec["response_time_ms"] == 42.5
        assert rec["success"] is True
        assert rec["error"] is None
        assert "timestamp" in rec

    def test_appends_multiple(self):
        for i in range(5):
            log_api_call("T", "u", "GET", 200, float(i), True)
        assert len(get_api_call_log()) == 5

    def test_error_field_recorded(self):
        log_api_call("T", "u", "GET", None, 0.0, False, error="timeout")
        rec = get_api_call_log()[0]
        assert rec["success"] is False
        assert rec["error"] == "timeout"


class TestClearApiCallLog:
    def setup_method(self):
        clear_api_call_log()

    def test_clears(self):
        log_api_call("T", "u", "GET", 200, 1.0, True)
        assert len(get_api_call_log()) == 1
        clear_api_call_log()
        assert len(get_api_call_log()) == 0


class TestComputeToolExecutionSummary:
    def test_empty_calls(self):
        summary = compute_tool_execution_summary([])
        assert summary["overall"]["total_api_calls"] == 0
        assert summary["overall"]["data_reliability"] == "NONE"

    def test_all_success(self):
        calls = [
            {"tool_name": "A", "success": True},
            {"tool_name": "A", "success": True},
            {"tool_name": "B", "success": True},
        ]
        summary = compute_tool_execution_summary(calls)
        assert summary["A"]["total_calls"] == 2
        assert summary["A"]["successful_calls"] == 2
        assert summary["A"]["all_data_is_real"] is True
        assert summary["B"]["total_calls"] == 1
        assert summary["overall"]["data_reliability"] == "FULL"

    def test_all_failure(self):
        calls = [
            {"tool_name": "A", "success": False},
            {"tool_name": "A", "success": False},
        ]
        summary = compute_tool_execution_summary(calls)
        assert summary["A"]["all_data_is_real"] is False
        assert summary["overall"]["data_reliability"] == "NONE"

    def test_partial(self):
        calls = [
            {"tool_name": "A", "success": True},
            {"tool_name": "A", "success": False},
        ]
        summary = compute_tool_execution_summary(calls)
        assert summary["A"]["all_data_is_real"] is False
        assert summary["overall"]["total_successful"] == 1
        assert summary["overall"]["total_failed"] == 1
        assert summary["overall"]["data_reliability"] == "PARTIAL"


class TestContextVarIsolation:
    """Verify that clear_api_call_log properly isolates sequential runs."""

    def test_isolation(self):
        clear_api_call_log()
        log_api_call("Run1", "u", "GET", 200, 1.0, True)
        first_log = get_api_call_log()
        assert len(first_log) == 1

        clear_api_call_log()
        assert len(get_api_call_log()) == 0

        log_api_call("Run2", "u", "GET", 200, 1.0, True)
        second_log = get_api_call_log()
        assert len(second_log) == 1
        assert second_log[0]["tool_name"] == "Run2"


# ---------------------------------------------------------------------------
# logged_requests wrappers
# ---------------------------------------------------------------------------


class TestLoggedGet:
    def setup_method(self):
        clear_api_call_log()

    @patch("crewai_service.utils.logged_requests.requests.get")
    def test_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.ok = True
        mock_get.return_value = mock_resp

        resp = logged_get("TestTool", "https://example.com")
        assert resp.status_code == 200

        log = get_api_call_log()
        assert len(log) == 1
        assert log[0]["success"] is True
        assert log[0]["tool_name"] == "TestTool"
        assert log[0]["http_method"] == "GET"

    @patch("crewai_service.utils.logged_requests.requests.get")
    def test_http_error_status(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.ok = False
        mock_get.return_value = mock_resp

        resp = logged_get("TestTool", "https://example.com")
        assert resp.status_code == 500

        log = get_api_call_log()
        assert len(log) == 1
        assert log[0]["success"] is False
        assert log[0]["error"] == "HTTP 500"

    @patch("crewai_service.utils.logged_requests.requests.get")
    def test_exception_reraised(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError("refused")

        with pytest.raises(requests.exceptions.ConnectionError):
            logged_get("TestTool", "https://example.com")

        log = get_api_call_log()
        assert len(log) == 1
        assert log[0]["success"] is False
        assert "refused" in log[0]["error"]


class TestLoggedPost:
    def setup_method(self):
        clear_api_call_log()

    @patch("crewai_service.utils.logged_requests.requests.post")
    def test_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.ok = True
        mock_post.return_value = mock_resp

        resp = logged_post("TestTool", "https://example.com", json={"a": 1})
        assert resp.status_code == 200

        log = get_api_call_log()
        assert len(log) == 1
        assert log[0]["http_method"] == "POST"
        assert log[0]["success"] is True


class TestLoggedOpenaiCall:
    def setup_method(self):
        clear_api_call_log()

    def test_success(self):
        mock_fn = MagicMock(return_value="result")
        result = logged_openai_call("TestTool", mock_fn, model="gpt-4o-mini")
        assert result == "result"
        mock_fn.assert_called_once_with(model="gpt-4o-mini")

        log = get_api_call_log()
        assert len(log) == 1
        assert log[0]["success"] is True

    def test_failure_reraised(self):
        mock_fn = MagicMock(side_effect=RuntimeError("API error"))
        with pytest.raises(RuntimeError, match="API error"):
            logged_openai_call("TestTool", mock_fn)

        log = get_api_call_log()
        assert len(log) == 1
        assert log[0]["success"] is False
        assert "API error" in log[0]["error"]


class TestLoggedSerperCall:
    def setup_method(self):
        clear_api_call_log()

    def test_success(self):
        mock_tool = MagicMock()
        mock_tool.run.return_value = "search results"
        result = logged_serper_call("TestTool", mock_tool, "query")
        assert result == "search results"

        log = get_api_call_log()
        assert len(log) == 1
        assert log[0]["success"] is True
        assert log[0]["status_code"] is None  # serper doesn't expose status

    def test_failure_reraised(self):
        mock_tool = MagicMock()
        mock_tool.run.side_effect = RuntimeError("serper down")
        with pytest.raises(RuntimeError):
            logged_serper_call("TestTool", mock_tool, "query")

        log = get_api_call_log()
        assert log[0]["success"] is False


class TestLoggedSupabaseRpc:
    def setup_method(self):
        clear_api_call_log()

    def test_success(self):
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_client.rpc.return_value.execute.return_value = mock_result

        result = logged_supabase_rpc("TestTool", mock_client, "my_func", {"a": 1})
        assert result == mock_result
        mock_client.rpc.assert_called_once_with("my_func", {"a": 1})

        log = get_api_call_log()
        assert len(log) == 1
        assert log[0]["success"] is True
        assert "my_func" in log[0]["api_endpoint"]

    def test_failure_reraised(self):
        mock_client = MagicMock()
        mock_client.rpc.return_value.execute.side_effect = RuntimeError("db down")

        with pytest.raises(RuntimeError):
            logged_supabase_rpc("TestTool", mock_client, "my_func", {})

        log = get_api_call_log()
        assert log[0]["success"] is False
