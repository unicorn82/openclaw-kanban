# OpenClaw Kanban Board

A modern, high-performance Kanban system integrated with an MCP server for AI agent automation.

## Features
- **Modern UI**: React v18+ with Framer Motion animations and Glassmorphic aesthetics.
- **Drag & Drop**: Powered by `@dnd-kit/core` for smooth task management.
- **FastAPI Backend**: Robust Python server with SQLite for persistent storage.
- **Easy Initialization**: Uses `server/init.json` to automatically set up columns on the first run.
- **MCP Enabled**: Full support for Model Context Protocol, allowing any AI agent to manage your tasks.
- **Node.js v22 Ready**: Fully compatible with the latest environments.

## Directory Structure
- `server/`: Python FastAPI application & MCP server.
- `client/`: React/TypeScript frontend.

## Getting Started

### Prerequisites
- Python 3.10+
- Node.js v22+
- `pip` & `npm`

### 1. One-Step Installation
From the root directory, run:
```bash
npm run install-all
```

### 2. Unified Launch
Launch both the backend and frontend with a single command:
```bash
npm start
```
Alternatively, you can use the provided shell script:
```bash
./start.sh
```
The board will be available at [http://localhost:5173](http://localhost:5173).

**Run the MCP Server (Stdio):**
```bash
cd server
# If using FastMCP
python mcp_server.py
```

## MCP Configuration
To use this with an agent (like Claude or OpenClaw), add this to your `mcp_servers` configuration:

```json
{
  "mcpServers": {
    "kanban": {
      "command": "python3",
      "args": ["/Users/easonyin/Project/Adless/openclaw-kanban/server/mcp_server.py"],
      "env": {
        "PYTHONPATH": "/Users/easonyin/Project/Adless/openclaw-kanban"
      }
    }
  }
}
```

## Tools Provided to Agents
- `list_tasks`: Retrieves all columns and tasks.
- `add_task`: Adds a new task to a specific column.
- `move_task`: Moves a task between columns (e.g., from "To Do" to "In Progress").
- `update_task_details`: Updates the task title/description.
- `delete_task`: Removes a task from the board.
