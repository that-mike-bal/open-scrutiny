#!/usr/bin/env python3
"""
MCP Server Startup Script for CrewAI TLD Evaluation Service

This script starts the MCP server that provides tools and resources
for managing TLD evaluations through Claude Code.
"""

import sys
import os
import asyncio
import logging
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import the MCP server
try:
    from crewai_service.mcp_server import main
except ImportError as e:
    print(f"Error importing MCP server: {e}")
    print("Make sure the crewai_service module is properly installed")
    sys.exit(1)

def setup_logging():
    """Setup logging configuration"""
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

if __name__ == "__main__":
    setup_logging()
    
    # Run the MCP server
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("MCP server stopped by user")
    except Exception as e:
        print(f"Error running MCP server: {e}")
        sys.exit(1)
