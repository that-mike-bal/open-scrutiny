# ==========================================================================
# CUSTOMIZE: CrewBuilder assembles crews from the YAML configs in evaluation/config/ (and application/config/ for generation). To retarget, edit the YAML (agents/tasks/tools/workflows), not usually this file.
# This platform is a domain-agnostic evaluate-then-generate engine; the
# gTLD/ICANN ruleset is just the bundled example. Grep for 'CUSTOMIZE:'
# to find every retargeting point. See the README's Customize section.
# ==========================================================================

"""
Dynamic Crew Builder

Loads agents, tasks, tools, and workflows from YAML configuration files
and builds CrewAI crews on-the-fly based on workflow specifications.

Enhanced with binary blocking gates for immediate workflow termination.
"""

import yaml
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
import importlib
import re
import sys

from crewai import Agent, Task, Crew, Process
from crewai_service.utils.model_config import get_model_for_agent

logger = logging.getLogger(__name__)

# Default config tree: the evaluation ruleset. Resolved relative to this file so
# it works regardless of the process working directory (Docker, Render, pytest).
_PACKAGE_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_DIR = _PACKAGE_DIR / "evaluation" / "config"
# Shared, domain-independent runtime settings (memory, rate limits per environment).
SHARED_ENVIRONMENT_FILE = _PACKAGE_DIR / "environment.yaml"


class WorkflowBlockedException(Exception):
    """Exception raised when workflow is blocked by binary gate."""
    def __init__(self, task_name: str, blocking_reason: str, details: str = ""):
        self.task_name = task_name
        self.blocking_reason = blocking_reason
        self.details = details
        super().__init__(f"Workflow blocked at {task_name}: {blocking_reason}")


