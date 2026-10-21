"""
CrewAI Model Configuration

Optimal model assignment for different agent types to balance quality and cost efficiency.
Designed for professional feasibility services requiring both high-quality analysis and economic viability.
"""

from crewai import LLM
from typing import Dict, Optional
import logging
import os

from crewai_service.utils.config import load_api_key

logger = logging.getLogger(__name__)

# Backward-compatible alias — some files import _load_api_key from here
_load_api_key = load_api_key

def get_model_for_agent(agent_type: str) -> LLM:
    """
    Get optimal model for specific agent type.
    
    GEMINI 2.5 FLASH ONLY Strategy (switched for reliability):
    - Gemini 2.5 Flash: All tasks (Pro was causing 503 Service Unavailable errors)
    - GPT-4o: Fallback when Gemini API keys not available
    
    Args:
        agent_type: The type/name of the agent
        
    Returns:
        Configured LLM instance with optimal model and temperature
    """
    
    # Load API keys
    gemini_key = _load_api_key("gemini")
    
    # Configure Gemini 2.5 models with fallback to GPT-4o
    # Gemini 2.5 Flash: Fast, cost-effective for most tasks (1M tokens/min, 8K output)
    # Gemini 2.5 Pro: Advanced reasoning for complex tasks (2M tokens/min, 8K output)
    gemini_flash_model = LLM(model="gemini/gemini-2.5-flash", api_key=gemini_key) if gemini_key else LLM(model="gpt-4o")
    gemini_pro_model = LLM(model="gemini/gemini-2.5-pro", api_key=gemini_key) if gemini_key else LLM(model="gpt-4o")
    
    model_mapping = {
        # POLICY SAFEGUARD TASKS - Gemini 2.5 Flash (switched from Pro for reliability)
        "gac_advisor": gemini_flash_model,  # Geographic names, safeguards, GAC risk analysis
        
        # VALIDATION TASKS - Gemini 2.5 Flash (switched from Pro for reliability)
        "evaluation_validator": gemini_flash_model,  # Data validation & fact-checking
        "risk_assessor": gemini_flash_model,  # Risk synthesis and final assessment
        
        # TECHNICAL ANALYSIS - Gemini 2.5 Flash (fast, efficient processing)
        "string_analyst": gemini_flash_model,
        "compliance_analyst": gemini_flash_model,
        "collision_analyst": gemini_flash_model,
        "icann_compliance_specialist": gemini_flash_model,
        "dns_stability_analyst": gemini_flash_model,
        "collision_detection_specialist": gemini_flash_model,
        "technical_risk_assessor": gemini_flash_model,
        
        # LEGAL & TRADEMARK ANALYSIS - Gemini 2.5 Flash (document analysis)
        "trademark_specialist": gemini_flash_model,
        "similarity_analyzer": gemini_flash_model,
        "legal_risk_analyst": gemini_flash_model,
        
        # REPORTING & SYNTHESIS - Gemini 2.5 Flash (text generation)
        "report_synthesizer": gemini_flash_model,
        "bulk_processor": gemini_flash_model,
        "portfolio_analyzer": gemini_flash_model,
        
        # Default fallback - Gemini 2.5 Flash
        "default": gemini_flash_model
    }
    
    selected_model = model_mapping.get(agent_type, model_mapping["default"])
    
    # Log the model assignment with clear indication of Gemini vs fallback
    model_name = selected_model.model
    if "gemini" in model_name.lower():
        logger.info(f"🤖 Assigned {model_name} to agent '{agent_type}'")
    else:
        logger.warning(f"🔄 Using GPT-4o fallback for agent '{agent_type}' (Gemini API key not available)")
    
    return selected_model

def get_model_costs() -> Dict[str, Dict[str, float]]:
    """
    Get estimated costs per 1M tokens for different models.
    
    Returns:
        Dictionary with model costs for input/output tokens
    """
    return {
        # Gemini 2.5 models (primary)
        "gemini/gemini-2.5-flash": {"input": 0.075, "output": 0.30},  # Cost-effective for most tasks
        "gemini/gemini-2.5-pro": {"input": 1.25, "output": 5.00},    # Higher cost for complex reasoning
        
        # Fallback models
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4.1": {"input": 2.50, "output": 10.00},
        "o3-mini": {"input": 3.00, "output": 12.00}  # Estimated
    }

