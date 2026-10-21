#!/bin/bash

# CrewAI Service Startup Script
# Ensures proper directory and module resolution

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Navigate to the project root
cd "$SCRIPT_DIR"

echo "🚀 Starting CrewAI Service from: $(pwd)"
echo "📦 Using Python module: crewai_service.app"

# Credentials come from the environment / .env (see env.example)
if [ -f ".env" ]; then set -a; . ./.env; set +a; fi
echo "🔑 SUPABASE_URL set: ${SUPABASE_URL:+yes}"; echo "🔑 SUPABASE_SERVICE_KEY set: ${SUPABASE_SERVICE_KEY:+yes}"; echo "🔑 GEMINI_API_KEY set: ${GEMINI_API_KEY:+yes}"

# Start the service using the proper module path
python3 -m uvicorn crewai_service.app:app --reload --host 0.0.0.0 --port 8000