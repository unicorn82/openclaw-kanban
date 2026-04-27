from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import os
import shutil
from dotenv import load_dotenv
from pathlib import Path
import models, schemas, database
from database import engine, get_db
import utils
import datetime

import json
# Load environment variables
load_dotenv()

WORKSPACE_ROOT = os.getenv("WORKSPACE_ROOT", "./workspace")
CONFIG_PATH = os.getenv("OPENCLAW_CONFIG_PATH")
os.makedirs(WORKSPACE_ROOT, exist_ok=True)

# Create the database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="OpenClaw Kanban API")

# Add CORS to allow React client to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development, allow everything
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize columns from openclaw.json
@app.on_event("startup")
def startup_db():
    db = database.SessionLocal()
    try:
        if not CONFIG_PATH or not os.path.exists(CONFIG_PATH):
            print(f"Warning: OPENCLAW_CONFIG_PATH ({CONFIG_PATH}) not found. Skipping agent sync.")
            # Fallback to default columns if db is empty
            if db.query(models.ColumnModel).count() == 0:
                default_cols = ["Idea", "Design", "Development", "QA", "Done"]
                for idx, name in enumerate(default_cols):
                    db.add(models.ColumnModel(name=name, order=idx))
                db.commit()
            return

        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)
            agents = config.get("agents", {}).get("list", [])
            
            # Map agents to desired column states
            agent_ids = []
            next_order = 0
            for agent_data in agents:
                agent_id = agent_data.get("id")
                agent_name = agent_data.get("name") or agent_id
                agent_ids.append(agent_id)
                
                db_col = db.query(models.ColumnModel).filter(models.ColumnModel.default_agent_id == agent_id).first()
                if not db_col:
                    print(f"Adding new column for agent: {agent_name}")
                    db_col = models.ColumnModel(
                        name=agent_name, 
                        default_agent_id=agent_id, 
                        order=next_order
                    )
                    db.add(db_col)
                else:
                    db_col.name = agent_name
                    db_col.order = next_order
                next_order += 1
            
            # Ensure "Done" column exists at the end
            done_col = db.query(models.ColumnModel).filter(models.ColumnModel.name == "Done").first()
            if not done_col:
                print("Adding archived 'Done' column")
                done_col = models.ColumnModel(name="Done", order=next_order)
                db.add(done_col)
            else:
                done_col.order = next_order
            
            # Identify columns to delete (not an agent column AND not "Done")
            all_cols = db.query(models.ColumnModel).all()
            for col in all_cols:
                is_agent_col = col.default_agent_id and col.default_agent_id in agent_ids
                is_done_col = col.name == "Done"
                
                if not is_agent_col and not is_done_col:
                    print(f"Removing unused column: {col.name}")
                    # Move any orphaned tasks to the "Done" column or first agent
                    target_move_col = done_col or db.query(models.ColumnModel).first()
                    if target_move_col and col.id != target_move_col.id:
                        tasks_to_move = db.query(models.TaskModel).filter(models.TaskModel.column_id == col.id).all()
                        for task in tasks_to_move:
                            task.column_id = target_move_col.id
                    db.delete(col)
            
            db.commit()
            print("Successfully synchronized columns (Agents + Done).")

    except Exception as e:
        print(f"Agent synchronization error: {e}")
        db.rollback()
    finally:
        db.close()

@app.get("/health/fix-columns")
def fix_columns(db: Session = Depends(get_db)):
    """API to force re-initialize columns if they are missing."""
    count = db.query(models.ColumnModel).count()
    if count == 0:
        startup_db()
        return {"status": "re-initialized", "count": db.query(models.ColumnModel).count()}
    return {"status": "ok", "count": count}

@app.get("/agents")
def get_agents():
    """Returns the list of available agents from openclaw.json."""
    if not CONFIG_PATH or not os.path.exists(CONFIG_PATH):
        return []
        
    try:
        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)
            agents = config.get("agents", {}).get("list", [])
            return agents
    except Exception as e:
        print(f"Error reading openclaw config: {e}")
        return []

@app.put("/columns/{column_id}", response_model=schemas.Column)
def update_column(column_id: int, column_update: schemas.ColumnUpdate, db: Session = Depends(get_db)):
    db_col = db.query(models.ColumnModel).filter(models.ColumnModel.id == column_id).first()
    if not db_col:
        raise HTTPException(status_code=404, detail="Column not found")
        
    update_data = column_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_col, key, value)
        
    db.commit()
    db.refresh(db_col)
    return db_col

# --- Columns ---
@app.get("/columns", response_model=List[schemas.Column])
def get_columns(db: Session = Depends(get_db)):
    return db.query(models.ColumnModel).order_by(models.ColumnModel.order).all()