class CrewBuilder:
    """Dynamic crew builder that constructs crews from YAML configurations."""
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize the crew builder.
        
        Args:
            config_dir: Directory containing YAML configuration files.
                Defaults to crewai_service/evaluation/config.
        """
        self.config_dir = Path(config_dir) if config_dir else DEFAULT_CONFIG_DIR
        self.agents_config = self._load_yaml("agents.yaml")
        self.tasks_config = self._load_yaml("tasks.yaml")
        self.tools_config = self._load_yaml("tools.yaml")
        self.workflows_config = self._load_yaml("workflows.yaml")
        
        # Load environment-specific configuration (shared across config trees;
        # a config tree may override it with its own environment.yaml)
        self.env_config = self._load_yaml("environment.yaml", fallback=SHARED_ENVIRONMENT_FILE)
        self.current_env = self.env_config.get("current_environment", "development")
        self.env_settings = self.env_config.get(self.current_env, {})
        
        # Debug: Print loaded workflows and environment
        logger.info(f"DEBUG: Loaded workflows: {list(self.workflows_config.keys())}")
        logger.info(f"🌍 Environment: {self.current_env}")
        logger.info(f"🧠 Memory enabled: {self.env_settings.get('memory', {}).get('enabled', False)}")
        
        # Cache for loaded tools
        self._tool_cache = {}
        
        logger.info("CrewBuilder initialized with configurations loaded")
    
    def _load_yaml(self, filename: str, fallback: Optional[Path] = None) -> Dict[str, Any]:
        """Load YAML configuration file from the config dir (or ``fallback`` if absent there)."""
        file_path = self.config_dir / filename
        if fallback is not None and not file_path.exists() and fallback.exists():
            file_path = fallback
        try:
            with open(file_path, 'r') as file:
                return yaml.safe_load(file) or {}
        except FileNotFoundError:
            logger.warning(f"Configuration file not found: {file_path}")
            return {}
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML file {file_path}: {e}")
            return {}
    
    def get_available_workflows(self) -> Dict[str, Dict[str, Any]]:
        """Get list of available workflows with their metadata."""
        return {
            name: {
                "name": config.get("name", name),
                "description": config.get("description", ""),
                "agents": config.get("agents", []),
                "tasks": config.get("tasks", []),
                "binary_gates": config.get("binary_gates", False),
                "blocking_tasks": config.get("blocking_tasks", [])
            }
            for name, config in self.workflows_config.items()
        }
    
    def build_crew(self, workflow_name: str, inputs: Dict[str, Any] = None) -> Crew:
        """
        Build a crew for the specified workflow.
        
        Args:
            workflow_name: Name of the workflow to build
            inputs: Input parameters for the workflow
            
        Returns:
            Configured Crew instance
            
        Raises:
            ValueError: If workflow not found or configuration invalid
        """
        if inputs is None:
            inputs = {}
            
        if workflow_name not in self.workflows_config:
            available = list(self.workflows_config.keys())
            raise ValueError(f"Workflow '{workflow_name}' not found. Available: {available}")
        
        workflow_config = self.workflows_config[workflow_name]
        
        # Handle legacy workflow redirects
        if workflow_config.get("redirect_to"):
            redirect_workflow = workflow_config["redirect_to"]
            logger.info(f"Redirecting legacy workflow '{workflow_name}' to '{redirect_workflow}'")
            return self.build_crew(redirect_workflow, inputs)
        
        # Check if workflow is deprecated
        if workflow_config.get("deprecated", False):
            logger.warning(f"Using deprecated workflow '{workflow_name}'. Consider using the recommended replacement.")
            if workflow_config.get("recommended_replacement"):
                logger.warning(f"Recommended replacement: {workflow_config['recommended_replacement']}")
        
        workflow_config = self.workflows_config[workflow_name]
        
        # Build agents
        agents = self._build_agents(workflow_config.get("agents", []))

        # Validate that agents with configured tools actually loaded them
        self._validate_agent_tools(agents, workflow_config.get("agents", []))

        # Build tasks with context dependencies and binary blocking
        tasks = self._build_tasks(workflow_config.get("tasks", []), agents, inputs, workflow_config)

        if not agents or not tasks:
            raise ValueError(
                f"Workflow '{workflow_name}' must define at least one agent and one task "
                f"(got {len(agents)} agent(s), {len(tasks)} task(s)); check workflows.yaml"
            )
        
        # Configure process
        process = self._get_process(workflow_config.get("process", "sequential"))
        
        # Extract workflow-level settings with environment overrides
        memory_enabled = self.env_settings.get("memory", {}).get("enabled", workflow_config.get("memory", True))
        share_crew = self.env_settings.get("memory", {}).get("share_crew", workflow_config.get("share_crew", True))
        
        # Use environment-specific rate limiting
        default_rpm = self.env_settings.get("rate_limiting", {}).get("max_rpm_default", 15)
        max_rpm = workflow_config.get("max_rpm", default_rpm)
        
        # Prepare crew configuration
        crew_config = {
            "agents": agents,
            "tasks": tasks,
            "process": process,
            "memory": memory_enabled,
            "verbose": workflow_config.get("verbose", True),
            "share_crew": share_crew,
            "max_rpm": max_rpm
        }
        
        # Add manager_llm for hierarchical processes
        if process == Process.hierarchical:
            manager_llm_name = workflow_config.get("manager_llm", "claude-3-sonnet")
            from crewai_service.utils.model_config import get_model_by_name
            crew_config["manager_llm"] = get_model_by_name(manager_llm_name)
            logger.info(f"Using manager LLM: {manager_llm_name} for hierarchical process")
        
        # Create crew with binary blocking support and context optimization
        crew = Crew(**crew_config)
        
        # Add binary blocking metadata to crew
        crew._binary_gates = workflow_config.get("binary_gates", False)
        crew._blocking_tasks = workflow_config.get("blocking_tasks", [])
        crew._stop_on_blocked = workflow_config.get("stop_on_blocked", False)
        
        logger.info(f"Built crew for workflow '{workflow_name}' with {len(agents)} agents and {len(tasks)} tasks")
        logger.info(f"Context optimization: memory={memory_enabled}, share_crew={share_crew}, max_rpm={max_rpm}")
        if crew._binary_gates:
            logger.info(f"Binary blocking enabled for tasks: {crew._blocking_tasks}")
        
        return crew
    
    def _build_agents(self, agent_names: List[str]) -> List[Agent]:
        """Build agents with optimal model assignments and memory configuration."""
        agents = []
        
        for agent_name in agent_names:
            if agent_name not in self.agents_config:
                logger.warning(f"Agent '{agent_name}' not found in configuration")
                continue
            
            agent_config = self.agents_config[agent_name]
            
            # Get optimal model for this agent type
            llm = get_model_for_agent(agent_name)
            
            # Get tools for this agent
            tools = self._get_agent_tools(agent_name)
            
            # Extract memory and context settings with environment overrides
            memory_enabled = self.env_settings.get("memory", {}).get("enabled", agent_config.get("memory", True))
            respect_context_window = self.env_settings.get("api_optimization", {}).get("respect_context_window", 
                                                         agent_config.get("respect_context_window", True))
            
            # Use environment-specific rate limiting for agents
            default_agent_rpm = self.env_settings.get("rate_limiting", {}).get("max_rpm_default", 15)
            max_rpm = agent_config.get("max_rpm", default_agent_rpm)
            
            # Create agent with specific model assignment and memory configuration
            agent = Agent(
                role=agent_config.get("role", agent_name),
                goal=agent_config.get("goal", ""),
                backstory=agent_config.get("backstory", ""),
                tools=tools,
                llm=llm,  # Assign optimal model
                verbose=True,
                memory=memory_enabled,  # Enable memory for context sharing
                respect_context_window=respect_context_window,  # Respect context limits
                max_rpm=max_rpm  # Limit API calls to reduce costs
            )
            
            agents.append(agent)
            logger.debug(f"Created agent '{agent_name}' with model '{llm.model}', memory={memory_enabled}, max_rpm={max_rpm}, and {len(tools)} tools")
        
        return agents
    
    def _validate_agent_tools(self, agents: List[Agent], agent_names: List[str]) -> None:
        """Verify that agents with configured tools actually loaded at least one.

        Raises ValueError if an agent's tools.yaml entries all failed to load,
        since that means the agent cannot perform its job.
        """
        for agent_name, agent in zip(agent_names, agents):
            agent_config = self.agents_config.get(agent_name, {})
            configured_tools = agent_config.get("tools", [])
            if not configured_tools:
                continue  # Agent doesn't need any tools

            loaded_count = len(agent.tools) if agent.tools else 0
            if loaded_count == 0:
                raise ValueError(
                    f"Agent '{agent_name}' requires tools {configured_tools} but none loaded successfully. "
                    f"Check that API keys are configured and tool modules are importable."
                )

            if loaded_count < len(configured_tools):
                missing = len(configured_tools) - loaded_count
                logger.warning(
                    f"Agent '{agent_name}' loaded {loaded_count}/{len(configured_tools)} tools — "
                    f"{missing} tool(s) failed to load"
                )

    def _build_tasks(self, task_names: List[str], agents: List[Agent], inputs: Dict[str, Any], workflow_config: Dict[str, Any]) -> List[Task]:
        """Build tasks from configuration with input substitution and binary blocking."""
        tasks = []
        task_map = {}  # For context dependencies
        
        # Check if binary blocking is enabled
        binary_gates_enabled = workflow_config.get("binary_gates", False)
        blocking_tasks = workflow_config.get("blocking_tasks", [])
        
        for i, task_name in enumerate(task_names):
            if task_name not in self.tasks_config:
                logger.warning(f"Task '{task_name}' not found in configuration")
                continue
            
            task_config = self.tasks_config[task_name]
            
            # Substitute inputs in description and expected_output
            description = self._substitute_inputs(task_config.get("description", ""), inputs)
            expected_output = self._substitute_inputs(task_config.get("expected_output", ""), inputs)
            
            # Add binary blocking instructions if enabled
            if binary_gates_enabled and task_name in blocking_tasks:
                description = self._add_blocking_instructions(description, task_name)
                expected_output = self._add_blocking_output_format(expected_output, task_name)
            
            # Assign agent based on task configuration
            agent_name = task_config.get("agent", "")
            agent = None
            
            # Find the agent by name
            for a in agents:
                if hasattr(a, 'role') and agent_name in a.role.lower():
                    agent = a
                    break
                # Also check if agent_name matches the agent configuration key
                for agent_key, agent_config in self.agents_config.items():
                    if agent_key == agent_name and agent_config.get("role", "") == a.role:
                        agent = a
                        break
                if agent:
                    break
            
            # Fallback to index-based assignment if no match found
            if agent is None:
                agent = agents[min(i, len(agents) - 1)]
                logger.warning(f"Could not find agent '{agent_name}' for task '{task_name}', using fallback agent '{agent.role}'")
            else:
                logger.info(f"Assigned task '{task_name}' to agent '{agent.role}'")
            
            # Build context dependencies. Only pass `context` when the task
            # declares one: an empty list would give the task NO prior output,
            # whereas leaving it unset lets a sequential crew pass every
            # previous task's output (what gut checks and validators need).
            task_kwargs: Dict[str, Any] = {}
            if "context" in task_config:
                context = []
                for context_task_name in task_config["context"]:
                    if context_task_name in task_map:
                        context.append(task_map[context_task_name])
                    else:
                        logger.warning(f"Task '{task_name}' lists unknown context task '{context_task_name}'")
                task_kwargs["context"] = context

            # Add async execution option
            async_execution = task_config.get("async_execution", False)

            # Create task with context dependencies and binary blocking
            task = Task(
                description=description,
                expected_output=expected_output,
                agent=agent,
                async_execution=async_execution,
                **task_kwargs,
            )
            
            # Add binary blocking metadata
            task._is_blocking_task = task_name in blocking_tasks
            task._binary_gate = task_config.get("binary_gate", False)
            task._blocking_conditions = task_config.get("blocking_conditions", [])
            task._task_name = task_name
            
            tasks.append(task)
            task_map[task_name] = task
            logger.debug(f"Created task '{task_name}' for agent '{agent.role}' (blocking: {task._is_blocking_task})")
        
        return tasks
    
    def _add_blocking_instructions(self, description: str, task_name: str) -> str:
        """Add binary blocking instructions to task description."""
        blocking_instruction = f"""
        
