"""
Tests for the two database access layers.

- crewai_service.utils.supabase_client.SupabaseClient: the service-side wrapper.
  It must disable itself (not crash) when credentials are missing, and must
  swallow PostgREST errors into None so a storage failure never kills an
  evaluation.
- db.tld_application_store.TldApplicationStore: the application/questions
  store used by the API. Every method returns a safe default on error.

The real Supabase SDK client is replaced with Mocks; no network.
"""

from unittest.mock import Mock, patch

import pytest

from crewai_service.utils import supabase_client as sc
from db import tld_application_store as store_module


# ---------------------------------------------------------------------------
# SupabaseClient wrapper
# ---------------------------------------------------------------------------

class TestSupabaseClientWrapper:
    def test_disabled_when_credentials_missing(self, monkeypatch):
        for var in ("SUPABASE_URL", "SUPABASE_SERVICE_KEY", "SUPABASE_ANON_KEY", "SUPABASE_KEY"):
            monkeypatch.delenv(var, raising=False)
        with patch.object(sc, "create_client") as create:
            client = sc.SupabaseClient()
        assert client.enabled is False
        assert client.client is None
        create.assert_not_called()
        assert client.table("tld_strings") is None
        assert client.store_tld_string({"tld_string": "x"}) is None

    def test_prefers_service_role_key(self, monkeypatch):
        monkeypatch.setenv("SUPABASE_URL", "http://localhost")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", "service-key")
        monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")
        with patch.object(sc, "create_client") as create:
            client = sc.SupabaseClient()
        create.assert_called_once_with("http://localhost", "service-key")
        assert client.enabled is True

    def test_store_tld_string_returns_inserted_row(self, monkeypatch):
        monkeypatch.setenv("SUPABASE_URL", "http://localhost")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", "service-key")
        sdk = Mock()
        sdk.table.return_value.insert.return_value.execute.return_value = Mock(
            data=[{"id": "test-uuid", "tld_string": "teststring", "overall_status": "PENDING"}]
        )
        with patch.object(sc, "create_client", return_value=sdk):
            client = sc.SupabaseClient()

        row = client.store_tld_string({"tld_string": "teststring", "overall_status": "PENDING"})

        sdk.table.assert_called_with("tld_strings")
        assert row["id"] == "test-uuid"

    def test_update_tld_string_filters_by_id(self, monkeypatch):
        monkeypatch.setenv("SUPABASE_URL", "http://localhost")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", "service-key")
        sdk = Mock()
        update_chain = sdk.table.return_value.update.return_value
        update_chain.eq.return_value.execute.return_value = Mock(data=[{"id": "test-uuid", "overall_status": "RUNNING"}])
        with patch.object(sc, "create_client", return_value=sdk):
            client = sc.SupabaseClient()

        row = client.update_tld_string("test-uuid", {"overall_status": "RUNNING"})

        sdk.table.return_value.update.assert_called_once_with({"overall_status": "RUNNING"})
        update_chain.eq.assert_called_once_with("id", "test-uuid")
        assert row["overall_status"] == "RUNNING"

    def test_storage_errors_are_swallowed(self, monkeypatch):
        monkeypatch.setenv("SUPABASE_URL", "http://localhost")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", "service-key")
        from postgrest import APIError

        sdk = Mock()
        sdk.table.return_value.insert.return_value.execute.side_effect = APIError({"message": "Connection failed"})
        with patch.object(sc, "create_client", return_value=sdk):
            client = sc.SupabaseClient()

        assert client.store_tld_string({"tld_string": "x"}) is None
        assert client.store_workflow_execution({"id": "w1"}) is None


# ---------------------------------------------------------------------------
# TldApplicationStore
# ---------------------------------------------------------------------------

@pytest.fixture
def store():
    sdk = Mock()
    with patch.object(store_module, "get_supabase", return_value=sdk):
        s = store_module.TldApplicationStore()
    return s, sdk


class TestTldApplicationStore:
    def test_default_applicant_is_first_row_or_none(self, store):
        s, sdk = store
        chain = sdk.table.return_value.select.return_value.limit.return_value
        chain.execute.return_value = Mock(data=[{"id": "a1", "legal_name": "Example Registry Ltd."}])
        assert s.get_default_applicant()["id"] == "a1"

        chain.execute.return_value = Mock(data=[])
        assert s.get_default_applicant() is None
        sdk.table.assert_called_with("applicants")

    def test_create_applicant_returns_new_id(self, store):
        s, sdk = store
        sdk.table.return_value.insert.return_value.execute.return_value = Mock(data=[{"id": "a2"}])
        assert s.create_applicant({"legal_name": "New Co"}) == "a2"
        sdk.table.return_value.insert.assert_called_once_with({"legal_name": "New Co"})

    def test_update_application_status_includes_completion_when_given(self, store):
        s, sdk = store
        update = sdk.table.return_value.update
        update.return_value.eq.return_value.execute.return_value = Mock(data=[{"id": "app1"}])

        assert s.update_application_status("app1", "IN_PROGRESS", completion_percentage=42.0) is True
        payload = update.call_args[0][0]
        assert payload["status"] == "IN_PROGRESS"
        assert payload["completion_percentage"] == 42.0
        assert "updated_at" in payload

        update.return_value.eq.return_value.execute.return_value = Mock(data=[])
        assert s.update_application_status("missing", "DONE") is False

    def test_get_question_by_number_uses_single_row(self, store):
        s, sdk = store
        chain = sdk.table.return_value.select.return_value.eq.return_value.single.return_value
        chain.execute.return_value = Mock(data={"question_number": "116", "question_text": "Applied-for string"})
        q = s.get_question_by_number("116")
        assert q["question_number"] == "116"
        sdk.table.assert_called_with("application_questions_enhanced")

    def test_errors_degrade_to_safe_defaults(self, store):
        s, sdk = store
        sdk.table.side_effect = RuntimeError("db down")
        assert s.get_default_applicant() is None
        assert s.create_applicant({}) is None
        assert s.update_application_status("x", "y") is False
        assert s.get_all_questions() == []
        assert s.get_question_by_number("1") is None
