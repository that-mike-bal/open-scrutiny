"""
Tests for the CrewBuilder: YAML config -> CrewAI agents, tasks, crews.

Config files are mocked via CrewBuilder._load_yaml (called in the order
agents, tasks, tools, workflows, environment). Agents get a real LLM object
from model_config, which needs GEMINI_API_KEY to be set (any value); nothing
is called over the network.
"""

import sys
import types
from unittest.mock import Mock, patch

import pytest
from crewai.tools import BaseTool

from crewai_service.crew import (
    DEFAULT_CONFIG_DIR,
    CrewBuilder,
    WorkflowBlockedException,
    build_crew_for_workflow,
)


class EchoTool(BaseTool):
    name: str = "Echo Tool"
    description: str = "Returns its input"

    def _run(self, text: str) -> str:
        return text


def configs(agents=None, tasks=None, tools=None, workflows=None, environment=None):
    return [agents or {}, tasks or {}, tools or {}, workflows or {}, environment or {"current_environment": "test"}]


class TestCrewBuilder:
    def test_defaults_to_the_evaluation_config_tree(self):
        builder = CrewBuilder()
        assert builder.config_dir == DEFAULT_CONFIG_DIR
        assert DEFAULT_CONFIG_DIR.name == "config" and DEFAULT_CONFIG_DIR.parent.name == "evaluation"
        assert set(builder.workflows_config) == {
            "technical_risk_assessment",
            "legal_risk_assessment",
            "policy_safeguard_review",
        }

    def test_shared_environment_file_is_used_when_tree_has_none(self):
        builder = CrewBuilder()
        assert builder.current_env in ("development", "production", "testing")
        assert "memory" in builder.env_settings

    @patch("crewai_service.crew.CrewBuilder._load_yaml")
    def test_initialization_loads_all_configs(self, mock_load_yaml):
        mock_load_yaml.side_effect = configs(
            agents={"test_agent": {"role": "Test Agent"}},
            tasks={"test_task": {"description": "Test Task"}},
            tools={"test_tool": {"name": "Test Tool"}},
            workflows={"test_workflow": {"agents": ["test_agent"]}},
        )
        builder = CrewBuilder("test_config")
        assert builder.agents_config == {"test_agent": {"role": "Test Agent"}}
        assert builder.workflows_config == {"test_workflow": {"agents": ["test_agent"]}}
        assert builder.current_env == "test"

    @patch("crewai_service.crew.CrewBuilder._load_yaml")
    def test_agents_are_built_with_their_declared_tools(self, mock_load_yaml):
        mock_load_yaml.side_effect = configs(
            agents={
                "risk_assessment_agent": {
                    "role": "Risk Assessment Specialist",
                    "goal": "Evaluate risks",
                    "backstory": "Expert in risk analysis",
                    "tools": ["echo_tool"],
                }
            },
            tools={"echo_tool": {"class": "EchoTool", "module": "tests_fake_tool_module"}},
        )
        fake_module = types.ModuleType("tests_fake_tool_module")
        fake_module.EchoTool = EchoTool
        # Register directly rather than via patch.dict(sys.modules): restoring the
        # whole module table would evict extension modules imported meanwhile.
        sys.modules["tests_fake_tool_module"] = fake_module
        try:
            builder = CrewBuilder("test_config")
            agents = builder._build_agents(["risk_assessment_agent"])
        finally:
            sys.modules.pop("tests_fake_tool_module", None)

        assert len(agents) == 1
        assert agents[0].role == "Risk Assessment Specialist"
        assert [t.name for t in agents[0].tools] == ["Echo Tool"]

    @patch("crewai_service.crew.CrewBuilder._load_yaml")
    def test_tasks_get_inputs_substituted_and_gate_metadata(self, mock_load_yaml):
        mock_load_yaml.side_effect = configs(
            agents={"gate_agent": {"role": "Binary Gate", "goal": "Check blocking conditions", "backstory": "Compliance checker"}},
            tasks={
                "binary_gate_task": {
                    "description": "Check if {tld_string} should be blocked. Example JSON: {\"score\": 0}",
                    "expected_output": "BLOCK or PROCEED for {tld_string}",
                    "agent": "gate_agent",
                    "binary_gate": True,
                    "blocking_conditions": ["BLOCK"],
                }
            },
        )
        builder = CrewBuilder("test_config")
        agents = builder._build_agents(["gate_agent"])
        tasks = builder._build_tasks(["binary_gate_task"], agents, {"tld_string": "example"}, {})

        assert len(tasks) == 1
        task = tasks[0]
        assert task.agent is agents[0]
        assert "Check if example should be blocked" in task.description
        assert '{"score": 0}' in task.description, "unknown braces must be left untouched"
        assert task.expected_output == "BLOCK or PROCEED for example"
        assert task._binary_gate is True
        assert task._blocking_conditions == ["BLOCK"]
        assert task._task_name == "binary_gate_task"

    def test_workflow_blocked_exception_carries_task_and_reason(self):
        exc = WorkflowBlockedException("binary_gate_task", "BLOCK: string is reserved", details="IANA")
        assert exc.task_name == "binary_gate_task"
        assert exc.details == "IANA"
        assert "BLOCK" in str(exc)


