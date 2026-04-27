from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from database import Base
import datetime

class ColumnModel(Base):
    __tablename__ = "columns"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    default_agent_id = Column(String, nullable=True)  # New: Automatic assignee for this column
    order = Column(Integer)  # To maintain position

    tasks = relationship("TaskModel", back_populates="column", cascade="all, delete-orphan")

class TaskModel(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String, nullable=True)
    column_id = Column(Integer, ForeignKey("columns.id"))
    expected_result = Column(String, nullable=True)
    subtasks = Column(JSON, nullable=True)  # List of objects representing subtasks
    workflow_ids = Column(JSON, nullable=True)  # List of column IDs that this task needs to visit
    order = Column(Integer)  # Position within column
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    column = relationship("ColumnModel", back_populates="tasks")
