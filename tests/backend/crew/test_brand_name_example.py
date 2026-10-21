"""
The second bundled ruleset (examples/brand-name-check) must build from its own
config tree and ship its own tool. No network: agents get an LLM object from
model_config (any GEMINI_API_KEY value will do) and nothing is kicked off.
"""

import json
from pathlib import Path

import pytest

from crewai_service.crew import CrewBuilder

EXAMPLE_DIR = Path(__file__).resolve().parents[3] / "examples" / "brand-name-check"
CONFIG_DIR = EXAMPLE_DIR / "config"
INPUTS = {"product_name": "Lumen", "category": "desk lamp"}


@pytest.fixture(scope="module")
def crew():
    return CrewBuilder(config_dir=str(CONFIG_DIR)).build_crew("brand_name_check", INPUTS)


class TestExampleTreeBuilds:
    def test_workflow_validates_against_its_own_tree(self):
        result = CrewBuilder(config_dir=str(CONFIG_DIR)).validate_workflow("brand_name_check")
        assert result["valid"], result["errors"]

    def test_two_agents_three_tasks(self, crew):
        assert [a.role for a in crew.agents] == ["Brand Guideline Guardian", "Naming Reviewer"]
        assert [t._task_name for t in crew.tasks] == [
            "guideline_compliance_check",
            "distinctiveness_review",
            "naming_gut_check",
        ]

    def test_tool_is_imported_from_the_example_tree(self, crew):
        guardian, reviewer = crew.agents
        assert [t.name for t in guardian.tools] == ["Brand Guideline Lookup"]
        assert reviewer.tools == []
        assert type(guardian.tools[0]).__module__ == "brand_tools.guideline_lookup"

    def test_inputs_are_substituted_and_context_wired(self, crew):
        compliance, review, gut = crew.tasks
        assert all("Lumen" in t.description for t in crew.tasks)
        assert all("{product_name}" not in t.description for t in crew.tasks)
        assert "desk lamp" in review.description
        assert review.context == [compliance]
        assert gut.context == [compliance, review]
        assert compliance.agent is crew.agents[0]
        assert review.agent is gut.agent is crew.agents[1]


class TestGuidelineTool:
    """The local-data tool runs with no model and no network."""

    def _tool(self):
        from brand_tools.guideline_lookup import BrandGuidelineLookupTool  # on sys.path after build
        return BrandGuidelineLookupTool()

    def test_clean_name_passes(self, crew):
        result = json.loads(self._tool()._run("Lumen"))
        assert result["status"] == "PASS"
        assert all(c["result"] == "PASS" for c in result["checks"])

    def test_prohibited_term_and_existing_product_are_blocking(self, crew):
        result = json.loads(self._tool()._run("AtlasPro"))
        assert result["status"] == "BLOCKED"
        failed = {c["rule"]: c for c in result["checks"] if c["result"] == "FAIL"}
        assert "prohibited_terms" in failed and "pro" in failed["prohibited_terms"]["detail"]
        assert "Atlas" in result["related_existing_products"]

    def test_soft_rule_only_flags(self, crew):
        result = json.loads(self._tool()._run("Emberly"))  # starts with 'e', ends with '-ly'
        assert result["status"] == "FLAGGED"
        failed = {c["rule"] for c in result["checks"] if c["result"] == "FAIL"}
        assert failed == {"must_not_start_with", "forbidden_suffixes"}
