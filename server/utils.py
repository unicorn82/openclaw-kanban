import datetime
import os
import shutil
import json
from pathlib import Path
from sqlalchemy.orm import Session
import models

def get_task_folder_path(workspace_root: str, task_id: int, title: str) -> Path:
    """Generates the sanitized folder path for a task."""
    safe_title = "".join([c for c in title if c.isalnum() or c in (' ', '-', '_')]).rstrip()
    folder_name = f"{task_id}_{safe_title}"
    return Path(workspace_root) / folder_name

def delete_task_folder(workspace_root: str, task_id: int, title: str):
    """Deletes the task's workspace folder if it exists."""
    folder_path = get_task_folder_path(workspace_root, task_id, title)
    if folder_path.exists() and folder_path.is_dir():
        shutil.rmtree(folder_path)

def sync_task_memory(db: Session, task_id: int, workspace_root: str, config_path: str = None):
    """Syncs project data to a task_memory.md file in its workspace folder."""
    db_task = db.query(models.TaskModel).filter(models.TaskModel.id == task_id).first()
    if not db_task:
        return
        
    # Get column name
    col_name = "Unknown"
    col = db.query(models.ColumnModel).filter(models.ColumnModel.id == db_task.column_id).first()
    if col:
        col_name = col.name
        
    # Get sanitized folder path
    folder_path = get_task_folder_path(workspace_root, db_task.id, db_task.title)
    
    os.makedirs(folder_path, exist_ok=True)
    
    memory_file = folder_path / "task_memory.md"
    
    # Read existing content if any
    existing_content = ""
    if memory_file.exists():
        try:
            with open(memory_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if "## Agent Memory & Progress" in content:
                    parts = content.split("## Agent Memory & Progress")
                    if len(parts) > 1:
                        existing_content = parts[1]
        except Exception as e:
            print(f"Error reading existing memory: {e}")

    # Build the tasks section
    subtasks_md = "*No tasks defined.*"
    if db_task.subtasks:
        subtasks_list = []
        for idx, sub in enumerate(db_task.subtasks):
            status_box = f"[{sub.get('status', 'pending').upper()}]"
            agent_str = f" @{sub.get('agent_id')}" if sub.get('agent_id') else ""
            subtasks_list.append(
                f"### {status_box} Task {idx+1}: {sub.get('title', 'Untitled')}{agent_str}\n"
                f"- **Goal**: {sub.get('description', 'N/A')}\n"
                f"- **Instructions**: {sub.get('instruction', 'N/A')}\n"
                f"- **Success Criteria (DoD)**: {sub.get('definition_of_done', 'N/A')}\n"
                f"- **Transition (What's Next)**: {sub.get('whats_next', 'N/A')}\n"
            )
        subtasks_md = "\n".join(subtasks_list)

    workflow_ids = db_task.workflow_ids or []
    workflow_md = ""
    if workflow_ids:
        workflow_names = []
        for wid in workflow_ids:
            w_col = db.query(models.ColumnModel).filter(models.ColumnModel.id == wid).first()
            if w_col:
                workflow_names.append(w_col.name)
        workflow_md = ", ".join(workflow_names)

    default_placeholder = '\n\n*Agents can append their notes and progress here...*\n'
    memory_section = existing_content if existing_content else default_placeholder

    md_content = f"""# Project #{db_task.id}: {db_task.title}
    
## Project Status
- **Current Column**: {col_name}
- **Created At**: {db_task.created_at}
- **Last Updated**: {db_task.updated_at}
- **Required Workflow**: {workflow_md or "Standard"}

## Description
{db_task.description or "No description provided."}

## Expected Result
{db_task.expected_result or "No expected result defined."}

## Projects & Execution Plan
{subtasks_md}

## Agent Memory & Progress{memory_section}
"""
    try:
        with open(memory_file, "w", encoding='utf-8') as f:
            f.write(md_content)
            
        # Also save task.json for machine-readable access
        task_data = {
            "id": db_task.id,
            "title": db_task.title,
            "description": db_task.description,
            "expected_result": db_task.expected_result,
            "column_id": db_task.column_id,
            "subtasks": db_task.subtasks,
            "workflow_ids": db_task.workflow_ids,
            "created_at": db_task.created_at.isoformat() if db_task.created_at else None,
            "updated_at": db_task.updated_at.isoformat() if db_task.updated_at else None
        }
        with open(folder_path / "task.json", "w", encoding='utf-8') as f:
            json.dump(task_data, f, indent=2)
            
    except Exception as e:
        print(f"Error writing task files: {e}")

def append_task_memory(db: Session, task_id: int, workspace_root: str, content: str, config_path: str = None):
    """Appends content to the task's memory file."""
    db_task = db.query(models.TaskModel).filter(models.TaskModel.id == task_id).first()
    if not db_task:
        return False
        
    folder_path = get_task_folder_path(workspace_root, db_task.id, db_task.title)
    memory_file = folder_path / "task_memory.md"
    
    if not memory_file.exists():
        sync_task_memory(db, task_id, workspace_root, config_path)
        
    try:
        ts = datetime.datetime.utcnow().isoformat()
        update_str = f"\n\n### Update at {ts}\n{content}\n"
        
        with open(memory_file, "a", encoding='utf-8') as f:
            f.write(update_str)
            
        return True
    except Exception as e:
        print(f"Error appending memory: {e}")
        return False