🚨 BINARY BLOCKING GATE ACTIVE 🚨
Task: {task_name}
CRITICAL: If you detect any blocking condition, immediately return:
- Status: BLOCKED
- Reason: [specific blocking reason]
- Details: [brief explanation]
- Recommendation: HALT WORKFLOW

This will immediately terminate the entire workflow to save processing costs.
Do not proceed with analysis if blocking conditions are detected.
        """
        return f"{description}\n\n{blocking_instruction}"
    
    def _add_blocking_output_format(self, expected_output: str, task_name: str) -> str:
        """Add binary blocking output format to expected output."""
        blocking_format = f"""
        
🚨 BINARY BLOCKING OUTPUT FORMAT:
If blocking conditions detected, return EXACTLY this format:

BINARY_GATE_RESULT: BLOCKED
BLOCKING_REASON: [specific reason]
TASK_NAME: {task_name}
DETAILS: [brief explanation]
RECOMMENDATION: HALT_WORKFLOW

Otherwise, provide the standard analysis output above.
        """
        if not expected_output.strip().endswith('.'):
            expected_output += "."
        
        return f"{expected_output} {blocking_format}"
    
    def check_for_blocking(self, task_output: str, task_name: str) -> Optional[Dict[str, str]]:
        """
        Check if task output indicates workflow should be blocked.
        
        Args:
            task_output: The output from the task
            task_name: Name of the task
            
        Returns:
            Dict with blocking information if blocked, None otherwise
        """
        if not task_output:
            return None
        
        # Check for binary blocking indicators
        blocking_patterns = [
            r"BINARY_GATE_RESULT:\s*BLOCKED",
            r"STATUS:\s*BLOCKED",
            r"BLOCKED",
            r"HALT\s*WORKFLOW",
            r"TERMINATE\s*IMMEDIATELY"
        ]
        
        for pattern in blocking_patterns:
            if re.search(pattern, task_output, re.IGNORECASE):
                # Extract blocking details
                reason = self._extract_blocking_reason(task_output)
                details = self._extract_blocking_details(task_output)
                
                return {
                    "task_name": task_name,
                    "blocking_reason": reason,
                    "details": details,
                    "raw_output": task_output
                }
        
        # Check if the task output contains the blocking signal
        if "BINARY_GATE_RESULT: BLOCKED" in task_output.upper():
            reason = self._extract_blocking_reason(task_output)
            details = self._extract_blocking_details(task_output)
            logger.warning(f"Blocking condition met for task '{task_name}': {reason}")
            return {"reason": reason, "details": details}
        return None
    
    def _extract_blocking_reason(self, output: str) -> str:
        """Extract blocking reason from task output."""
        patterns = [
            r"BLOCKING_REASON:\s*([^\n]+)",
            r"Reason:\s*([^\n]+)",
            r"BLOCKED:\s*([^\n]+)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return "No specific reason found in output"
    
    def _extract_blocking_details(self, output: str) -> str:
        """Extract blocking details from task output."""
        patterns = [
            r"DETAILS:\s*([^\n]+)",
            r"Details:\s*([^\n]+)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return "No additional details found."
    
    def _get_agent_tools(self, agent_name: str) -> List[Any]:
        """
        Get all tools assigned to an agent, including workflow-level tools.
        This now correctly loads tools and their configurations.
        """
        agent_config = self.agents_config.get(agent_name, {})
        tool_names = agent_config.get("tools", [])
        
        # Add workflow-level tools if any
        # This part seems complex, let's simplify by assuming tools are defined per agent
        # For workflow-level tools, they should be explicitly added to agents in the workflow config if needed.

        tools = []
        for tool_name in tool_names:
            tool_config = self.tools_config.get(tool_name, {})
            tool = self._load_tool(tool_name, tool_config)
            if tool:
                tools.append(tool)
        return tools

    def _load_tool(self, tool_name: str, tool_config: Dict[str, Any]) -> Optional[Any]:
        """
        Dynamically load a tool by its name and configuration.
        This version is more robust and handles initialization arguments.
        """
        if tool_name in self._tool_cache:
            return self._tool_cache[tool_name]

        try:
            module_path = tool_config.get("module")
            class_name = tool_config.get("class")
            
            if not module_path or not class_name:
                logger.error(f"Tool '{tool_name}' is missing 'module' or 'class' in tools.yaml")
                return None

            # Dynamically import the module and get the class. If the module is
            # not on sys.path, retry with the config tree's parent directory so a
            # config tree can ship its tools next to its YAML (see docs/ADAPTING.md).
            try:
                module = importlib.import_module(module_path)
            except ImportError:
                tree_root = str(self.config_dir.resolve().parent)
                if tree_root in sys.path:
                    raise
                logger.info(f"Tool module '{module_path}' not importable; retrying with '{tree_root}' on sys.path")
                sys.path.insert(0, tree_root)
                module = importlib.import_module(module_path)
            tool_class = getattr(module, class_name)
            
            # Get initialization arguments from config
            args = tool_config.get("args", {})

            # Initialize the tool with its arguments
            tool = tool_class(**args)
            self._tool_cache[tool_name] = tool
            logger.info(f"Successfully loaded tool: '{tool_name}' from {module_path}.{class_name}")
            return tool

        except ImportError:
            logger.error(f"Could not import module for tool '{tool_name}': {module_path}")
        except AttributeError:
            logger.error(f"Could not find class '{class_name}' in module '{module_path}' for tool '{tool_name}'")
        except Exception as e:
            logger.error(f"Failed to load tool '{tool_name}': {e}", exc_info=True)
            
        return None

    def _substitute_inputs(self, text: str, inputs: Dict[str, Any]) -> str:
        """Substitute input variables in text using {variable} format."""
        if not text:
            return ""
        
        # Use safer string substitution to avoid warnings on JSON examples
        try:
            # Only substitute known input variables to avoid JSON example warnings
            import re
            for key, value in inputs.items():
                pattern = r'\{' + re.escape(key) + r'\}'
                text = re.sub(pattern, str(value), text)
            return text
        except Exception as e:
            logger.warning(f"Error in text substitution: {e}")
            return text
    
    def _get_process(self, process_name: str) -> Process:
        """Get Process enum value from string."""
        process_map = {
            "sequential": Process.sequential,
            "hierarchical": Process.hierarchical
        }
        
        return process_map.get(process_name.lower(), Process.sequential)
    
    def validate_workflow(self, workflow_name: str) -> Dict[str, Any]:
        """
        Validate a workflow configuration to ensure all components are defined.
        
        Args:
            workflow_name: The name of the workflow to validate
            
        Returns:
            A dictionary containing validation results (valid, errors, warnings)
        """
        results = {"valid": True, "errors": [], "warnings": []}
        
        if workflow_name not in self.workflows_config:
            results["valid"] = False
            results["errors"].append(f"Workflow '{workflow_name}' not found.")
            return results
        
        config = self.workflows_config[workflow_name]
        
        # Validate agents
        agent_names = config.get("agents", [])
        if not agent_names:
            results["warnings"].append(f"Workflow '{workflow_name}' has no agents assigned.")
        
        for agent_name in agent_names:
            if agent_name not in self.agents_config:
                results["valid"] = False
                results["errors"].append(f"Agent '{agent_name}' not found in agents.yaml.")
            else:
                # Validate agent tools
                agent_config = self.agents_config[agent_name]
                tool_names = agent_config.get("tools", [])
                for tool_name in tool_names:
                    if tool_name not in self.tools_config:
                        results["valid"] = False
                        results["errors"].append(f"Tool '{tool_name}' for agent '{agent_name}' not found in tools.yaml.")

        # Validate tasks
        task_names = config.get("tasks", [])
        if not task_names:
            results["warnings"].append(f"Workflow '{workflow_name}' has no tasks assigned.")
            
        for task_name in task_names:
            if task_name not in self.tasks_config:
                results["valid"] = False
                results["errors"].append(f"Task '{task_name}' not found in tasks.yaml.")
            else:
                # Validate task agent assignment
                task_config = self.tasks_config[task_name]
                task_agent = task_config.get("agent")
                if not task_agent:
                    results["errors"].append(f"Task '{task_name}' does not have an agent assigned.")
                elif task_agent not in agent_names:
                    results["warnings"].append(f"Agent '{task_agent}' for task '{task_name}' is not in the workflow's agent list.")

        return results


# Convenience function for external usage
def build_crew_for_workflow(workflow_name: str, inputs: Dict[str, Any] = None, config_dir: Optional[str] = None) -> Crew:
    """
    Build a CrewAI crew for a specific workflow.
    
    Args:
        workflow_name: The name of the workflow.
        inputs: Input data for the workflow tasks.
        config_dir: The directory containing configuration files
            (defaults to crewai_service/evaluation/config).
        
    Returns:
        An instance of a CrewAI Crew.
    """
    builder = CrewBuilder(config_dir=config_dir)
    return builder.build_crew(workflow_name, inputs=inputs)

def kickoff_and_get_results(crew: Crew, inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Kick off the crew and return a structured dictionary of results,
    including raw output and any structured data.
    """
    logger.info("Kicking off crew execution...")
    result = crew.kickoff(inputs=inputs)
    
    task_outputs = []
    for task in crew.tasks:
        task_output_data = {
            "task_description": task.description,
            "agent_role": task.agent.role if task.agent else "N/A",
            "result": None
        }
        if task.output:
            # The final result is now encapsulated in a more complex object.
            # We access the raw string output via .raw
            raw_output = task.output.raw if hasattr(task.output, 'raw') else str(task.output)
            task_output_data["result"] = raw_output
        task_outputs.append(task_output_data)

    return {
        "final_result": result,
        "task_outputs": task_outputs
    } 