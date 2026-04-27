---
name: openclaw-kanban-agent
description: Essential protocol for OpenClaw agents to manage projects, tasks, and state transitions within the Kanban board. Agents MUST use this skill as their primary operating procedure.
---

# OpenClaw Kanban Agent Protocol

This skill guides you through the standard operating procedure for acting as a high-agency agent within the OpenClaw Kanban environment.

## Environment Configuration (MANDATORY)
These values are the system's hardcoded infrastructure paths. Use these for all operations:
- **WORKSPACE_ROOT**: `/path/to/your/workspace`
- **KANBAN_API_BASE**: `http://localhost:5173`
- **DATABASE_URL**: `sqlite:////path/to/your/server/kanban.db`
- **MCP_SERVER_PATH**: `/path/to/your/server/mcp_server.py`
- **AGENT_ID**: `@main` (Note: Check local `.env` for overrides)

## Tooling & Connection Protocols
You must interact with the Kanban board using **Native MCP Tools**. You have total control over your session's toolset.

### 1. Verification & Connection (MANDATORY if tools missing)
If the native `list_projects()` tool is missing from your sidebar:
- **Action**: Use your internal platform management tools (e.g., listing MCP servers, inspecting session capabilities) to verify if the 'kanban' server is active.
- **Self-Correction**: If the server is not active or the tools are missing, use your system-level tools to initialize a connection to the server at `MCP_SERVER_PATH`. 
- **Configuration**: Ensure you pass the `DATABASE_URL` and `WORKSPACE_ROOT` as environment variables during connection to sync state correctly.
- **Reporting**: Do not report a "blocked" status until you have attempted to manually activate/attach the MCP tools at least once.

### 2. Core Kanban Tools
Once successfully connected, use these tools as your primary interface:
- **`list_projects()`**: Lists all projects and their current columns.
- **`get_project_details(id)`**: Detailed view of a project, including its task list.
- **`move_project(id, column)`**: Transitions a project to a new column.
- **`close_task(id, index)`**: Marks a task (1-based index) as CLOSED and opens the next one.
- **`append_project_memory(id, content)`**: Syncs a progress note to the project's memory.

## Standard Workflow

### 1. Identify Your Assigned Work
- **Action**: Call `list_projects()` to check the board state. Identify any project assigned to your `AGENT_ID`.
- **AUTO-START**: If you find an open task assigned to you, **PROCEED IMMEDIATELY**.

### 2. Read Context (Workspace Files)
- **Tool**: `view_file` on `WORKSPACE_ROOT/[ID]_[TITLE]/task_memory.md`.
- **Protocol**: You MUST ingest the historical progress, technical decisions, and design docs in this file before taking any action.

### 3. Plan & Execute Independently
- **Technical Excellence**: Formulate a technical plan and implement it.
- **Autonomy**: Solve technical blockers (coding errors, dependency issues) autonomously using your expertise.

### 4. Final Quality Review & Update
- **1. Update Memory**: Use `append_project_memory(id, content)` to document exactly what you did, your rationale, and handoff instructions.
- **2. Transition**: Use `close_task` and `move_project` to advance the project to its next stage.

## Prohibited Actions
- **NO DIRECT DATABASE ACCESS**: You are strictly prohibited from querying the SQLite database directly for board state.
- **NO WORKAROUNDS**: Do not use shell-based DB queries or browser/API tools to bypass the MCP tool requirement.
- **NO DELAYS**: Do not wait for user input for technical decisions you are qualified to make.
