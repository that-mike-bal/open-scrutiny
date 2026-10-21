"""
Progressive Application Generation Workflow Executor
====================================================

Executes the ICANN application generation workflow progressively through defined phases
with proper tracking, validation, and integration of specialist agent responses.
"""

import logging
import asyncio
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class WorkflowPhase:
    """Represents a phase in the application generation workflow"""
    name: str
    agent: str
    task: str
    dependencies: List[str]
    estimated_questions: int
    expected_output_file: str
    status: str = "pending"  # pending, running, completed, failed
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

class ProgressiveWorkflowExecutor:
    """
    Executes application generation workflows with progressive phase tracking
    """
    
    def __init__(self):
        self.phases: List[WorkflowPhase] = []
        self.context_data: Dict[str, Any] = {}
        self.execution_id: Optional[str] = None
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.overall_status: str = "not_started"
        
    def initialize_application_generation_phases(self, tld_string: str) -> List[WorkflowPhase]:
        """Initialize the phases for ICANN application generation"""
        
        phases = [
            WorkflowPhase(
                name="Organization Information Generation",
                agent="organization_info_agent", 
                task="generate_organization_information",
                dependencies=[],
                estimated_questions=118,  # Q7-125 range
                expected_output_file=f"outputs/organization_responses_{tld_string}.md"
            ),
            WorkflowPhase(
                name="Technical Capability Generation",
                agent="technical_capability_agent",
                task="generate_technical_capability", 
                dependencies=["generate_organization_information"],
                estimated_questions=37,  # Q18-55 range
                expected_output_file=f"outputs/technical_capability_{tld_string}.md"
            ),
            WorkflowPhase(
                name="Financial Capability Generation",
                agent="financial_capability_agent",
                task="generate_financial_capability",
                dependencies=["generate_technical_capability"],
                estimated_questions=85,  # Q126-210 range
                expected_output_file=f"outputs/financial_capability_{tld_string}.md"
            ),
            WorkflowPhase(
                name="Legal Compliance Generation",
                agent="legal_compliance_agent",
                task="generate_legal_compliance",
                dependencies=["generate_financial_capability"],
                estimated_questions=64,  # Q211-275 range
                expected_output_file=f"outputs/legal_compliance_{tld_string}.md"
            ),
            WorkflowPhase(
                name="Response Validation",
                agent="evaluation_validator",
                task="validate_application_responses",
                dependencies=["generate_legal_compliance"],
                estimated_questions=0,  # Validation phase
                expected_output_file=f"outputs/response_validation_{tld_string}.md"
            ),
            WorkflowPhase(
                name="Application Integration",
                agent="application_response_synthesizer",
                task="integrate_application_responses",
                dependencies=["validate_application_responses"],
                estimated_questions=0,  # Integration phase
                expected_output_file=f"outputs/integrated_application_{tld_string}.md"
            )
        ]
        
        return phases
    
    async def execute_workflow(self, workflow_name: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a workflow progressively with phase tracking
        
        Args:
            workflow_name: Name of the workflow to execute
            inputs: Input parameters including tld_string, applicant_id, etc.
        
        Returns:
            Dictionary containing execution results and status
        """
        
        if workflow_name != "application_generation":
            return {
                "status": "failed",
                "error": f"Unknown workflow: {workflow_name}",
                "execution_time": 0
            }
        
        # Initialize execution
        self.execution_id = f"app_gen_{inputs['tld_string']}_{int(time.time())}"
        self.start_time = datetime.utcnow()
        self.overall_status = "running"
        self.context_data = inputs.copy()
        
        tld_string = inputs["tld_string"]
        logger.info(f"🚀 Starting progressive application generation for .{tld_string} (ID: {self.execution_id})")
        
        # Initialize phases
        self.phases = self.initialize_application_generation_phases(tld_string)
        
        try:
            # Execute phases progressively
            completed_phases = 0
            total_questions_answered = 0
            
            for phase in self.phases:
                logger.info(f"🔄 Starting phase: {phase.name}")
                phase.status = "running"
                phase.start_time = datetime.utcnow()
                
                try:
                    # Execute the phase (simulated for now)
                    phase_result = await self._execute_phase(phase, tld_string)
                    
                    phase.status = "completed"
                    phase.end_time = datetime.utcnow()
                    phase.output_data = phase_result
                    
                    completed_phases += 1
                    total_questions_answered += phase.estimated_questions
                    
                    logger.info(f"✅ Completed phase: {phase.name} ({phase.estimated_questions} questions)")
                    
                    # Update context for next phases
                    self.context_data[f"{phase.task}_completed"] = True
                    self.context_data[f"{phase.task}_output"] = phase_result
                    
                except Exception as phase_error:
                    logger.error(f"❌ Phase {phase.name} failed: {phase_error}")
                    phase.status = "failed"
                    phase.end_time = datetime.utcnow()
                    phase.error_message = str(phase_error)
                    break
            
            # Determine overall status
            if completed_phases == len(self.phases):
                self.overall_status = "completed"
                logger.info(f"🎉 Application generation completed for .{tld_string}")
            else:
                self.overall_status = "failed"
                logger.error(f"💥 Application generation failed for .{tld_string}")
            
            self.end_time = datetime.utcnow()
            execution_time = (self.end_time - self.start_time).total_seconds()
            
            # Generate execution results
            results = {
                "status": self.overall_status,
                "execution_id": self.execution_id,
                "phases_completed": completed_phases,
                "total_phases": len(self.phases),
                "questions_answered": total_questions_answered,
                "estimated_questions": sum(p.estimated_questions for p in self.phases),
                "execution_time": execution_time,
                "output_files": [p.expected_output_file for p in self.phases if p.status == "completed"],
                "quality_score": self._calculate_quality_score(),
                "validation_status": self._get_validation_status(),
                "phase_details": self._get_phase_details()
            }
            
            # Add phase completion flags
            for phase in self.phases:
                phase_key = phase.task.replace("generate_", "").replace("_", "_") + "_completed"
                results[phase_key] = phase.status == "completed"
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Workflow execution failed: {e}")
            self.overall_status = "failed"
            self.end_time = datetime.utcnow()
            
            return {
                "status": "failed",
                "error": str(e),
                "execution_id": self.execution_id,
                "phases_completed": 0,
                "execution_time": (self.end_time - self.start_time).total_seconds() if self.start_time else 0
            }
    
    async def _execute_phase(self, phase: WorkflowPhase, tld_string: str) -> Dict[str, Any]:
        """
        Execute a single phase (simulated for now - would integrate with actual CrewAI)
        """
        
        # Simulate phase execution time based on complexity
        execution_times = {
            "generate_organization_information": 3,
            "generate_technical_capability": 5,
            "generate_financial_capability": 7,
            "generate_legal_compliance": 6,
            "validate_application_responses": 2,
            "integrate_application_responses": 3
        }
        
        await asyncio.sleep(execution_times.get(phase.task, 2))
        
        # Simulate successful phase completion with mock results
        phase_results = {
            "phase_name": phase.name,
            "questions_processed": phase.estimated_questions,
            "responses_generated": phase.estimated_questions,
            "completion_percentage": 95.0 if phase.estimated_questions > 0 else 100.0,
            "quality_indicators": {
                "completeness": "high",
                "compliance": "validated", 
                "professional_quality": "excellent"
            },
            "output_file": phase.expected_output_file,
            "generated_at": datetime.utcnow().isoformat(),
            "agent": phase.agent,
            "simulation_note": "This is simulated output - actual CrewAI integration would generate real responses"
        }
        
        # Create mock output directory and file
        output_path = Path(phase.expected_output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write mock output file
        with open(output_path, 'w') as f:
            f.write(f"# {phase.name}: .{tld_string}\n\n")
            f.write(f"Generated by {phase.agent}\n")
            f.write(f"Questions processed: {phase.estimated_questions}\n")
            f.write(f"Generated at: {datetime.utcnow().isoformat()}\n\n")
            f.write("## Mock Generated Content\n\n")
            f.write("This is simulated content for testing purposes.\n")
            f.write("In production, this would contain actual ICANN application responses.\n")
        
        return phase_results
    
    def _calculate_quality_score(self) -> float:
        """Calculate overall quality score based on phase completions"""
        if not self.phases:
            return 0.0
        
        completed_phases = sum(1 for p in self.phases if p.status == "completed")
        base_score = (completed_phases / len(self.phases)) * 5.0
        
        # Bonus for validation phase completion
        validation_phase = next((p for p in self.phases if "validation" in p.task), None)
        if validation_phase and validation_phase.status == "completed":
            base_score += 0.5
        
        return min(base_score, 5.0)
    
    def _get_validation_status(self) -> str:
        """Get validation status from validation phase"""
        validation_phase = next((p for p in self.phases if "validation" in p.task), None)
        
        if not validation_phase:
            return "not_applicable"
        elif validation_phase.status == "completed":
            return "passed"
        elif validation_phase.status == "failed":
            return "failed"
        else:
            return "pending"
    
    def _get_phase_details(self) -> List[Dict[str, Any]]:
        """Get detailed information about each phase"""
        details = []
        
        for phase in self.phases:
            phase_detail = {
                "name": phase.name,
                "agent": phase.agent,
                "task": phase.task,
                "status": phase.status,
                "estimated_questions": phase.estimated_questions,
                "expected_output_file": phase.expected_output_file
            }
            
            if phase.start_time:
                phase_detail["start_time"] = phase.start_time.isoformat()
            if phase.end_time:
                phase_detail["end_time"] = phase.end_time.isoformat()
                if phase.start_time:
                    phase_detail["duration_seconds"] = (phase.end_time - phase.start_time).total_seconds()
            
            if phase.error_message:
                phase_detail["error_message"] = phase.error_message
            
            details.append(phase_detail)
        
        return details

# Global executor instance
_workflow_executor = ProgressiveWorkflowExecutor()

async def execute_workflow(workflow_name: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a workflow using the global executor instance
    
    Args:
        workflow_name: Name of the workflow to execute
        inputs: Input parameters for the workflow
    
    Returns:
        Dictionary containing execution results
    """
    return await _workflow_executor.execute_workflow(workflow_name, inputs)