@app.post("/columns", response_model=schemas.Column)
def create_column(column: schemas.ColumnCreate, db: Session = Depends(get_db)):
    db_col = models.ColumnModel(**column.dict())
    db.add(db_col)
    db.commit()
    db.refresh(db_col)
    return db_col

# --- Tasks ---
@app.get("/tasks", response_model=List[schemas.Task])
def get_tasks(db: Session = Depends(get_db)):
    return db.query(models.TaskModel).all()

@app.post("/tasks", response_model=schemas.Task)
def create_task(task: schemas.TaskCreate, db: Session = Depends(get_db)):
    db_task = models.TaskModel(**task.dict())
    
    # Initialize subtask statuses
    if db_task.subtasks:
        updated_subs = []
        for idx, sub in enumerate(db_task.subtasks):
            # Ensure sub is a dict if it happens to be a Pydantic model
            if hasattr(sub, "dict"):
                sub_dict = sub.dict()
            elif hasattr(sub, "model_dump"):
                sub_dict = sub.model_dump()
            else:
                sub_dict = dict(sub)
                
            sub_dict['status'] = 'open' if idx == 0 else 'pending'
            updated_subs.append(sub_dict)
        db_task.subtasks = updated_subs
        
        # Auto-move based on first open subtask
        if len(db_task.subtasks) > 0:
            open_sub = db_task.subtasks[0]
            agent_id = open_sub.get('agent_id')
            if agent_id:
                target_col = db.query(models.ColumnModel).filter(models.ColumnModel.default_agent_id == agent_id).first()
                if target_col:
                    db_task.column_id = target_col.id

    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    # Create associated folder and sync memory
    utils.sync_task_memory(db, db_task.id, WORKSPACE_ROOT, CONFIG_PATH)
        
    return db_task

@app.put("/tasks/{task_id}", response_model=schemas.Task)
def update_task(task_id: int, task_update: schemas.TaskUpdate, db: Session = Depends(get_db)):
    db_task = db.query(models.TaskModel).filter(models.TaskModel.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    update_data = task_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_task, key, value)
    
    # Auto-move and Enforce Single-Open Invariant
    if db_task.subtasks:
        # Standardize subtasks to dicts
        normalized_subs = []
        for s in db_task.subtasks:
            if hasattr(s, "model_dump"): normalized_subs.append(s.model_dump())
            elif hasattr(s, "dict"): normalized_subs.append(s.dict())
            else: normalized_subs.append(s if isinstance(s, dict) else dict(s))
        
        # Enforce: only one subtask can be "open"
        # We find the first "open" subtask and set all others to "pending" (if not "closed")
        found_open_idx = -1
        for i, s in enumerate(normalized_subs):
            if s.get('status') == 'open':
                if found_open_idx == -1:
                    found_open_idx = i
                else:
                    s['status'] = 'pending'
        
        db_task.subtasks = normalized_subs
        
        if found_open_idx != -1:
            open_sub = normalized_subs[found_open_idx]
            if open_sub.get('agent_id'):
                target_col = db.query(models.ColumnModel).filter(models.ColumnModel.default_agent_id == open_sub.get('agent_id')).first()
                if target_col:
                    db_task.column_id = target_col.id
        elif all(s.get('status') == 'closed' for s in normalized_subs):
            # All closed? Move to Done if exists
            done_col = db.query(models.ColumnModel).filter(models.ColumnModel.name == 'Done').first()
            if done_col:
                db_task.column_id = done_col.id
            
    db.commit()
    db.refresh(db_task)
    
    # Sync memory on update
    utils.sync_task_memory(db, db_task.id, WORKSPACE_ROOT, CONFIG_PATH)
    
    return db_task

