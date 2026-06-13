#!/bin/bash
# Start backend API and frontend services together

set -e

echo "🚀 Starting H.I.V.E. Mind services..."

# Get the project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Activate Python environment if needed
if [ -f "$PROJECT_ROOT/.venv/bin/activate" ]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
fi

# Backend port
BACKEND_PORT=${BACKEND_PORT:-8000}
BACKEND_URL="http://localhost:$BACKEND_PORT"

# Frontend port
FRONTEND_PORT=${FRONTEND_PORT:-8501}
FRONTEND_URL="http://localhost:$FRONTEND_PORT"

# Trap to kill both processes on exit
cleanup() {
    echo "🛑 Shutting down services..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Start backend
echo "📡 Starting backend orchestrator API on $BACKEND_URL..."
cd "$PROJECT_ROOT/backend"
python -m api &
BACKEND_PID=$!

# Wait for backend to be ready
echo "⏳ Waiting for backend to be ready..."
for i in {1..30}; do
    if curl -s "http://localhost:$BACKEND_PORT/health" > /dev/null; then
        echo "✅ Backend is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Backend failed to start"
        exit 1
    fi
    sleep 1
done

# Start frontend
echo "🎨 Starting frontend on $FRONTEND_URL..."
cd "$PROJECT_ROOT/frontend"
BACKEND_URL="$BACKEND_URL" streamlit run src/main.py --server.port=$FRONTEND_PORT &
FRONTEND_PID=$!

echo ""
echo "✨ Services are running!"
echo "  Frontend:  $FRONTEND_URL"
echo "  Backend:   $BACKEND_URL"
echo ""
echo "Press Ctrl+C to stop both services"

# Wait for both processes
wait