class TestWorkflowConfiguration:
    @patch("crewai_service.crew.CrewBuilder._load_yaml")
    def test_workflow_without_agents_or_tasks_is_rejected(self, mock_load_yaml):
        mock_load_yaml.side_effect = configs(workflows={"invalid_workflow": {"process": "sequential"}})
        builder = CrewBuilder("test_config")
        with pytest.raises(ValueError, match="invalid_workflow"):
            builder.build_crew("invalid_workflow", {})

    @patch("crewai_service.crew.CrewBuilder._load_yaml")
    def test_unknown_workflow_lists_available_ones(self, mock_load_yaml):
        mock_load_yaml.side_effect = configs(workflows={"known": {"agents": [], "tasks": []}})
        builder = CrewBuilder("test_config")
        with pytest.raises(ValueError, match="known"):
            builder.build_crew("missing", {})

    @patch("crewai_service.crew.CrewBuilder._load_yaml")
    def test_environment_specific_config(self, mock_load_yaml):
        mock_load_yaml.side_effect = configs(
            agents={"test_agent": {"role": "Test Agent"}},
            environment={
                "current_environment": "production",
                "production": {"memory": {"enabled": False}, "rate_limiting": {"max_rpm_default": 5}},
                "development": {"memory": {"enabled": True}},
            },
        )
        builder = CrewBuilder("test_config")
        assert builder.current_env == "production"
        assert builder.env_settings["rate_limiting"]["max_rpm_default"] == 5


class TestBuildCrewForWorkflow:
    def test_delegates_to_a_builder_with_the_given_config_dir(self):
        mock_builder = Mock()
        mock_builder.build_crew.return_value = Mock()
        with patch("crewai_service.crew.CrewBuilder", return_value=mock_builder) as builder_class:
            inputs = {"tld_string": "test", "use_case": "testing"}
            result = build_crew_for_workflow("risk_evaluation", inputs, config_dir="/tmp/cfg")

        builder_class.assert_called_once_with(config_dir="/tmp/cfg")
        mock_builder.build_crew.assert_called_once_with("risk_evaluation", inputs=inputs)
        assert result is mock_builder.build_crew.return_value


class TestBundledExample:
    """The shipped ICANN ruleset must stay buildable end to end (no network)."""

    @pytest.mark.parametrize("workflow", ["technical_risk_assessment", "legal_risk_assessment", "policy_safeguard_review"])
    def test_bundled_workflow_builds(self, workflow):
        crew = CrewBuilder().build_crew(workflow, {"tld_string": "example", "use_case": "demo"})
        assert crew.agents and crew.tasks
        assert all("example" in t.description for t in crew.tasks)
        assert all("{tld_string}" not in t.description for t in crew.tasks)

    @pytest.mark.parametrize(
        "workflow, validator_tasks",
        [
            ("technical_risk_assessment", ["technical_gut_check"]),
            ("legal_risk_assessment", ["legal_risk_validation", "legal_gut_check"]),
            ("policy_safeguard_review", ["policy_gut_check"]),
        ],
    )
    def test_validator_runs_the_validation_and_gut_check_tasks(self, workflow, validator_tasks):
        crew = CrewBuilder().build_crew(workflow, {"tld_string": "example", "use_case": "demo"})
        validator = next(a for a in crew.agents if a.role == "Data Validation & Fact-Checking Specialist")
        by_name = {t._task_name: t for t in crew.tasks}
        for name in validator_tasks:
            assert by_name[name].agent is validator, name
            # Validation tasks declare the outputs they review and get exactly those
            assert by_name[name].context, f"{name} must see the outputs it reviews"
        last = crew.tasks[-1]
        assert last.context == crew.tasks[:-1] or set(last.context) <= set(crew.tasks[:-1])

    def test_guidebook_search_is_wired_to_the_agents_whose_prompts_cite_it(self):
        builder = CrewBuilder()
        for agent_name in ("string_analyst", "trademark_specialist", "gac_advisor", "evaluation_validator"):
            tools = builder._get_agent_tools(agent_name)
            assert "ICANN Guidebook Search" in [t.name for t in tools], agent_name

    @patch("crewai_service.crew.CrewBuilder._load_yaml")
    def test_task_without_context_key_keeps_crewai_default(self, mock_load_yaml):
        from crewai.utilities.constants import NOT_SPECIFIED

        mock_load_yaml.side_effect = configs(
            agents={"a": {"role": "Analyst", "goal": "g", "backstory": "b"}},
            tasks={
                "first": {"description": "one", "expected_output": "x", "agent": "a"},
                "second": {"description": "two", "expected_output": "y", "agent": "a"},
                "third": {"description": "three", "expected_output": "z", "agent": "a", "context": ["first"]},
            },
        )
        builder = CrewBuilder("test_config")
        agents = builder._build_agents(["a"])
        first, second, third = builder._build_tasks(["first", "second", "third"], agents, {}, {})
        assert second.context is NOT_SPECIFIED, "unset context must fall through to all prior outputs"
        assert third.context == [first]