@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    db_task = db.query(models.TaskModel).filter(models.TaskModel.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Delete workspace folder
    utils.delete_task_folder(WORKSPACE_ROOT, db_task.id, db_task.title)
    
    db.delete(db_task)
    db.commit()
    return {"detail": "Deleted"}

# --- Drag and Drop Batch Update ---
@app.post("/tasks/{task_id}/attachments")
async def upload_attachment(task_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    db_task = db.query(models.TaskModel).filter(models.TaskModel.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    # Get task folder
    folder_path = utils.get_task_folder_path(WORKSPACE_ROOT, db_task.id, db_task.title)
    
    # Ensure it exists (if somehow deleted)
    os.makedirs(folder_path, exist_ok=True)
    
    # Save file
    file_path = folder_path / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    return {"filename": file.filename, "path": str(file_path)}

@app.get("/tasks/{task_id}/attachments")
def list_attachments(task_id: int, db: Session = Depends(get_db)):
    db_task = db.query(models.TaskModel).filter(models.TaskModel.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    folder_path = utils.get_task_folder_path(WORKSPACE_ROOT, db_task.id, db_task.title)
    
    if not os.path.exists(folder_path):
        return []
    
    files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
    return files

@app.post("/tasks/{task_id}/subtasks/{subtask_index}/close", response_model=schemas.Task)
def close_subtask(task_id: int, subtask_index: int, db: Session = Depends(get_db)):
    db_task = db.query(models.TaskModel).filter(models.TaskModel.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if not db_task.subtasks or subtask_index < 0 or subtask_index >= len(db_task.subtasks):
        raise HTTPException(status_code=404, detail="Subtask index out of range")
        
    # Standardize and update subtasks with single-open invariant
    updated_subs = []
    next_to_open_idx = subtask_index + 1
    for idx, sub in enumerate(db_task.subtasks):
        if hasattr(sub, "model_dump"): s_dict = sub.model_dump()
        elif hasattr(sub, "dict"): s_dict = sub.dict()
        else: s_dict = dict(sub)
        
        if idx == subtask_index:
            s_dict['status'] = 'closed'
        elif idx == next_to_open_idx:
            s_dict['status'] = 'open'
        elif s_dict.get('status') == 'open':
            # Ensure no other subtask stays open
            s_dict['status'] = 'pending'
            
        updated_subs.append(s_dict)
        
    db_task.subtasks = updated_subs
    
    # Auto-move logic
    next_open = next((s for s in updated_subs if s.get('status') == 'open'), None)
    if next_open and next_open.get('agent_id'):
        target_col = db.query(models.ColumnModel).filter(models.ColumnModel.default_agent_id == next_open.get('agent_id')).first()
        if target_col:
            db_task.column_id = target_col.id
    elif all(s.get('status') == 'closed' for s in updated_subs):
        # All closed? Move to Done
        done_col = db.query(models.ColumnModel).filter(models.ColumnModel.name == 'Done').first()
        if done_col:
            db_task.column_id = done_col.id
            
    db.commit()
    db.refresh(db_task)
    utils.sync_task_memory(db, db_task.id, WORKSPACE_ROOT, CONFIG_PATH)
    return db_task

@app.post("/tasks/reorder")
def reorder_tasks(task_ids: List[int], column_id: int, db: Session = Depends(get_db)):
    col = db.query(models.ColumnModel).filter(models.ColumnModel.id == column_id).first()
    for idx, tid in enumerate(task_ids):
        db_task = db.query(models.TaskModel).filter(models.TaskModel.id == tid).first()
        if db_task:
            db_task.column_id = column_id
            db_task.order = idx
            # New: Auto assignee on reorder/move
            if col and col.default_agent_id:
                db_task.agent_id = col.default_agent_id
            # Sync memory for moved tasks
            utils.sync_task_memory(db, tid, WORKSPACE_ROOT)
    db.commit()
    return {"detail": "Reordered"}

@app.post("/tasks/{task_id}/subtasks/{subtask_index}/reopen", response_model=schemas.Task)
def reopen_subtask(task_id: int, subtask_index: int, db: Session = Depends(get_db)):
    db_task = db.query(models.TaskModel).filter(models.TaskModel.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if not db_task.subtasks or subtask_index < 0 or subtask_index >= len(db_task.subtasks):
        raise HTTPException(status_code=404, detail="Subtask index out of range")
        
    # Standardize and update subtasks with single-open invariant
    updated_subs = []
    for idx, sub in enumerate(db_task.subtasks):
        if hasattr(sub, "model_dump"): s_dict = sub.model_dump()
        elif hasattr(sub, "dict"): s_dict = sub.dict()
        else: s_dict = dict(sub)
            
        if idx == subtask_index:
            s_dict['status'] = 'open'
        elif s_dict.get('status') == 'open':
            # Move previously open subtasks to pending
            s_dict['status'] = 'pending'
            
        updated_subs.append(s_dict)
        
    db_task.subtasks = updated_subs
    
    # Auto-move based on newly opened subtask
    open_sub = updated_subs[subtask_index]
    if open_sub.get('agent_id'):
        target_col = db.query(models.ColumnModel).filter(models.ColumnModel.default_agent_id == open_sub.get('agent_id')).first()
        if target_col:
            db_task.column_id = target_col.id
            
    db.commit()
    db.refresh(db_task)
    
    # Sync memory/files
    utils.sync_task_memory(db, db_task.id, WORKSPACE_ROOT, CONFIG_PATH)
    
    return db_task

@app.post("/tasks/{task_id}/append_memory")
def append_task_memory_endpoint(task_id: int, content: str, db: Session = Depends(get_db)):
    success = utils.append_task_memory(db, task_id, WORKSPACE_ROOT, content)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found or update failed")
    return {"detail": "Memory appended"}
