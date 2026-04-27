# OpenClaw Kanban Board

A modern, high-performance Kanban system integrated with an MCP server for AI agent automation.


## Directory Structure
- `server/`: Python FastAPI application & MCP server.
- `client/`: React/TypeScript frontend.
- `skills/openclaw-kanban-agent/`: Project-specific agent protocol (SKILL.md) and environment.

## Getting Started

### Prerequisites
- Python 3.10+
- Node.js v22+
- `pip` & `npm`

#### a. Install Dependencies
From the root directory, run:
```bash
npm run install-all
```

#### b. Setup Environment Variables
Copy the sample environment file and configure your local paths:
```bash
cp server/.env.sample server/.env
# Edit server/.env with your absolute paths
```

### 2. Unified Launch
Launch the backend, frontend, and MCP server with a single command:
```bash
./start.sh
```
The board will be available at [http://localhost:5173](http://localhost:5173) (or the network IP shown in the logs).

To stop all services:
```bash
./shutdown.sh
```

## MCP Configuration (For Agents)

To give an AI agent (like Claude or OpenClaw) control over the board, add the following to your `openclaw.json` or MCP configuration. **Note: Use absolute paths.**

```json
"mcp": {
  "servers": {
    "kanban": {
      "command": "python3",
      "args": [
        "/absolute/path/to/server/mcp_server.py"
      ],
      "env": {
        "PYTHONPATH": "/absolute/path/to/server",
        "DATABASE_URL": "sqlite://///absolute/path/to/server/kanban.db",
        "WORKSPACE_ROOT": "/absolute/path/to/workspace",
        "OPENCLAW_CONFIG_PATH": "/absolute/path/to/openclaw.json"
      }
    }
  }
}
```

## Unified Terminology
The system uses a **Project > Task** hierarchy:
- **Project**: A high-level goal (e.g., "Build Auth System").
- **Task**: An individual step within a project (e.g., "Setup JWT").

## Agent Protocol
Agents assigned to projects MUST follow the protocol defined in `skills/openclaw-kanban-agent/SKILL.md`. This protocol enforces high-agency behavior, mandatory memory synchronization, and clear stage transitions.
