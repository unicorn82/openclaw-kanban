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

# Create an MCP server
mcp = FastMCP("Kanban Server")

def get_db_instance():
    return SessionLocal()

@mcp.tool()
def add_task(title: str, description: Optional[str] = None, column_name: str = "Idea") -> str:
    """Adds a new task to the kanban board and creates an associated folder in the workspace."""
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
        utils.sync_task_memory(db, task.id, WORKSPACE_ROOT)
        
        return f"Task '{title}' (ID: {task.id}) added to column '{column_name}'. Workspace created at: {folder_name}"
    finally:
        db.close()

@mcp.tool()
def list_tasks() -> str:
    """Lists all tasks on the kanban board grouped by columns, including assigned agents."""
    db = get_db_instance()
    try:
        cols = db.query(models.ColumnModel).order_by(models.ColumnModel.order).all()
        if not cols:
            return "No columns/tasks found."
        
        result = []
        for col in cols:
            tasks = db.query(models.TaskModel).filter(models.TaskModel.column_id == col.id).order_by(models.TaskModel.order).all()
            task_list = [f"  - [{t.id}] {t.title} (Agent: {t.agent_id or 'Unassigned'}): {t.description or 'No desc'}" for t in tasks]
            result.append(f"Column: {col.name}")
            if task_list:
                result.extend(task_list)
            else:
                result.append("  (Empty)")
        
        return "\n".join(result)
    finally:
        db.close()

@mcp.tool()
def get_task_details(task_id: int) -> str:
    """Returns full details of a specific task including its workflow requirements and current status."""
    db = get_db_instance()
    try:
        task = db.query(models.TaskModel).filter(models.TaskModel.id == task_id).first()
        if not task:
            return f"Task ID {task_id} not found."
        
        col = db.query(models.ColumnModel).filter(models.ColumnModel.id == task.column_id).first()
        col_name = col.name if col else "Unknown"
        
        workflow_stages = []
        if task.workflow_ids:
            for wid in task.workflow_ids:
                wcol = db.query(models.ColumnModel).filter(models.ColumnModel.id == wid).first()
                if wcol:
                    workflow_stages.append(wcol.name)
        
        return (
            f"ID: {task.id}\n"
            f"Title: {task.title}\n"
            f"Description: {task.description or 'None'}\n"
            f"Current Column: {col_name}\n"
            f"Assigned Agent: {task.agent_id or 'Unassigned'}\n"
            f"Workflow Stages: {', '.join(workflow_stages) if workflow_stages else 'Standard'}\n"
            f"Expected Result: {task.expected_result or 'Not specified'}\n"
            f"Steps: {task.steps or []}"
        )
    finally:
        db.close()

@mcp.tool()
def move_task(task_id: int, target_column_name: str) -> str:
    """Moves a task to a different column by specifying the task ID and target column name."""
    db = get_db_instance()
    try:
        task = db.query(models.TaskModel).filter(models.TaskModel.id == task_id).first()
        if not task:
            return f"Task ID {task_id} not found."
            
        col = db.query(models.ColumnModel).filter(models.ColumnModel.name == target_column_name).first()
        if not col:
            return f"Column name '{target_column_name}' not found."
            
        task.column_id = col.id
        db.commit()
        # Sync memory on move
        utils.sync_task_memory(db, task_id, WORKSPACE_ROOT)
        return f"Task '{task.title}' moved to '{target_column_name}'."
    finally:
        db.close()

@mcp.tool()
def update_task_details(task_id: int, title: Optional[str] = None, description: Optional[str] = None) -> str:
    """Updates the title or description of an existing task."""
    db = get_db_instance()
    try:
        task = db.query(models.TaskModel).filter(models.TaskModel.id == task_id).first()
        if not task:
            return f"Task ID {task_id} not found."
        
        if title:
            task.title = title
        if description:
            task.description = description
            
        db.commit()
        # Sync memory on update
        utils.sync_task_memory(db, task_id, WORKSPACE_ROOT)
        return f"Task ID {task_id} updated."
    finally:
        db.close()

@mcp.tool()
def delete_task(task_id: int) -> str:
    """Deletes a task from the kanban board by ID."""
    db = get_db_instance()
    try:
        task = db.query(models.TaskModel).filter(models.TaskModel.id == task_id).first()
        if not task:
            return f"Task ID {task_id} not found."
        
        db.delete(task)
        db.commit()
        return f"Task '{task.title}' deleted."
    finally:
        db.close()

@mcp.tool()
def list_attachments(task_id: int) -> str:
    """Lists all files attached to a specific task."""
    db = get_db_instance()
    try:
        task = db.query(models.TaskModel).filter(models.TaskModel.id == task_id).first()
        if not task:
            return f"Task ID {task_id} not found."
            
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
def read_attachment(task_id: int, filename: str) -> str:
    """Reads the content of a specific attachment file for a task."""
    db = get_db_instance()
    try:
        task = db.query(models.TaskModel).filter(models.TaskModel.id == task_id).first()
        if not task:
            return f"Task ID {task_id} not found."
            
        safe_title = "".join([c for c in task.title if c.isalnum() or c in (' ', '-', '_')]).rstrip()
        folder_name = f"{task.id}_{safe_title}"
        folder_path = Path(WORKSPACE_ROOT) / folder_name
        file_path = folder_path / filename
        
        if not os.path.exists(file_path):
            return f"File '{filename}' not found for task {task_id}."
            
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
def append_task_memory(task_id: int, content: str) -> str:
    """Appends notes or progress updates to the task's memory file."""
    db = get_db_instance()
    try:
        success = utils.append_task_memory(db, task_id, WORKSPACE_ROOT, content)
        if success:
            return f"Memory appended to task ID {task_id}."
        else:
            return f"Could not append memory for task ID {task_id} (not found or error)."
    finally:
        db.close()

if __name__ == "__main__":
    mcp.run()