def estimate_workflow_cost(workflow_name: str, token_estimate: int = 50000) -> Dict[str, float]:
    """
    Estimate cost for running a workflow with Gemini 2.5 models.
    
    Args:
        workflow_name: Name of the workflow
        token_estimate: Estimated total tokens for the workflow
        
    Returns:
        Cost breakdown by model type
    """
    costs = get_model_costs()
    
    # Workflow model distribution (Gemini 2.5 optimized)
    workflow_distributions = {
        "technical_risk_assessment": {
            "gemini/gemini-2.5-flash": 1.0   # 100% of tokens - all Flash for reliability
        },
        "legal_risk_assessment": {
            "gemini/gemini-2.5-flash": 1.0   # 100% of tokens - all Flash for reliability
        },
        "policy_safeguard_review": {
            "gemini/gemini-2.5-flash": 1.0   # 100% of tokens - switched from Pro for reliability
        },
        "comprehensive_evaluation": {
            "gemini/gemini-2.5-flash": 1.0   # 100% of tokens - all Flash for reliability
        },
        "bulk_processing": {
            "gemini/gemini-2.5-flash": 1.0   # 100% of tokens - all Flash for reliability
        }
    }
    
    distribution = workflow_distributions.get(workflow_name, workflow_distributions["comprehensive_evaluation"])
    
    total_cost = 0.0
    cost_breakdown = {}
    
    for model, percentage in distribution.items():
        model_tokens = int(token_estimate * percentage)
        # Assume 70% input, 30% output tokens
        input_tokens = int(model_tokens * 0.7)
        output_tokens = int(model_tokens * 0.3)
        
        model_cost = (
            (input_tokens / 1_000_000) * costs[model]["input"] +
            (output_tokens / 1_000_000) * costs[model]["output"]
        )
        
        cost_breakdown[model] = model_cost
        total_cost += model_cost
    
    cost_breakdown["total"] = total_cost
    return cost_breakdown

def get_model_recommendations() -> Dict[str, str]:
    """
    Get model recommendations for different use cases.
    
    Returns:
        Dictionary with use case recommendations
    """
    return {
        "single_feasibility": "Gemini 2.5 optimized - Flash for analysis + Pro for validation",
        "bulk_portfolio": "Cost-optimized - Gemini 2.5 Flash for volume + Pro for quality checks",
        "premium_analysis": "Full Gemini 2.5 stack - Pro for critical tasks + Flash for processing",
        "budget_conscious": "Gemini 2.5 Flash primary with selective Pro usage for complex reasoning",
        "policy_safeguards": "Gemini 2.5 Pro required for policy analysis and validation tasks"
    }

def get_model_by_name(model_name: str) -> LLM:
    """
    Get model instance by name for manager LLM configuration.
    
    Args:
        model_name: Name of the model to get
        
    Returns:
        Configured LLM instance
    """
    # Load API keys
    gemini_key = _load_api_key("gemini")
    
    model_configs = {
        # Gemini 2.5 models (primary)
        "gemini-2.5-flash": LLM(model="gemini/gemini-2.5-flash", api_key=gemini_key),
        "gemini-2.5-pro": LLM(model="gemini/gemini-2.5-pro", api_key=gemini_key),
        
        # Fallback models
        "claude-3-sonnet": LLM(model="claude-3-sonnet"),
        "gpt-4o": LLM(model="gpt-4o"),
        "gpt-4.1": LLM(model="gpt-4.1"),
        "o3-mini": LLM(model="o3-mini"),
        
        # Legacy support
        "gemini-2.0-flash-thinking-exp": LLM(
            model="gemini/gemini-2.0-flash-thinking-exp-01-21", 
            api_key=gemini_key
        )
    }
    
    if model_name in model_configs:
        logger.debug(f"Retrieved model configuration for '{model_name}'")
        return model_configs[model_name]
    else:
        logger.warning(f"Model '{model_name}' not found, using default Gemini 2.5 Flash")
        return LLM(model="gemini/gemini-2.5-flash", api_key=gemini_key) if gemini_key else LLM(model="gpt-4o")

def validate_model_availability() -> Dict[str, bool]:
    """
    Validate that all configured models are available.
    
    Returns:
        Dictionary showing model availability status
    """
    # Check if API keys are available
    gemini_key = _load_api_key("gemini")
    
    return {
        # Primary Gemini 2.5 models
        "gemini/gemini-2.5-flash": gemini_key is not None,
        "gemini/gemini-2.5-pro": gemini_key is not None,
        
        # Fallback models
        "gpt-4o": True,
        "gpt-4.1": True,
        "o3-mini": True,  # Available when you get API keys
        
        # Legacy support
        "gemini/gemini-2.0-flash-exp": gemini_key is not None
    } 