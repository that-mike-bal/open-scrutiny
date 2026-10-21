"""
Tests for report generation and result classification.

Covers the pure functions that turn raw agent output into stored data
(_classify_result_status, _compute_confidence_score, parse_html_risk_assessment)
and the two report entry points (generate_automatic_report after a run, and
POST /reports/generate). Model calls and the database are mocked.
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from crewai_service.app import (
    _classify_result_status,
    _compute_confidence_score,
    app,
    generate_automatic_report,
    parse_html_risk_assessment,
)

client = TestClient(app)


def run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Result classification
# ---------------------------------------------------------------------------

LONG = "x" * 250


class TestClassifyResultStatus:
    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("", "FAIL"),
            (None, "FAIL"),
            ("I cannot fulfill this request because the tool failed", "FAIL"),
            ("Analysis complete. Overall Risk Level: HIGH RISK due to collisions", "HIGH_RISK"),
            ("Result: medium_risk after review", "MEDIUM_RISK"),
            ("Everything looks fine. LOW RISK.", "LOW_RISK"),
            ("STATUS: BLOCKED — string is reserved", "BLOCKED"),
            ("Search bypassed; model knowledge only", "REVIEW_REQUIRED"),
            ("Risk Level: CLEAR", "CLEAR"),
            ("Recommendation: PROCEED with application", "CLEAR"),
            ("Assessment: FAIL — hyphen in position 3", "FAIL"),
            ("Result: PASS", "PASS"),
            ("short note", "REVIEW_REQUIRED"),
            (LONG, "CLEAR"),
        ],
    )
    def test_classification(self, raw, expected):
        assert _classify_result_status(raw) == expected

    def test_failure_phrases_beat_risk_levels(self):
        text = "HIGH RISK was expected but the analysis could not be completed"
        assert _classify_result_status(text) == "FAIL"

    def test_pass_is_not_matched_inside_other_words(self):
        # "bypass" / "compass" must not read as PASS; long text without markers is CLEAR
        text = "The search was run via a bypass proxy and the compass heading was noted. " * 4
        assert _classify_result_status(text) == "CLEAR"


class TestComputeConfidenceScore:
    @staticmethod
    def summary(reliability="NONE", total=0, ok=0):
        return {"overall": {"data_reliability": reliability, "total_api_calls": total, "total_successful": ok}}

    def test_full_data_and_clear_result_is_high(self):
        assert _compute_confidence_score("CLEAR", self.summary("FULL", 3, 3)) == 0.9

    def test_no_data_and_review_required_is_low(self):
        assert _compute_confidence_score("REVIEW_REQUIRED", self.summary("NONE")) == 0.25

    def test_all_api_calls_failing_is_penalised(self):
        with_failures = _compute_confidence_score("CLEAR", self.summary("PARTIAL", 2, 0))
        without = _compute_confidence_score("CLEAR", self.summary("PARTIAL", 2, 2))
        assert without - with_failures == pytest.approx(0.2)

    def test_score_is_clamped_to_unit_interval(self):
        assert 0.0 <= _compute_confidence_score("FAIL", {}) <= 1.0
        assert _compute_confidence_score("CLEAR", self.summary("FULL", 1, 1)) <= 1.0


class TestParseRiskAssessment:
    def test_extracts_fields_from_markdown(self):
        report = (
            "# Report\n\nRisk Score: 68/100\n\n"
            "OVERALL RISK CLASSIFICATION: **MODERATE**\n\n"
            "Risk Level: Moderate\n\nRecommendation: Proceed with mitigation\n"
        )
        data = parse_html_risk_assessment(report)
        assert data["risk_score"] == 68
        assert data["risk_classification"] == "MODERATE"
        assert data["risk_level"] == "Moderate"
        assert data["recommendation"] == "Proceed with mitigation"

    def test_missing_fields_are_none(self):
        data = parse_html_risk_assessment("No structured content here.")
        assert data == {"risk_score": None, "risk_classification": None, "risk_level": None, "recommendation": None}


# ---------------------------------------------------------------------------
# Automatic report after a run
# ---------------------------------------------------------------------------

class TestGenerateAutomaticReport:
    @staticmethod
    def supabase_with_tasks(rows):
        sb = Mock()
        sb.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(data=rows)
        return sb

    @patch("crewai_service.app.save_report_to_database", new_callable=AsyncMock)
    @patch("crewai_service.app.generate_report_content", new_callable=AsyncMock)
    def test_generates_and_saves_when_tasks_exist(self, gen, save):
        gen.return_value = "# Report\n\nRisk Level: Low\n\nRecommendation: Proceed"
        sb = self.supabase_with_tasks(
            [
                {"task_name": "dns_stability_review", "status": "COMPLETED", "result_status": "PASS",
                 "result_data": {"summary": "ok"}, "completed_at": "2026-01-01T00:00:00Z"},
                {"task_name": "legal_gut_check", "status": "COMPLETED", "result_status": "CLEAR",
                 "result_data": {"summary": "ok"}, "completed_at": "2026-01-01T00:05:00Z"},
            ]
        )

        run(generate_automatic_report("tld-id", "example", sb))

        gen.assert_awaited_once()
        tld, evaluation_data = gen.await_args[0]
        assert tld == "example"
        assert [t["task_name"] for t in evaluation_data["task_executions"]] == ["dns_stability_review", "legal_gut_check"]
        save.assert_awaited_once()
        assert save.await_args[0][0] == "example"
        assert save.await_args[0][3]["risk_level"] == "Low"

    @patch("crewai_service.app.save_report_to_database", new_callable=AsyncMock)
    @patch("crewai_service.app.generate_report_content", new_callable=AsyncMock)
    def test_skips_when_no_task_executions(self, gen, save):
        run(generate_automatic_report("tld-id", "example", self.supabase_with_tasks([])))
        gen.assert_not_awaited()
        save.assert_not_awaited()

    @patch("crewai_service.app.save_report_to_database", new_callable=AsyncMock)
    @patch("crewai_service.app.generate_report_content", new_callable=AsyncMock)
    def test_model_failure_propagates(self, gen, save):
        gen.side_effect = RuntimeError("Gemini unavailable")
        sb = self.supabase_with_tasks([{"task_name": "t", "status": "COMPLETED", "result_data": {}}])
        with pytest.raises(RuntimeError, match="Gemini unavailable"):
            run(generate_automatic_report("tld-id", "example", sb))
        save.assert_not_awaited()


# ---------------------------------------------------------------------------
# POST /reports/generate
# ---------------------------------------------------------------------------

class TestReportGenerationEndpoint:
    def test_requires_evaluation_data(self):
        response = client.post("/reports/generate", json={"tld_string": "example"})
        assert response.status_code == 422

    def test_empty_task_executions_is_reported_as_failure(self):
        response = client.post(
            "/reports/generate",
            json={"tld_string": "example", "evaluation_data": {"task_executions": []}, "create_google_doc": False},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is False
        assert "No evaluation data" in body["error"]

    @patch("crewai_service.app.export_report_to_google_drive", return_value=None)
    @patch("crewai_service.app.save_report_to_database", new_callable=AsyncMock)
    @patch("crewai_service.app.generate_report_content", new_callable=AsyncMock)
    def test_successful_generation_returns_report_and_risk_fields(self, gen, save, export):
        gen.return_value = "# Report\n\nRisk Score: 20/100\n\nRisk Level: Low\n\nRecommendation: Proceed"
        response = client.post(
            "/reports/generate",
            json={
                "tld_string": "example",
                "evaluation_data": {"task_executions": [{"task_name": "dns_stability_review", "status": "COMPLETED"}]},
                "create_google_doc": False,
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["report"].startswith("# Report")
        assert body["risk_score"] == 20
        assert body["risk_level"] == "Low"
        save.assert_awaited_once()
        export.assert_called_once_with("example")

    @patch("crewai_service.app.generate_report_content", new_callable=AsyncMock, return_value="")
    def test_model_outage_is_reported_as_failure(self, gen):
        response = client.post(
            "/reports/generate",
            json={"tld_string": "example", "evaluation_data": {"task_executions": [{"task_name": "t"}]}},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is False
        assert "unavailable" in body["error"]
