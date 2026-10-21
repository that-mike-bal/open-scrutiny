"""
REAL WORKFLOW TESTS - Testing the ACTUAL running code

This test file covers the exact code paths that execute when a TLD evaluation runs,
traced from the production "unit" evaluation that completed successfully.

ACTUAL FLOW TRACED:
1. POST /api/evaluations/auto-submit → auto_submit_evaluation()
2. auto_submit_evaluation() → asyncio.create_task(run_evaluation_with_timeout())
3. run_evaluation_with_timeout() → run_sequential_workflows()
4. run_sequential_workflows() → executes 3 workflows: technical_risk_assessment, legal_risk_assessment, policy_safeguard_review
5. Each workflow → build_crew_for_workflow() → crew.kickoff() → extract_task_results() → save_task_executions()
6. After all workflows → generate_automatic_report()
7. Update overall_status to 'COMPLETED'
"""

import pytest
from unittest.mock import patch, Mock, AsyncMock
import asyncio
import json
from datetime import datetime


def run(coro):
    """Run a coroutine to completion without requiring an asyncio pytest plugin."""
    return asyncio.run(coro)


class TestRealAPIEndpoint:
    """Test the actual API endpoint that handles TLD submissions"""
    
    @patch('crewai_service.app._add_string_to_json_file')  # keep the test off data/existing_tld_strings.json
    @patch('crewai_service.app.TldApplicationStore')
    @patch('crewai_service.app.asyncio.create_task')
    def test_auto_submit_evaluation_real_flow(self, mock_create_task, mock_store_class, _mock_json):
        """Test the ACTUAL auto_submit_evaluation endpoint that gets called"""
        
        # Import the real function
        from crewai_service.app import auto_submit_evaluation, AutoEvaluationRequest
        
        # Mock the TldApplicationStore
        mock_store = Mock()
        mock_store_class.return_value = mock_store
        
        # Mock database response for new TLD
        mock_store.supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(
            data=[]  # No existing TLD found
        )
        
        # Mock TLD creation
        mock_store.supabase.table.return_value.insert.return_value.execute.return_value = Mock(
            data=[{'id': 'test-uuid-123', 'tld_string': 'testreal', 'overall_status': 'PENDING'}]
        )
        
        # Mock the background task creation
        mock_task = Mock()
        mock_create_task.return_value = mock_task
        
        # Create test request
        request = AutoEvaluationRequest(
            tld_string="testreal",
            use_case="Technology",
            enable_auto_execution=True
        )
        
        # Execute the real endpoint
        result = run(auto_submit_evaluation(request))
        
        # Verify the real flow was triggered
        assert result["status"] == "RUNNING"
        assert result["evaluation_id"] == "test-uuid-123"
        assert result["tld_string"] == "testreal"
        
        # Verify background task was created
        mock_create_task.assert_called_once()
        
        # Verify TLD was created in database
        mock_store.supabase.table.assert_called()


