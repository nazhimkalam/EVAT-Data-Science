#!/bin/bash

##############################################################################
# ChargeBnB Startup Script - SIMPLE VERSION
# Start both frontend and backend with pyenv support
##############################################################################

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# Get project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${BOLD}${BLUE}Starting ChargeBnB...${NC}\n"

# Initialize pyenv if available
if command -v pyenv &> /dev/null; then
    eval "$(pyenv init - bash)" 2>/dev/null || true
    pyenv shell evat_env_py310 2>/dev/null || echo "⚠️  Could not set pyenv shell"
fi

# Function to cleanup on exit
cleanup() {
    echo -e "\n${BOLD}Stopping servers...${NC}"
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    echo -e "${GREEN}Done!${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start backend in background
echo -e "${BOLD}▶ Backend Server${NC}"
cd "$PROJECT_ROOT/backend"
python3 main.py > /tmp/backend.log 2>&1 &
BACKEND_PID=$!
echo -e "  PID: $BACKEND_PID"
echo -e "  Port: 8001"
echo -e "  Logs: tail -f /tmp/backend.log\n"

# Wait a bit for backend to start
sleep 3

# Start frontend in background
echo -e "${BOLD}▶ Frontend Server${NC}"
cd "$PROJECT_ROOT/frontend"
npm run dev > /tmp/frontend.log 2>&1 &
FRONTEND_PID=$!
echo -e "  PID: $FRONTEND_PID"
echo -e "  Port: 5173"
echo -e "  Logs: tail -f /tmp/frontend.log\n"

# Wait for frontend to start
sleep 3

echo -e "${GREEN}${BOLD}✓ Both servers started!${NC}\n"
echo -e "${BLUE}Frontend:${NC} http://localhost:5173"
echo -e "${BLUE}Backend:${NC}  http://localhost:8001"
echo -e "${BLUE}API Docs:${NC} http://localhost:8001/docs\n"

echo -e "Press ${BOLD}Ctrl+C${NC} to stop both servers\n"

# Wait for both processes
while true; do
    wait $BACKEND_PID $FRONTEND_PID 2>/dev/null
    break
done
