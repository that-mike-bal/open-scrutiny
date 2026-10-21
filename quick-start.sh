#!/bin/bash

echo "🚀 OpenScrutiny Quick Start (backend + frontend)"
echo "=============================================="
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Kill any existing processes on our ports
echo "🧹 Cleaning up any existing processes..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || true  # Backend port
lsof -ti:5173 | xargs kill -9 2>/dev/null || true  # Frontend port (Vite default)
lsof -ti:3000 | xargs kill -9 2>/dev/null || true  # Frontend fallback port
sleep 2

echo "✅ Ports cleaned"
echo ""

# Check dependencies
echo "🔍 Checking dependencies..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found"
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found"
    exit 1
fi

echo "✅ Python: $(python3 --version)"
echo "✅ Node.js: $(node --version)"
echo ""

# Install Python deps if needed
if ! python3 -c "import crewai" &> /dev/null; then
    echo "📦 Installing Python dependencies..."
    pip install -r requirements.txt
fi

# Install Node deps if needed in client directory
if [ ! -d "client/node_modules" ]; then
    echo "📦 Installing Node.js dependencies..."
    cd client
    npm install
    cd ..
fi

echo "✅ Dependencies ready"
echo ""

# Credentials come from the environment / .env (see env.example)
if [ -f ".env" ]; then set -a; . ./.env; set +a; fi
if [ -z "$SUPABASE_URL" ] || [ -z "$GEMINI_API_KEY" ]; then
    echo "⚠️  SUPABASE_URL / GEMINI_API_KEY not set — copy env.example to .env and fill it in"
fi

# Start CrewAI service
echo "🐍 Starting CrewAI service on port 8000..."
python3 -m uvicorn crewai_service.app:app --host 0.0.0.0 --port 8000 --reload > crewai.log 2>&1 &
CREWAI_PID=$!
echo "   PID: $CREWAI_PID"

# Wait for CrewAI service
echo "⏳ Waiting for CrewAI service..."
for i in {1..20}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ CrewAI service ready!"
        break
    fi
    if [ $i -eq 20 ]; then
        echo "❌ CrewAI service failed to start"
        echo "📋 Check crewai.log for errors"
        kill $CREWAI_PID 2>/dev/null
        exit 1
    fi
    echo "   Attempt $i/20..."
    sleep 3
done

echo ""

# Start Frontend (React with Vite)
echo "🌐 Starting Frontend on port 5173..."
cd client
export VITE_CREWAI_ENDPOINT=http://localhost:8000
npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..
echo "   PID: $FRONTEND_PID"

# Wait for Frontend
echo "⏳ Waiting for Frontend interface..."
for i in {1..20}; do
    if curl -s http://localhost:5173 > /dev/null 2>&1; then
        echo "✅ Frontend interface ready!"
        break
    fi
    if [ $i -eq 20 ]; then
        echo "❌ Frontend interface failed to start"
        echo "📋 Check frontend.log for errors"
        kill $CREWAI_PID $FRONTEND_PID 2>/dev/null
        exit 1
    fi
    echo "   Attempt $i/20..."
    sleep 3
done

echo ""
echo "🎉 SUCCESS! Both services are running:"
echo ""
echo "   🔗 Frontend Interface: http://localhost:5173"
echo "   🔗 CrewAI API: http://localhost:8000"  
echo "   🔗 API Health Check: http://localhost:8000/health"
echo "   🔗 API Documentation: http://localhost:8000/docs"
echo ""
echo "💡 Tips:"
echo "   • Open http://localhost:5173 in your browser"
echo "   • Try evaluating an item (in the bundled example, a TLD string like 'example')"
echo "   • Check logs: 'tail -f crewai.log' or 'tail -f frontend.log'"
echo "   • Use Ctrl+C to stop this script and all services"
echo ""

# Cleanup function
cleanup() {
    echo ""
    echo "🛑 Shutting down services..."
    kill $CREWAI_PID $FRONTEND_PID 2>/dev/null
    echo "✅ Services stopped"
    exit 0
}

# Set trap to cleanup on script exit
trap cleanup EXIT INT TERM

# Keep script running
echo "📡 Services running... Press Ctrl+C to stop"
while true; do
    sleep 10
    
    # Check if services are still running
    if ! kill -0 $CREWAI_PID 2>/dev/null; then
        echo "❌ CrewAI service stopped unexpectedly"
        break
    fi
    
    if ! kill -0 $FRONTEND_PID 2>/dev/null; then
        echo "❌ Frontend service stopped unexpectedly"  
        break
    fi
done

cleanup 