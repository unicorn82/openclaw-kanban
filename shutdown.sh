#!/bin/bash

echo "🛑 Shutting down OpenClaw Kanban system..."

# Function to kill processes by port
kill_port() {
  local port=$1
  local pid=$(lsof -t -i:$port)
  if [ -n "$pid" ]; then
    echo "Killing process on port $port (PID: $pid)..."
    kill -9 $pid
  else
    echo "No process found on port $port."
  fi
}

# 1. Kill Backend (Port 8000)
kill_port 8000

# 2. Kill Frontend (Port 5173 or 5174)
kill_port 5173
kill_port 5174

# 3. Kill MCP Server (Looking for the specific python file)
mcp_pid=$(pgrep -f "python3 mcp_server.py")
if [ -n "$mcp_pid" ]; then
  echo "Killing MCP Server (PID: $mcp_pid)..."
  kill -9 $mcp_pid
else
  echo "No MCP Server process found."
fi

# 4. Clean up any orphaned uvicorn or vite processes
pkill -f "uvicorn main:app"
pkill -f "vite"

echo "✅ Shutdown complete."
