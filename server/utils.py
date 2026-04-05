import os
import datetime
from pathlib import Path
from sqlalchemy.orm import Session
import models

def sync_task_memory(db: Session, task_id: int, workspace_root: str):
    """Syncs task data to a task_memory.md file in its workspace folder."""
    db_task = db.query(models.TaskModel).filter(models.TaskModel.id == task_id).first()
    if not db_task:
        return
        
    # Get column name
    col_name = "Unknown"
    col = db.query(models.ColumnModel).filter(models.ColumnModel.id == db_task.column_id).first()
    if col:
        col_name = col.name
        
    # Sanitize title for folder name
    safe_title = "".join([c for c in db_task.title if c.isalnum() or c in (' ', '-', '_')]).rstrip()
    folder_name = f"{db_task.id}_{safe_title}"
    folder_path = Path(workspace_root) / folder_name
    
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

    # Build the header/metadata
    steps_md = "\n".join([f"- [ ] {s}" for s in (db_task.steps or [])])
    workflow_ids = db_task.workflow_ids or []
    workflow_md = ""
    if workflow_ids:
        workflow_names = []
        for wid in workflow_ids:
            w_col = db.query(models.ColumnModel).filter(models.ColumnModel.id == wid).first()
            if w_col:
                workflow_names.append(w_col.name)
        workflow_md = ", ".join(workflow_names)

    md_content = f"""# Task #{db_task.id}: {db_task.title}

## Task Status
- **Current Column**: {col_name}
- **Assigned Agent**: {db_task.agent_id or "Unassigned"}
- **Created At**: {db_task.created_at}
- **Last Updated**: {db_task.updated_at}
- **Required Workflow**: {workflow_md or "Standard"}

## Description
{db_task.description or "No description provided."}

## Expected Result
{db_task.expected_result or "No expected result defined."}

## Proposed Steps
{steps_md or "No steps defined."}

## Agent Memory & Progress{existing_content if existing_content else '\n\n*Agents can append their notes and progress here...*\n'}
"""
    try:
        with open(memory_file, "w", encoding='utf-8') as f:
            f.write(md_content)
    except Exception as e:
        print(f"Error writing memory file: {e}")

def append_task_memory(db: Session, task_id: int, workspace_root: str, content: str):
    """Appends content to the task's memory file."""
    db_task = db.query(models.TaskModel).filter(models.TaskModel.id == task_id).first()
    if not db_task:
        return False
        
    safe_title = "".join([c for c in db_task.title if c.isalnum() or c in (' ', '-', '_')]).rstrip()
    folder_name = f"{db_task.id}_{safe_title}"
    folder_path = Path(workspace_root) / folder_name
    memory_file = folder_path / "task_memory.md"
    
    if not memory_file.exists():
        sync_task_memory(db, task_id, workspace_root)
        
    try:
        with open(memory_file, "a", encoding='utf-8') as f:
            f.write(f"\n\n### Update at {datetime.datetime.utcnow().isoformat()}\n{content}\n")
        return True
    except Exception as e:
        print(f"Error appending memory: {e}")
        return False
