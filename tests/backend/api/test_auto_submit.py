"""
Tests for POST /api/evaluations/auto-submit

The endpoint is the single entry point for evaluations. Contract under test:
  - checks server availability first and returns 409 while another evaluation runs
  - reuses an existing tld_strings row, otherwise inserts one
  - with auto-execution: marks the row RUNNING, schedules the background
    workflow task, and returns status RUNNING with the three workflow names
  - without auto-execution: returns status CREATED and schedules nothing
  - database (PostgREST) errors surface as HTTP 500 with a "Database error" detail

All database access goes through TldApplicationStore().supabase, which is mocked.
"""

from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient
from postgrest import APIError

from crewai_service.app import app

client = TestClient(app)

WORKFLOWS = ["technical_risk_assessment", "legal_risk_assessment", "policy_safeguard_review"]


def make_store(running=None, existing=None, inserted_id="new-id"):
    """Build a TldApplicationStore mock.

    The server-status check selects '*' filtered on overall_status, while the
    endpoint selects 'id' filtered on tld_string; both go through
    table().select().eq().execute(), so route on the select() argument.
    """
    store = Mock()

    def select(columns):
        chain = Mock()
        rows = (running or []) if columns == "*" else (existing or [])
        chain.eq.return_value.execute.return_value = Mock(data=rows)
        return chain

    table = store.supabase.table.return_value
    table.select.side_effect = select
    table.insert.return_value.execute.return_value = Mock(data=[{"id": inserted_id}])
    table.update.return_value.eq.return_value.execute.return_value = Mock(data=[{"id": inserted_id}])
    return store


def close_coroutine(coro):
    """Stand-in for asyncio.create_task that discards the coroutine cleanly."""
    coro.close()
    return Mock()


@pytest.fixture(autouse=True)
def no_json_side_effects():
    """The endpoint appends new strings to data/existing_tld_strings.json; keep tests off disk."""
    with patch("crewai_service.app._add_string_to_json_file"):
        yield


@pytest.fixture
def no_background_tasks():
    with patch("crewai_service.app.asyncio.create_task", side_effect=close_coroutine) as m:
        yield m


class TestAutoSubmitEndpoint:
    def test_new_string_with_auto_execution_starts_workflows(self, no_background_tasks):
        store = make_store()
        with patch("crewai_service.app.TldApplicationStore", return_value=store):
            response = client.post(
                "/api/evaluations/auto-submit",
                json={"tld_string": "teststring", "use_case": "Test use case", "enable_auto_execution": True},
            )

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "RUNNING"
        assert body["evaluation_id"] == "new-id"
        assert body["tld_string"] == "teststring"
        assert body["workflows_queued"] == WORKFLOWS
        assert body["message"] == "Evaluation started for .teststring"
        assert body["evaluation"] == {"id": "new-id", "tld_string": "teststring"}

        table = store.supabase.table.return_value
        assert table.insert.call_args[0][0]["tld_string"] == "teststring"
        assert table.update.call_args[0][0] == {"overall_status": "RUNNING"}
        no_background_tasks.assert_called_once()

    def test_without_auto_execution_creates_only(self, no_background_tasks):
        store = make_store()
        with patch("crewai_service.app.TldApplicationStore", return_value=store):
            response = client.post(
                "/api/evaluations/auto-submit",
                json={"tld_string": "teststring", "enable_auto_execution": False},
            )

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "CREATED"
        assert body["workflows_queued"] == []
        assert "Auto-execution disabled" in body["message"]
        store.supabase.table.return_value.update.assert_not_called()
        no_background_tasks.assert_not_called()

    def test_existing_string_is_reused_not_reinserted(self, no_background_tasks):
        store = make_store(existing=[{"id": "existing-id"}])
        with patch("crewai_service.app.TldApplicationStore", return_value=store):
            response = client.post(
                "/api/evaluations/auto-submit",
                json={"tld_string": "teststring", "enable_auto_execution": True},
            )

        assert response.status_code == 200
        assert response.json()["evaluation_id"] == "existing-id"
        store.supabase.table.return_value.insert.assert_not_called()

    def test_server_busy_returns_409_before_touching_the_row(self, no_background_tasks):
        store = make_store(running=[{"id": "running-id", "tld_string": "othertld", "overall_status": "RUNNING"}])
        with patch("crewai_service.app.TldApplicationStore", return_value=store):
            response = client.post(
                "/api/evaluations/auto-submit",
                json={"tld_string": "newtld", "enable_auto_execution": True},
            )

        assert response.status_code == 409
        assert "processing .othertld" in response.json()["detail"]
        store.supabase.table.return_value.insert.assert_not_called()
        no_background_tasks.assert_not_called()

    def test_database_unavailable_for_status_check_returns_409(self, no_background_tasks):
        with patch("crewai_service.app.TldApplicationStore", side_effect=RuntimeError("no db")):
            response = client.post(
                "/api/evaluations/auto-submit",
                json={"tld_string": "teststring", "enable_auto_execution": True},
            )

        assert response.status_code == 409
        no_background_tasks.assert_not_called()

    def test_postgrest_error_returns_500(self, no_background_tasks):
        store = Mock()
        store.supabase.table.return_value.select.return_value.eq.return_value.execute.side_effect = APIError(
            {"message": "Database connection failed"}
        )
        with patch("crewai_service.app.TldApplicationStore", return_value=store):
            response = client.post(
                "/api/evaluations/auto-submit",
                json={"tld_string": "teststring", "enable_auto_execution": False},
            )

        assert response.status_code == 500
        assert "Database error" in response.json()["detail"]

    def test_missing_tld_string_is_rejected(self):
        response = client.post("/api/evaluations/auto-submit", json={"use_case": "Test use case"})
        assert response.status_code == 422

    def test_string_type_defaults_to_primary(self, no_background_tasks):
        store = make_store()
        with patch("crewai_service.app.TldApplicationStore", return_value=store):
            client.post("/api/evaluations/auto-submit", json={"tld_string": "teststring", "enable_auto_execution": False})

        inserted = store.supabase.table.return_value.insert.call_args[0][0]
        assert inserted["string_type"] == "primary"
