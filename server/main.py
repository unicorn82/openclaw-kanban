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

# Initialize default columns if missing
@app.on_event("startup")
def startup_db():
    db = database.SessionLocal()
    try:
        if db.query(models.ColumnModel).count() == 0:
            print("Empty database detected. Initializing columns...")
            init_path = os.path.join(os.path.dirname(__file__), "init.json")
            if os.path.exists(init_path):
                try:
                    with open(init_path, 'r') as f:
                        config = json.load(f)
                        for col_data in config.get("columns", []):
                            name = col_data if isinstance(col_data, str) else col_data.get("name")
                            order = 0 if isinstance(col_data, str) else col_data.get("order", 0)
                            agent = None if isinstance(col_data, str) else col_data.get("default_agent_id")
                            
                            # Use merge or check to be safe
                            existing = db.query(models.ColumnModel).filter(models.ColumnModel.name == name).first()
                            if not existing:
                                db.add(models.ColumnModel(name=name, order=order, default_agent_id=agent))
                    db.commit()
                except Exception as e:
                    print(f"Error loading init.json: {e}")
                    db.rollback()
                    # Fallback
                    default_cols = ["Idea", "Design", "Development", "QA", "Done"]
                    for idx, name in enumerate(default_cols):
                        if not db.query(models.ColumnModel).filter(models.ColumnModel.name == name).first():
                            db.add(models.ColumnModel(name=name, order=idx))
                    db.commit()
            else:
                default_cols = ["Idea", "Design", "Development", "QA", "Done"]
                for idx, name in enumerate(default_cols):
                    if not db.query(models.ColumnModel).filter(models.ColumnModel.name == name).first():
                        db.add(models.ColumnModel(name=name, order=idx))
                db.commit()
    except Exception as e:
        print(f"Database initialization error: {e}")
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
    
    # Apply default agent for the initial column
    col = db.query(models.ColumnModel).filter(models.ColumnModel.id == task.column_id).first()
    if col and col.default_agent_id:
        db_task.agent_id = col.default_agent_id

    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    # Create associated folder and sync memory
    utils.sync_task_memory(db, db_task.id, WORKSPACE_ROOT)
        
    return db_task

@app.put("/tasks/{task_id}", response_model=schemas.Task)
def update_task(task_id: int, task_update: schemas.TaskUpdate, db: Session = Depends(get_db)):
    db_task = db.query(models.TaskModel).filter(models.TaskModel.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    update_data = task_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_task, key, value)
    
    # If column was changed, update agent automatically based on column's default
    if "column_id" in update_data:
        col = db.query(models.ColumnModel).filter(models.ColumnModel.id == db_task.column_id).first()
        if col and col.default_agent_id:
            db_task.agent_id = col.default_agent_id
            
    db.commit()
    db.refresh(db_task)
    
    # Sync memory on update
    utils.sync_task_memory(db, db_task.id, WORKSPACE_ROOT)
    
    return db_task

@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    db_task = db.query(models.TaskModel).filter(models.TaskModel.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
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
    safe_title = "".join([c for c in db_task.title if c.isalnum() or c in (' ', '-', '_')]).rstrip()
    folder_name = f"{db_task.id}_{safe_title}"
    folder_path = Path(WORKSPACE_ROOT) / folder_name
    
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
        
    safe_title = "".join([c for c in db_task.title if c.isalnum() or c in (' ', '-', '_')]).rstrip()
    folder_name = f"{db_task.id}_{safe_title}"
    folder_path = Path(WORKSPACE_ROOT) / folder_name
    
    if not os.path.exists(folder_path):
        return []
    
    files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
    return files

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

@app.post("/tasks/{task_id}/append_memory")
def append_task_memory_endpoint(task_id: int, content: str, db: Session = Depends(get_db)):
    success = utils.append_task_memory(db, task_id, WORKSPACE_ROOT, content)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found or update failed")
    return {"detail": "Memory appended"}
