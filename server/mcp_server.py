import os
from dotenv import load_dotenv
from pathlib import Path
from fastmcp import FastMCP
from database import SessionLocal, get_db
from sqlalchemy.orm import Session
from typing import List, Optional
import models
import utils

# Load environment variables
load_dotenv()
WORKSPACE_ROOT = os.getenv("WORKSPACE_ROOT", "./workspace")
CONFIG_PATH = os.getenv("OPENCLAW_CONFIG_PATH")

# Create an MCP server
mcp = FastMCP("Kanban Server")

def get_db_instance():
    return SessionLocal()

@mcp.tool()
def add_project(title: str, description: Optional[str] = None, column_name: str = "Idea") -> str:
    """Adds a new project to the kanban board and creates an associated folder in the workspace."""
    db = get_db_instance()
    try:
        col = db.query(models.ColumnModel).filter(models.ColumnModel.name == column_name).first()
        if not col:
            # Create column if not exists
            col = models.ColumnModel(name=column_name, order=0)
            db.add(col)
            db.commit()
            db.refresh(col)
        
        # Determine highest order to put at bottom
        highest_order = db.query(models.TaskModel).filter(models.TaskModel.column_id == col.id).count() 
        
        task = models.TaskModel(
            title=title,
            description=description,
            column_id=col.id,
            order=highest_order
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        # Sync memory
        utils.sync_task_memory(db, task.id, WORKSPACE_ROOT, CONFIG_PATH)
        
        folder_name = f"{task.id}_{title.replace(' ', '_')}" # Fallback folder name
        return f"Project '{title}' (ID: {task.id}) added to column '{column_name}'. Workspace created."
    finally:
        db.close()

@mcp.tool()
def list_projects() -> str:
    """Lists all projects on the kanban board grouped by columns, including assigned agents."""
    db = get_db_instance()
    try:
        cols = db.query(models.ColumnModel).order_by(models.ColumnModel.order).all()
        if not cols:
            return "No columns/projects found."
        
        result = []
        for col in cols:
            tasks = db.query(models.TaskModel).filter(models.TaskModel.column_id == col.id).order_by(models.TaskModel.order).all()
            task_list = [f"  - [{t.id}] {t.title} (Agent: {getattr(t, 'agent_id', None) or 'Unassigned'}): {t.description or 'No desc'}" for t in tasks]
            result.append(f"Column: {col.name}")
            if task_list:
                result.extend(task_list)
            else:
                result.append("  (Empty)")
        
        return "\n".join(result)
    finally:
        db.close()

@mcp.tool()
def get_project_details(project_id: int) -> str:
    """Returns full details of a specific project including its workflow requirements and current status."""
    db = get_db_instance()
    try:
        task = db.query(models.TaskModel).filter(models.TaskModel.id == project_id).first()
        if not task:
            return f"Project ID {project_id} not found."
        
        col = db.query(models.ColumnModel).filter(models.ColumnModel.id == task.column_id).first()
        col_name = col.name if col else "Unknown"
        
        workflow_stages = []
        if task.workflow_ids:
            for wid in task.workflow_ids:
                wcol = db.query(models.ColumnModel).filter(models.ColumnModel.id == wid).first()
                if wcol:
                    workflow_stages.append(wcol.name)
        
        subtasks_str = "None"
        if task.subtasks:
            subtasks_list = []
            for idx, sub in enumerate(task.subtasks):
                status_box = f"[{sub.get('status', 'pending').upper()}]"
                subtasks_list.append(
                    f"  {idx+1}. {status_box} {sub.get('title', 'No title')}\n"
                    f"     - Goal: {sub.get('description', 'No description')}\n"
                    f"     - Instruction: {sub.get('instruction', 'N/A')}\n"
                    f"     - DoD: {sub.get('definition_of_done', 'N/A')}\n"
                    f"     - Next: {sub.get('whats_next', 'N/A')}"
                )
            subtasks_str = "\n" + "\n".join(subtasks_list)
        
        return (
            f"ID: {task.id}\n"
            f"Title: {task.title}\n"
            f"Description: {task.description or 'None'}\n"
            f"Current Column: {col_name}\n"
            f"Assigned Agent: {getattr(task, 'agent_id', None) or 'Unassigned'}\n"
            f"Workflow Stages: {', '.join(workflow_stages) if workflow_stages else 'Standard'}\n"
            f"Expected Result: {task.expected_result or 'Not specified'}\n"
            f"Tasks: {subtasks_str}"
        )
    finally:
        db.close()

@mcp.tool()
def move_project(project_id: int, target_column_name: str) -> str:
    """Moves a project to a different column by specifying the project ID and target column name."""
    db = get_db_instance()
    try:
        task = db.query(models.TaskModel).filter(models.TaskModel.id == project_id).first()
        if not task:
            return f"Project ID {project_id} not found."
            
        col = db.query(models.ColumnModel).filter(models.ColumnModel.name == target_column_name).first()
        if not col:
            return f"Column name '{target_column_name}' not found."
            
        task.column_id = col.id
        db.commit()
        # Sync memory on move
        utils.sync_task_memory(db, project_id, WORKSPACE_ROOT, CONFIG_PATH)
        return f"Project '{task.title}' moved to '{target_column_name}'."
    finally:
        db.close()

@mcp.tool()
def update_project_details(project_id: int, title: Optional[str] = None, description: Optional[str] = None) -> str:
    """Updates the title or description of an existing project."""
    db = get_db_instance()
    try:
        task = db.query(models.TaskModel).filter(models.TaskModel.id == project_id).first()
        if not task:
            return f"Project ID {project_id} not found."
        
        if title:
            task.title = title
        if description:
            task.description = description
            
        db.commit()
        # Sync memory on update
        utils.sync_task_memory(db, project_id, WORKSPACE_ROOT, CONFIG_PATH)
        return f"Project ID {project_id} updated."
    finally:
        db.close()

@mcp.tool()
def delete_project(project_id: int) -> str:
    """Deletes a project from the kanban board by ID."""
    db = get_db_instance()
    try:
        task = db.query(models.TaskModel).filter(models.TaskModel.id == project_id).first()
        if not task:
            return f"Project ID {project_id} not found."
        
        db.delete(task)
        db.commit()
        return f"Project '{task.title}' deleted."
    finally:
        db.close()

@mcp.tool()
def list_attachments(project_id: int) -> str:
    """Lists all files attached to a specific project."""
    db = get_db_instance()
    try:
        task = db.query(models.TaskModel).filter(models.TaskModel.id == project_id).first()
        if not task:
            return f"Project ID {project_id} not found."
            
        safe_title = "".join([c for c in task.title if c.isalnum() or c in (' ', '-', '_')]).rstrip()
        folder_name = f"{task.id}_{safe_title}"
        folder_path = Path(WORKSPACE_ROOT) / folder_name
        
        if not os.path.exists(folder_path):
            return "No attachments found (workspace folder missing)."
            
        files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
        if not files:
            return "No attachments found in workspace folder."
            
        return "Attachments:\n" + "\n".join([f"- {f}" for f in files])
    finally:
        db.close()

@mcp.tool()
def read_attachment(project_id: int, filename: str) -> str:
    """Reads the content of a specific attachment file for a project."""
    db = get_db_instance()
    try:
        task = db.query(models.TaskModel).filter(models.TaskModel.id == project_id).first()
        if not task:
            return f"Project ID {project_id} not found."
            
        safe_title = "".join([c for c in task.title if c.isalnum() or c in (' ', '-', '_')]).rstrip()
        folder_name = f"{task.id}_{safe_title}"
        folder_path = Path(WORKSPACE_ROOT) / folder_name
        file_path = folder_path / filename
        
        if not os.path.exists(file_path):
            return f"File '{filename}' not found for project {project_id}."
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            return f"File '{filename}' is a binary file or not UTF-8 encoded. Cannot read text content."
        except Exception as e:
            return f"Error reading file: {str(e)}"
    finally:
        db.close()

@mcp.tool()
def append_project_memory(project_id: int, content: str) -> str:
    """Appends notes or progress updates to the project's memory file."""
    db = get_db_instance()
    try:
        success = utils.append_task_memory(db, project_id, WORKSPACE_ROOT, content, CONFIG_PATH)
        if success:
            return f"Memory appended to project ID {project_id}."
        else:
            return f"Could not append memory for project ID {project_id} (not found or error)."
    finally:
        db.close()

@mcp.tool()
def close_task(project_id: int, task_index: int) -> str:
    """Closes a specific task by its 1-based index and automatically opens the next pending task."""
    db = get_db_instance()
    try:
        task = db.query(models.TaskModel).filter(models.TaskModel.id == project_id).first()
        if not task:
            return f"Project ID {project_id} not found."
            
        if not task.subtasks or task_index < 1 or task_index > len(task.subtasks):
            return f"Task index {task_index} out of range for project {project_id}."
            
        updated_subs = []
        for idx, sub in enumerate(task.subtasks):
            actual_idx = idx + 1
            if actual_idx == task_index:
                if sub.get('review_required'):
                    return f"Error: Task {task_index} requires manager review and cannot be closed directly via MCP. Stop and wait for manager approval."
                sub['status'] = 'closed'
            elif actual_idx == task_index + 1 and sub.get('status') == 'pending':
                sub['status'] = 'open'
            updated_subs.append(sub)
            
        task.subtasks = updated_subs
        db.commit()
        utils.sync_task_memory(db, project_id, WORKSPACE_ROOT, CONFIG_PATH)
        
        msg = f"Task {task_index} ('{task.subtasks[task_index-1].get('title')}') closed."
        if task_index < len(task.subtasks):
            msg += f" Task {task_index + 1} ('{task.subtasks[task_index].get('title')}') is now 'open'."
        return msg
    finally:
        db.close()

if __name__ == "__main__":
    mcp.run()
