from pydantic import BaseModel
from typing import List, Optional, Literal
from datetime import datetime

class SubTask(BaseModel):
    title: str
    description: str
    instruction: str
    definition_of_done: str
    whats_next: str
    agent_id: Optional[str] = None
    review_required: bool = False
    status: Literal['open', 'pending', 'closed'] = 'pending'

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    column_id: int
    expected_result: Optional[str] = None
    subtasks: Optional[List[SubTask]] = []
    workflow_ids: Optional[List[int]] = None
    order: Optional[int] = 0

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    column_id: Optional[int] = None
    expected_result: Optional[str] = None
    subtasks: Optional[List[SubTask]] = None
    workflow_ids: Optional[List[int]] = None
    order: Optional[int] = None

class Task(TaskBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ColumnBase(BaseModel):
    name: str
    default_agent_id: Optional[str] = None
    order: Optional[int] = 0

class ColumnCreate(ColumnBase):
    pass

class ColumnUpdate(BaseModel):
    name: Optional[str] = None
    default_agent_id: Optional[str] = None
    order: Optional[int] = None

class Column(ColumnBase):
    id: int
    tasks: List[Task] = []

    class Config:
        from_attributes = True

# For the front-end dashboard view
class BoardState(BaseModel):
    columns: List[Column]
