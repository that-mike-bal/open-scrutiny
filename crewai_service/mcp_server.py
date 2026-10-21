"""
MCP Server for CrewAI TLD Evaluation Service

This server provides MCP tools and resources for managing TLD evaluations,
binary compliance checks, and workflow management through Claude Code.
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Sequence
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import mcp.types as types
    from mcp.server import Server
    from mcp.server.models import InitializationOptions
    from mcp.server.stdio import stdio_server
except ImportError:
    print("MCP package not found. Please install it with: pip install mcp")
    sys.exit(1)

# Import project modules
try:
    from crewai_service.utils.config import Config
    from crewai_service.workflow_executor import ProgressiveWorkflowExecutor
    from crewai_service.rag_search_tool import RAGVectorSearchTool
    from supabase import create_client, Client
except ImportError as e:
    print(f"Error importing project modules: {e}")
    sys.exit(1)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize configuration
config = Config()

# Initialize Supabase client
supabase: Client = create_client(
    config.get_supabase_url(),
    config.get_supabase_key()
)

# Initialize workflow executor
workflow_executor = ProgressiveWorkflowExecutor()

# Create MCP server instance
server = Server("crewai-tld-evaluation")

@server.list_tools()
async def handle_list_tools() -> List[types.Tool]:
    """List available MCP tools"""
    return [
        types.Tool(
            name="submit_tld_evaluation",
            description="Submit a new TLD string for evaluation",
            inputSchema={
                "type": "object",
                "properties": {
                    "tld_string": {
                        "type": "string",
                        "description": "The TLD string to evaluate (without the dot)"
                    },
                    "use_case": {
                        "type": "string", 
                        "description": "The intended use case for the TLD",
                        "default": "General purpose"
                    },
                    "enable_auto_execution": {
                        "type": "boolean",
                        "description": "Whether to automatically start the evaluation workflow",
                        "default": True
                    }
                },
                "required": ["tld_string"]
            }
        ),
        types.Tool(
            name="get_evaluation_status",
            description="Get the status of a TLD evaluation",
            inputSchema={
                "type": "object",
                "properties": {
                    "tld_string": {
                        "type": "string",
                        "description": "The TLD string to check status for"
                    }
                },
                "required": ["tld_string"]
            }
        ),
        types.Tool(
            name="list_evaluations",
            description="List recent TLD evaluations with their status",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of evaluations to return",
                        "default": 10
                    },
                    "status_filter": {
                        "type": "string",
                        "description": "Filter by status (processing, completed, failed)",
                        "enum": ["processing", "completed", "failed"]
                    }
                }
            }
        ),
        types.Tool(
            name="check_binary_compliance",
            description="Check binary compliance for a TLD string",
            inputSchema={
                "type": "object",
                "properties": {
                    "tld_string": {
                        "type": "string",
                        "description": "The TLD string to check compliance for"
                    }
                },
                "required": ["tld_string"]
            }
        ),
        types.Tool(
            name="get_queue_status",
            description="Get the current workflow queue status",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="delete_evaluation",
            description="Delete a TLD evaluation and its associated data",
            inputSchema={
                "type": "object",
                "properties": {
                    "tld_string": {
                        "type": "string",
                        "description": "The TLD string evaluation to delete"
                    },
                    "confirm": {
                        "type": "boolean",
                        "description": "Confirmation that you want to delete the evaluation",
                        "default": False
                    }
                },
                "required": ["tld_string", "confirm"]
            }
        ),
        types.Tool(
            name="search_knowledge_base",
            description="Search the TLD knowledge base for relevant information",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for the knowledge base"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Handle tool calls"""
    
    try:
        if name == "submit_tld_evaluation":
            return await submit_tld_evaluation(arguments)
        elif name == "get_evaluation_status":
            return await get_evaluation_status(arguments)
        elif name == "list_evaluations":
            return await list_evaluations(arguments)
        elif name == "check_binary_compliance":
            return await check_binary_compliance(arguments)
        elif name == "get_queue_status":
            return await get_queue_status(arguments)
        elif name == "delete_evaluation":
            return await delete_evaluation(arguments)
        elif name == "search_knowledge_base":
            return await search_knowledge_base(arguments)
        else:
            return [types.TextContent(
                type="text",
                text=f"Unknown tool: {name}"
            )]
    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}")
        return [types.TextContent(
            type="text",
            text=f"Error executing tool {name}: {str(e)}"
        )]

