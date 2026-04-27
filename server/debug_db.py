import models
from database import engine, SessionLocal
import os
import sys
import json
import datetime
import utils

# Ensure tables exist
models.Base.metadata.create_all(bind=engine)

WORKSPACE_ROOT = os.getenv("WORKSPACE_ROOT", "/Users/eyin/Repository/openclaw-kanban/workspace")

def get_db():
    return SessionLocal()

def list_projects():
    db = get_db()
    try:
        tasks = db.query(models.TaskModel).all()
        cols = {c.id: c.name for c in db.query(models.ColumnModel).all()}
        output = [{"id": t.id, "title": t.title, "column": cols.get(t.column_id, "Unknown"), "agent_id": t.agent_id} for t in tasks]
        print(json.dumps(output, indent=2))
    finally:
        db.close()

def get_project_details(project_id):
    db = get_db()
    try:
        t = db.query(models.TaskModel).filter(models.TaskModel.id == project_id).first()
        if not t:
            print(json.dumps({"error": "Project not found"}))
            return
        cols = {c.id: c.name for c in db.query(models.ColumnModel).all()}
        output = {
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "column": cols.get(t.column_id, "Unknown"),
            "tasks": t.subtasks,
            "expected_result": t.expected_result
        }
        print(json.dumps(output, indent=2))
    finally:
        db.close()

def move_project(project_id, column_name):
    db = get_db()
    try:
        t = db.query(models.TaskModel).filter(models.TaskModel.id == project_id).first()
        c = db.query(models.ColumnModel).filter(models.ColumnModel.name == column_name).first()
        if not t or not c:
            print(json.dumps({"error": "Project or Column not found"}))
            return
        t.column_id = c.id
        db.commit()
        print(json.dumps({"status": "success", "new_column": column_name}))
    finally:
        db.close()

def close_task(project_id, task_index):
    # This logic matches main.py close_subtask
    db = get_db()
    try:
        t = db.query(models.TaskModel).filter(models.TaskModel.id == project_id).first()
        if not t or not t.subtasks or task_index < 1 or task_index > len(t.subtasks):
            print(json.dumps({"error": "Invalid project or task index"}))
            return
        
        idx = task_index - 1
        updated_subs = []
        for i, s in enumerate(t.subtasks):
            s_dict = dict(s)
            if i == idx: s_dict['status'] = 'closed'
            elif i == idx + 1: s_dict['status'] = 'open'
            updated_subs.append(s_dict)
        
        t.subtasks = updated_subs
        db.commit()
        print(json.dumps({"status": "success", "tasks": updated_subs}))
    finally:
        db.close()

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "--list": list_projects()
    elif cmd == "--details" and len(sys.argv) > 2: get_project_details(int(sys.argv[2]))
    elif cmd == "--move" and len(sys.argv) > 3: move_project(int(sys.argv[2]), sys.argv[3])
    elif cmd == "--close" and len(sys.argv) > 3: close_task(int(sys.argv[2]), int(sys.argv[3]))
    else:
        print("Usage: python3 debug_db.py [--list | --details ID | --move ID COL | --close ID IDX]")