class TestRealWorkflowExecution:
    """Test the actual workflow execution function that runs in production"""
    
    @patch('crewai_service.app.TldApplicationStore')
    @patch('crewai_service.app.build_crew_for_workflow')
    @patch('crewai_service.app.extract_task_results')
    @patch('crewai_service.app.save_task_executions')
    @patch('crewai_service.app.update_workflow_status')
    @patch('crewai_service.app.generate_automatic_report')
    def test_run_sequential_workflows_real_flow(self, mock_generate_report, mock_update_status, 
                                                      mock_save_tasks, mock_extract_results, 
                                                      mock_build_crew, mock_store_class):
        """Test the ACTUAL run_sequential_workflows function that executes the 3 workflows"""
        
        # Import the real function
        from crewai_service.app import run_sequential_workflows
        
        # Mock Supabase client (obtained via TldApplicationStore().supabase)
        mock_supabase = Mock()
        mock_store_class.return_value.supabase = mock_supabase
        
        # Mock the table method chain for database tests
        mock_supabase.table.return_value.select.return_value.limit.return_value.execute.return_value = Mock(
            data=[{'id': 'test'}]
        )
        # Post-run check that task executions were saved
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(
            data=[{'id': 'task-1'}, {'id': 'task-2'}]
        )
        
        # Mock successful crew building and execution for each workflow
        mock_crew = Mock()
        mock_crew.agents = [Mock(), Mock()]  # Mock list of agents for len() check
        mock_crew.tasks = [Mock(), Mock(), Mock(), Mock()]  # Mock list of tasks for len() check
        mock_crew.kickoff.return_value = "Workflow completed successfully with detailed analysis"
        mock_build_crew.return_value = mock_crew
        
        # Mock task result extraction (this simulates the 12 tasks that completed for "unit")
        mock_extract_results.return_value = [
            {
                'task_name': 'legal_gut_check',
                'agent_name': 'Legal Analysis Agent',
                'status': 'COMPLETED',
                'output': 'Legal analysis completed successfully',
                'started_at': '2024-01-01T00:00:00Z',
                'completed_at': '2024-01-01T00:05:00Z'
            },
            {
                'task_name': 'dns_stability_review', 
                'agent_name': 'DNS Analysis Agent',
                'status': 'COMPLETED',
                'output': 'DNS stability analysis complete',
                'started_at': '2024-01-01T00:05:00Z',
                'completed_at': '2024-01-01T00:10:00Z'
            }
        ]
        
        # Mock save_task_executions return
        mock_save_tasks.return_value = 2  # 2 tasks saved
        
        # Mock successful workflow status updates (awaited by the function)
        mock_update_status.side_effect = AsyncMock(return_value=None)
        
        # Mock successful report generation (awaited by the function)
        mock_generate_report.side_effect = AsyncMock(return_value=None)
        
        # Execute the real workflow function
        run(run_sequential_workflows("test-tld-id", "testreal", "Technology"))
        
        # Verify the 3 workflows were executed (this is what actually runs)
        expected_workflows = ["technical_risk_assessment", "legal_risk_assessment", "policy_safeguard_review"]
        assert mock_build_crew.call_count == len(expected_workflows)
        assert mock_crew.kickoff.call_count == len(expected_workflows)
        
        # Verify task results were extracted and saved for each workflow
        assert mock_extract_results.call_count == len(expected_workflows)
        assert mock_save_tasks.call_count == len(expected_workflows)
        
        # Verify workflow statuses were updated (called twice per workflow: RUNNING then COMPLETED)
        assert mock_update_status.call_count == len(expected_workflows) * 2
        
        # Verify automatic report generation was triggered
        mock_generate_report.assert_called_once()
        # Verify it was called with the right TLD and string
        call_args = mock_generate_report.call_args[0]
        assert call_args[0] == "test-tld-id"
        assert call_args[1] == "testreal"


class TestRealTaskPersistence:
    """Test the actual save_task_executions function that stores results"""
    
    @patch('crewai_service.app.uuid.uuid4')
    def test_save_task_executions_real_function(self, mock_uuid):
        """Test the ACTUAL save_task_executions function that saves to database"""
        
        # Import the real function
        from crewai_service.app import save_task_executions
        
        # Mock UUID generation
        mock_uuid.return_value = Mock()
        mock_uuid.return_value.__str__ = Mock(return_value='task-exec-uuid-123')
        
        # Mock Supabase client
        mock_supabase = Mock()
        mock_supabase.enabled = True
        
        # Mock task definitions fetch
        mock_supabase.table.return_value.select.return_value.execute.return_value = Mock(
            data=[
                {'id': 'task-def-1', 'task_name': 'legal_gut_check'},
                {'id': 'task-def-2', 'task_name': 'dns_stability_review'}
            ]
        )
        
        # Mock task execution insert (returns list of inserted records)
        mock_supabase.table.return_value.insert.return_value.execute.return_value = Mock(
            data=[
                {'id': 'task-exec-uuid-1'},
                {'id': 'task-exec-uuid-2'}
            ]
        )
        
        # Test task executions (like what comes from "unit" evaluation)
        task_executions = [
            {
                'task_name': 'legal_gut_check',
                'agent_name': 'Legal Analysis Agent', 
                'status': 'COMPLETED',
                'output': 'Legal analysis completed successfully',
                'started_at': '2024-01-01T00:00:00Z',
                'completed_at': '2024-01-01T00:05:00Z'
            },
            {
                'task_name': 'dns_stability_review',
                'agent_name': 'DNS Analysis Agent',
                'status': 'COMPLETED', 
                'output': 'DNS stability analysis complete',
                'started_at': '2024-01-01T00:05:00Z',
                'completed_at': '2024-01-01T00:10:00Z'
            }
        ]
        
        # Execute the real function
        result = save_task_executions(
            mock_supabase,
            "test-tld-id",
            "workflow-exec-id", 
            task_executions,
            "technical_risk_assessment",
            "testreal",
            "Technology"
        )
        
        # Verify task definitions were fetched
        mock_supabase.table.assert_any_call('task_definitions')
        
        # Verify task executions were inserted
        mock_supabase.table.assert_any_call('task_executions')
        
        # Should return number of tasks saved
        assert result == 2