async def submit_tld_evaluation(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Submit a new TLD evaluation"""
    tld_string = arguments["tld_string"]
    use_case = arguments.get("use_case", "General purpose")
    enable_auto_execution = arguments.get("enable_auto_execution", True)
    
    # Insert into database
    result = supabase.table('tld_strings').insert({
        'tld_string': tld_string,
        'use_case': use_case,
        'status': 'processing' if enable_auto_execution else 'pending',
        'created_at': 'now()'
    }).execute()
    
    if enable_auto_execution:
        # Initialize workflow phases for the TLD
        phases = workflow_executor.initialize_application_generation_phases(tld_string)
        logger.info(f"Initialized {len(phases)} workflow phases for {tld_string}")
    
    return [types.TextContent(
        type="text",
        text=f"✅ TLD evaluation submitted for '{tld_string}'\n"
             f"Use case: {use_case}\n"
             f"Auto-execution: {'Enabled' if enable_auto_execution else 'Disabled'}\n"
             f"Status: {'Processing' if enable_auto_execution else 'Pending'}"
    )]

async def get_evaluation_status(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Get evaluation status for a TLD"""
    tld_string = arguments["tld_string"]
    
    # Query database for TLD status
    result = supabase.table('tld_strings').select('*').eq('tld_string', tld_string).execute()
    
    if not result.data:
        return [types.TextContent(
            type="text",
            text=f"❌ No evaluation found for TLD '{tld_string}'"
        )]
    
    tld_data = result.data[0]
    
    # Get task executions
    task_result = supabase.table('task_executions').select('*').eq('tld_string_id', tld_data['id']).execute()
    
    status_text = f"📊 Evaluation Status for '{tld_string}'\n"
    status_text += f"Status: {tld_data.get('overall_status', tld_data.get('status', 'unknown'))}\n"
    status_text += f"Created: {tld_data.get('created_at', 'unknown')}\n"
    status_text += f"Use Case: {tld_data.get('use_case', 'N/A')}\n"
    
    if task_result.data:
        status_text += f"\nTask Executions ({len(task_result.data)}):\n"
        for task in task_result.data:
            status_text += f"- {task['task_name']}: {task.get('result_status', 'unknown')}\n"
    
    return [types.TextContent(type="text", text=status_text)]

async def list_evaluations(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """List recent TLD evaluations"""
    limit = arguments.get("limit", 10)
    status_filter = arguments.get("status_filter")
    
    query = supabase.table('tld_strings').select('*').order('created_at', desc=True).limit(limit)
    
    if status_filter:
        query = query.eq('overall_status', status_filter)
    
    result = query.execute()
    
    if not result.data:
        return [types.TextContent(
            type="text",
            text="📋 No evaluations found"
        )]
    
    text = f"📋 Recent TLD Evaluations (showing {len(result.data)}):\n\n"
    
    for tld in result.data:
        text += f"• {tld['tld_string']}\n"
        text += f"  Status: {tld.get('status', 'unknown')}\n"
        text += f"  Created: {tld.get('created_at', 'unknown')}\n"
        text += f"  Use Case: {tld.get('use_case', 'N/A')}\n\n"
    
    return [types.TextContent(type="text", text=text)]

async def check_binary_compliance(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Check binary compliance for a TLD"""
    tld_string = arguments["tld_string"]
    
    # This would integrate with your binary compliance checking logic
    # For now, return a placeholder response
    
    return [types.TextContent(
        type="text",
        text=f"🔍 Binary Compliance Check for '{tld_string}'\n"
             f"Status: Analysis in progress\n"
             f"Note: Binary compliance checking is being processed..."
    )]

async def get_queue_status(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Get workflow queue status"""
    
    # Query for running workflows
    running_result = supabase.table('workflow_executions').select('*').eq('status', 'running').execute()
    pending_result = supabase.table('tld_strings').select('*').or_(
        'overall_status.eq.PENDING,overall_status.eq.not_started'
    ).execute()
    processing_result = supabase.table('tld_strings').select('*').eq('overall_status', 'RUNNING').execute()
    
    text = "📊 Workflow Queue Status\n\n"
    text += f"🔄 Running workflows: {len(running_result.data)}\n"
    text += f"⏳ Pending evaluations: {len(pending_result.data)}\n" 
    text += f"🔄 Processing evaluations: {len(processing_result.data)}\n"
    
    if running_result.data:
        text += "\nRunning Workflows:\n"
        for workflow in running_result.data:
            text += f"- {workflow.get('workflow_name', 'Unknown')}: {workflow.get('tld_string', 'N/A')}\n"
    
    return [types.TextContent(type="text", text=text)]

async def delete_evaluation(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Delete a TLD evaluation"""
    tld_string = arguments["tld_string"]
    confirm = arguments.get("confirm", False)
    
    if not confirm:
        return [types.TextContent(
            type="text",
            text=f"⚠️ To delete evaluation for '{tld_string}', you must set confirm=true"
        )]
    
    # Delete from database
    result = supabase.table('tld_strings').delete().eq('tld_string', tld_string).execute()
    
    if result.data:
        return [types.TextContent(
            type="text",
            text=f"✅ Deleted evaluation for '{tld_string}'"
        )]
    else:
        return [types.TextContent(
            type="text",
            text=f"❌ No evaluation found for '{tld_string}' or deletion failed"
        )]

async def search_knowledge_base(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Search the knowledge base"""
    query = arguments["query"]
    limit = arguments.get("limit", 5)
    
    try:
        # Initialize RAG search tool
        rag_tool = RAGVectorSearchTool()
        # Use the tool's _run method since it's a BaseTool
        results = rag_tool._run(query=query, limit=limit)
        
        if not results:
            return [types.TextContent(
                type="text",
                text=f"🔍 No results found for query: '{query}'"
            )]
        
        text = f"🔍 Knowledge Base Search Results for: '{query}'\n\n"
        
        for i, result in enumerate(results, 1):
            text += f"{i}. {result.get('title', 'Untitled')}\n"
            text += f"   {result.get('content', 'No content')[:200]}...\n\n"
        
        return [types.TextContent(type="text", text=text)]
        
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"❌ Error searching knowledge base: {str(e)}"
        )]

@server.list_resources()
async def handle_list_resources() -> List[types.Resource]:
    """List available resources"""
    return [
        types.Resource(
            uri="tld://evaluations",
            name="TLD Evaluations",
            description="List of all TLD evaluations in the system",
            mimeType="application/json"
        ),
        types.Resource(
            uri="tld://queue-status", 
            name="Queue Status",
            description="Current workflow queue status",
            mimeType="application/json"
        ),
        types.Resource(
            uri="tld://binary-compliance",
            name="Binary Compliance Data",
            description="Binary compliance checking data and rules",
            mimeType="application/json"
        )
    ]

@server.read_resource()
async def handle_read_resource(uri: str) -> str:
    """Handle resource reading"""
    
    if uri == "tld://evaluations":
        result = supabase.table('tld_strings').select('*').order('created_at', desc=True).limit(50).execute()
        return json.dumps(result.data, indent=2)
    
    elif uri == "tld://queue-status":
        running_result = supabase.table('workflow_executions').select('*').eq('status', 'running').execute()
        pending_result = supabase.table('tld_strings').select('*').or_(
            'overall_status.eq.PENDING,overall_status.eq.not_started'
        ).execute()
        
        status = {
            "running_workflows": len(running_result.data),
            "pending_evaluations": len(pending_result.data),
            "running_details": running_result.data,
            "pending_details": pending_result.data
        }
        return json.dumps(status, indent=2)
    
    elif uri == "tld://binary-compliance":
        # Return binary compliance data
        compliance_data = {
            "description": "Binary compliance checking rules and data",
            "rules": [
                "Check for existing trademark conflicts",
                "Verify DNS compatibility", 
                "Analyze string similarity to existing TLDs",
                "Check for reserved strings"
            ],
            "status": "operational"
        }
        return json.dumps(compliance_data, indent=2)
    
    else:
        raise ValueError(f"Unknown resource: {uri}")

@server.list_prompts()
async def handle_list_prompts() -> List[types.Prompt]:
    """List available prompts"""
    return [
        types.Prompt(
            name="evaluate_tld",
            description="Comprehensive TLD evaluation prompt",
            arguments=[
                types.PromptArgument(
                    name="tld_string",
                    description="The TLD string to evaluate",
                    required=True
                ),
                types.PromptArgument(
                    name="use_case",
                    description="Intended use case for the TLD",
                    required=False
                )
            ]
        ),
        types.Prompt(
            name="analyze_queue",
            description="Analyze workflow queue performance",
            arguments=[]
        ),
        types.Prompt(
            name="compliance_check",
            description="Binary compliance assessment prompt",
            arguments=[
                types.PromptArgument(
                    name="tld_string",
                    description="The TLD string to check compliance for",
                    required=True
                )
            ]
        )
    ]

@server.get_prompt()
async def handle_get_prompt(name: str, arguments: Dict[str, str]) -> types.GetPromptResult:
    """Handle prompt requests"""
    
    if name == "evaluate_tld":
        tld_string = arguments.get("tld_string", "")
        use_case = arguments.get("use_case", "General purpose")
        
        prompt = f"""Please perform a comprehensive evaluation of the TLD string '{tld_string}' for the use case: {use_case}

Consider the following aspects:
1. Trademark and legal compliance
2. DNS technical compatibility  
3. String similarity to existing TLDs
4. Market viability and brand potential
5. Regulatory compliance requirements

Provide a detailed analysis with recommendations."""

        return types.GetPromptResult(
            description=f"Comprehensive evaluation prompt for TLD '{tld_string}'",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(type="text", text=prompt)
                )
            ]
        )
    
    elif name == "analyze_queue":
        prompt = """Please analyze the current workflow queue performance and provide insights on:

1. Queue processing efficiency
2. Bottlenecks or delays
3. Resource utilization
4. Recommendations for optimization

Use the queue status data to provide actionable insights."""

        return types.GetPromptResult(
            description="Workflow queue performance analysis prompt",
            messages=[
                types.PromptMessage(
                    role="user", 
                    content=types.TextContent(type="text", text=prompt)
                )
            ]
        )
    
    elif name == "compliance_check":
        tld_string = arguments.get("tld_string", "")
        
        prompt = f"""Please perform a binary compliance check for the TLD string '{tld_string}':

1. Check against existing trademark databases
2. Verify DNS technical requirements
3. Analyze similarity to existing TLDs
4. Check reserved string lists
5. Assess regulatory compliance

Provide a clear compliance status and any issues found."""

        return types.GetPromptResult(
            description=f"Binary compliance check prompt for TLD '{tld_string}'",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(type="text", text=prompt)
                )
            ]
        )
    
    else:
        raise ValueError(f"Unknown prompt: {name}")

async def main():
    """Main function to run the MCP server"""
    
    # Initialize the server
    logger.info("Starting CrewAI TLD Evaluation MCP Server...")
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="crewai-tld-evaluation",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=None,
                    experimental_capabilities=None,
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
