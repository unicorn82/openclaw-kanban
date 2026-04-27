#!/bin/bash

# Terminate all background processes on exit
trap 'kill 0' EXIT

echo "🚀 Starting OpenClaw Kanban Board..."

# 1. Start the Backend (FastAPI)
echo "📂 Starting Backend Server (Port 8000)..."
(cd server && python3 -m uvicorn main:app --reload --port 8000 --host 0.0.0.0) &

# 2. Start the Frontend (React + Vite)
echo "📂 Starting Frontend Client (Port 5173)..."
(cd client && npm run dev) &

# 3. Start the MCP Server
echo "📂 Starting MCP Server..."
(cd server && python3 mcp_server.py) &

# Wait for all background processes
wait