class TestRealReportGeneration:
    """Test the actual automatic report generation that runs after workflows"""
    
    @patch('crewai_service.app.save_report_to_database', new_callable=AsyncMock)
    @patch('crewai_service.app.generate_report_content', new_callable=AsyncMock)
    def test_generate_automatic_report_real_function(self, mock_generate_content, mock_save_report):
        """Test the ACTUAL generate_automatic_report function that creates AI reports"""
        
        # Import the real function
        from crewai_service.app import generate_automatic_report
        
        # Mock Supabase client and task executions fetch
        mock_supabase = Mock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(
            data=[
                {
                    'task_name': 'legal_gut_check',
                    'output': 'Legal analysis completed successfully',
                    'status': 'COMPLETED'
                },
                {
                    'task_name': 'dns_stability_review', 
                    'output': 'DNS stability analysis complete',
                    'status': 'COMPLETED'
                }
            ]
        )
        
        # Mock report content generation
        mock_generate_content.return_value = "# Comprehensive TLD Risk Assessment\n\nRisk Level: HIGH\n\nDetailed analysis..."
        
        # Mock report save
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = Mock(
            data=[{'id': 'test-tld-id', 'generated_report': 'saved'}]
        )
        
        # Mock final status update
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = Mock(
            data=[{'id': 'test-tld-id', 'overall_status': 'COMPLETED'}]
        )
        
        # Execute the real function
        run(generate_automatic_report("test-tld-id", "testreal", mock_supabase))
        
        # Verify task executions were fetched
        mock_supabase.table.assert_any_call('task_executions')
        
        # Verify report content was generated
        mock_generate_content.assert_called_once()
        
        # Verify the report was handed to the unified save helper
        mock_save_report.assert_awaited_once()
        saved_tld, saved_report = mock_save_report.await_args[0][:2]
        assert saved_tld == "testreal"
        assert saved_report.startswith("# Comprehensive TLD Risk Assessment")


class TestRealCrewBuilder:
    """Test the actual crew building that happens for each workflow"""
    
    @patch('crewai_service.crew.CrewBuilder')
    def test_build_crew_for_workflow_real_function(self, mock_crew_builder_class):
        """Test the ACTUAL build_crew_for_workflow function used in production"""
        
        # Import the real function
        from crewai_service.crew import build_crew_for_workflow
        
        # Mock CrewBuilder instance
        mock_builder = Mock()
        mock_crew_builder_class.return_value = mock_builder
        
        # Mock crew building
        mock_crew = Mock()
        mock_builder.build_crew.return_value = mock_crew
        
        # Test inputs (like what gets passed for "unit" evaluation)
        inputs = {
            'tld_string': 'testreal',
            'use_case': 'Technology'
        }
        
        # Execute the real function (this is what gets called for each of the 3 workflows)
        result = build_crew_for_workflow('technical_risk_assessment', inputs)
        
        # Verify CrewBuilder was instantiated with correct config
        mock_crew_builder_class.assert_called_once()
        
        # Verify crew was built with correct parameters
        mock_builder.build_crew.assert_called_once_with('technical_risk_assessment', inputs=inputs)
        
        # Verify crew was returned
        assert result == mock_crew


class TestRealDatabaseUpdates:
    """Test the actual database status updates that happen during workflow execution"""
    
    @patch('crewai_service.app.get_supabase_client')
    def test_update_workflow_status_real_function(self, mock_get_supabase):
        """Test the ACTUAL update_workflow_status function that updates database"""
        
        # Import the real function
        from crewai_service.app import update_workflow_status
        
        # Mock Supabase client
        mock_supabase = Mock()
        mock_get_supabase.return_value = mock_supabase
        
        # Mock status update
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = Mock(
            data=[{'id': 'test-tld-id', 'status': 'COMPLETED'}]
        )
        
        # Execute the real function
        run(update_workflow_status(mock_supabase, "test-tld-id", "technical_risk_assessment", "COMPLETED"))
        
        # Verify status was updated
        mock_supabase.table.assert_called_with('workflow_executions')
        mock_supabase.table.return_value.update.assert_called_once()



    print("Traced from the successful 'unit' evaluation that completed")
