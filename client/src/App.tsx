import React, { useState, useEffect } from 'react';
import type { 
  DragStartEvent, 
  DragOverEvent, 
  DragEndEvent,
} from '@dnd-kit/core';
import { 
  DndContext, 
  DragOverlay, 
  closestCorners, 
  KeyboardSensor, 
  PointerSensor, 
  useSensor, 
  useSensors, 
  defaultDropAnimationSideEffects
} from '@dnd-kit/core';
import { 
  SortableContext, 
  sortableKeyboardCoordinates, 
  verticalListSortingStrategy 
} from '@dnd-kit/sortable';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { 
  Plus, 
  Trash2, 
  MoreHorizontal, 
  GripVertical, 
  CheckCircle2, 
  Check,
  Lightbulb, 
  Palette, 
  Code2, 
  FlaskConical,
  Paperclip,
  User,
  X,
  Pencil,
  ChevronDown
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import type { Column, Task, Agent } from './api';
import * as api from './api';

// --- Components ---

const TaskCard = ({ task, onDelete, onEdit, onRefresh }: { task: Task; onDelete: (id: number) => void; onEdit: (task: Task) => void; onRefresh: () => void }) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging
  } = useSortable({ 
    id: task.id,
    data: {
      type: 'Project',
      task
    }
  });

  const style = {
    transition,
    transform: CSS.Translate.toString(transform),
    opacity: isDragging ? 0.3 : 1,
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      try {
        await api.uploadAttachment(task.id, e.target.files[0]);
        alert("File attached successfully!");
        // We could refresh state here to show a badge or list
      } catch (err) {
        console.error("Upload failed", err);
        alert("Upload failed");
      }
    }
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`task-card ${isDragging ? 'dragging' : ''}`}
      {...attributes}
    >
      <div className="task-card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <h4>
          <span style={{ color: 'var(--primary)', opacity: 0.8, marginRight: '8px', fontSize: '0.9em', fontWeight: 500 }}>
            #{task.id}
          </span>
          {task.title}
        </h4>
        <div {...listeners} className="drag-handle" style={{ cursor: 'grab', padding: '4px' }}>
          <GripVertical size={16} color="#94a3b8" />
        </div>
      </div>
      {task.description && <p>{task.description}</p>}
      
      {task.subtasks && task.subtasks.length > 0 && (
        <div className="task-subtasks" style={{ marginTop: '1rem', borderTop: '1px solid var(--glass-border)', paddingTop: '1rem', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {task.subtasks.map((sub, idx) => {
            const isClosed = sub.status === 'closed';
            const isOpen = sub.status === 'open';
            
            return (
              <div key={idx} className="subtask-row" style={{ 
                fontSize: '0.8rem', 
                opacity: isClosed ? 0.4 : (isOpen ? 1 : 0.6), 
                display: 'flex', 
                alignItems: 'flex-start', 
                gap: '8px',
                padding: '8px',
                borderRadius: '8px',
                background: isOpen ? 'rgba(var(--primary-rgb), 0.1)' : 'rgba(255,255,255,0.02)',
                border: isOpen ? '1px solid rgba(99, 102, 241, 0.2)' : '1px solid transparent'
              }}>
                <div 
                  onClick={async (e) => {
                    e.stopPropagation();
                    try {
                      if (isClosed) {
                        await api.reopenSubtask(task.id, idx);
                      } else {
                        await api.closeSubtask(task.id, idx);
                      }
                      onRefresh(); 
                    } catch (err) {
                      console.error("Failed to update task", err);
                    }
                  }}
                  className="subtask-status-box"
                  style={{ 
                    cursor: 'pointer',
                    minWidth: '22px', 
                    height: '22px', 
                    borderRadius: '6px', 
                    background: isClosed ? 'var(--success)' : (isOpen ? 'var(--primary)' : 'rgba(255,255,255,0.05)'), 
                    border: (isClosed || isOpen) ? 'none' : '1px solid rgba(255,255,255,0.1)',
                    color: (isClosed || isOpen) ? 'white' : 'var(--text)', 
                    display: 'flex', 
                    alignItems: 'center', 
                    justifyContent: 'center', 
                    fontSize: '0.7rem', 
                    fontWeight: 800,
                    marginTop: '1px',
                    boxShadow: (isClosed || isOpen) ? `0 0 10px ${isClosed ? 'rgba(34, 197, 94, 0.3)' : 'rgba(99, 102, 241, 0.3)'}` : 'none'
                  }}
                >
                  {isClosed ? <Check size={12} strokeWidth={3} /> : idx + 1}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ 
                    fontWeight: isOpen ? 700 : 500, 
                    color: isOpen ? 'var(--text-main)' : 'var(--text-muted)', 
                    textDecoration: isClosed ? 'line-through' : 'none' 
                  }}>
                    {sub.title || sub.description}
                  </div>
                  {sub.agent_id && (
                    <div style={{ fontSize: '0.7rem', opacity: isOpen ? 1 : 0.5, color: isOpen ? 'var(--primary)' : 'inherit', display: 'flex', alignItems: 'center', gap: '4px', marginTop: '2px' }}>
                      <User size={10} /> {isOpen ? 'Active: ' : ''}{sub.agent_id}
                    </div>
                  )}
                </div>
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  <select 
                    className={`status-select ${sub.status}`}
                    value={sub.status}
                    onClick={(e) => e.stopPropagation()}
                    onChange={async (e) => {
                      e.stopPropagation();
                      const newStatus = e.target.value as 'open' | 'pending' | 'closed';
                      if (!task.subtasks) return;
                      
                      const updatedSubtasks = [...task.subtasks];
                      updatedSubtasks[idx] = { ...updatedSubtasks[idx], status: newStatus };
                      
                      try {
                        await api.updateTask(task.id, { subtasks: updatedSubtasks });
                        onRefresh();
                      } catch (err) {
                        console.error("Failed to update status", err);
                      }
                    }}
                  >
                    <option value="open">Open</option>
                    <option value="pending">Pending</option>
                    <option value="closed">Closed</option>
                  </select>
                </div>
              </div>
            );
          })}
        </div>
      )}

      <div className="task-footer" style={{ marginTop: '1rem', display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: '8px' }}>
        {(() => {
          const reviewIdx = task.subtasks?.findIndex(s => s.status === 'open' && s.review_required);
          if (reviewIdx !== undefined && reviewIdx !== -1) {
            return (
              <button 
                onClick={async (e) => {
                  e.stopPropagation();
                  try {
                    await api.closeSubtask(task.id, reviewIdx);
                    onRefresh();
                  } catch (err) { console.error("Failed to approve review", err); }
                }}
                className="btn btn-success"
                style={{ 
                  fontSize: '0.7rem', 
                  padding: '4px 10px',
                  marginRight: 'auto'
                }}
              >
                Review Completed
              </button>
            );
          }
          return null;
        })()}
        <input 
          type="file" 
          id={`file-input-${task.id}`} 
          style={{ display: 'none' }} 
          onChange={handleFileChange}
        />
        <label htmlFor={`file-input-${task.id}`} className="btn-icon" title="Attach file" style={{ cursor: 'pointer' }}>
          <Paperclip size={14} />
        </label>
        <button 
          onClick={(e) => { e.stopPropagation(); onEdit(task); }}
          className="btn-icon"
          title="Edit project"
        >
          <Pencil size={14} /> 
        </button>
        <button 
          onClick={(e) => { e.stopPropagation(); onDelete(task.id); }}
          className="btn-icon"
          title="Delete project"
        >
          <Trash2 size={14} />
        </button>
      </div>
      
      {task.workflow_ids && task.workflow_ids.length > 0 && (
        <div className="task-workflow-indicator" style={{ display: 'flex', gap: '4px', marginTop: '12px' }}>
          {task.workflow_ids.map(id => (
            <div 
              key={id} 
              className={`workflow-dot ${task.column_id === id ? 'active' : ''}`} 
              title={`Stage ${id}`}
              style={{ 
                width: '6px', 
                height: '6px', 
                borderRadius: '50%', 
                backgroundColor: task.column_id === id ? 'var(--primary)' : 'rgba(255,255,255,0.2)',
                boxShadow: task.column_id === id ? '0 0 8px var(--primary)' : 'none'
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
};

const KanbanColumn = ({ 
  column, 
  tasks, 
  onDeleteTask,
  onEditTask,
  onRefresh
}: { 
  column: Column; 
  tasks: Task[]; 
  onDeleteTask: (id: number) => void;
  onEditTask: (task: Task) => void;
  onRefresh: () => void;
}) => {
  const { setNodeRef } = useSortable({
    id: `column-${column.id}`,
    data: {
      type: 'Column',
      column
    }
  });

  const taskIds = tasks.map(t => t.id);

  return (
    <div ref={setNodeRef} className="kanban-column">
      <div className="column-header" style={{ position: 'relative' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <h3>
            {column.name === 'Idea' && <Lightbulb size={20} color="#ef4444" />}
            {column.name === 'Design' && <Palette size={20} color="#a855f7" />}
            {column.name === 'Development' && <Code2 size={20} color="#3b82f6" />}
            {column.name === 'QA' && <FlaskConical size={20} color="#f59e0b" />}
            {column.name === 'Done' && <CheckCircle2 size={20} color="#10b981" />}
            {(!['Idea', 'Design', 'Development', 'QA', 'Done'].includes(column.name)) && <User size={20} color="var(--primary)" />}
            {column.name}
            <span className="task-count">{tasks.length}</span>
          </h3>
          {column.default_agent_id && (
            <div style={{ fontSize: '0.7rem', opacity: 0.6, display: 'flex', alignItems: 'center', gap: '4px', marginLeft: '24px' }}>
              <User size={10} /> {column.default_agent_id}
            </div>
          )}
        </div>
        <button className="btn-icon"><MoreHorizontal size={18} /></button>
      </div>
      
      <SortableContext items={taskIds} strategy={verticalListSortingStrategy}>
        <div className="task-list">
          {tasks.map(task => (
            <TaskCard key={task.id} task={task} onDelete={onDeleteTask} onEdit={onEditTask} onRefresh={onRefresh} />
          ))}
        </div>
      </SortableContext>
    </div>
  );
};

// --- Main App ---

export default function App() {
  const [columns, setColumns] = useState<Column[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [activeTask, setActiveTask] = useState<Task | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [taskToDelete, setTaskToDelete] = useState<Task | null>(null);
  const [newTaskTitle, setNewTaskTitle] = useState('');
  const [newTaskDesc, setNewTaskDesc] = useState('');
  const [newTaskExpectedResult, setNewTaskExpectedResult] = useState('');
  const [newTaskSubtasks, setNewTaskSubtasks] = useState<api.SubTask[]>([
    { title: '', description: '', instruction: '', definition_of_done: '', whats_next: '', agent_id: '', review_required: false, status: 'pending' }
  ]);
  const [selectedWorkflowIds, setSelectedWorkflowIds] = useState<number[]>([]);
  const [isEditMode, setIsEditMode] = useState(false);
  const [editingTaskId, setEditingTaskId] = useState<number | null>(null);
  const [theme, setTheme] = useState(localStorage.getItem('kanban-theme') || 'default');
  const [expandedSubtaskIndices, setExpandedSubtaskIndices] = useState<number[]>([]);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('kanban-theme', theme);
  }, [theme]);

  // Pre-select "Done" stage when modal opens
  useEffect(() => {
    if (isModalOpen) {
      const doneCol = columns.find(c => c.name === 'Done');
      if (doneCol) {
        setSelectedWorkflowIds(prev => prev.includes(doneCol.id) ? prev : [...prev, doneCol.id].sort());
      }
    }
  }, [isModalOpen, columns]);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 5,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const fetchData = async () => {
    try {
      const [colRes, agentRes] = await Promise.all([
        api.getColumns(),
        api.getAgents()
      ]);
      setColumns(colRes.data);
      setAgents(agentRes.data);
    } catch (err: any) {
      console.error("Failed to fetch data", err);
      // If columns are missing, try to fix them automatically once
      if (columns.length === 0) {
        try {
          await api.fixColumns();
          const colRes = await api.getColumns();
          setColumns(colRes.data);
        } catch (fixErr) {
          console.error("Auto-fix failed", fixErr);
        }
      }
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const findContainer = (id: string | number) => {
    // If it's a column ID directly (e.g. "column-1")
    if (typeof id === 'string' && id.startsWith('column-')) {
      const colId = parseInt(id.replace('column-', ''));
      return columns.find(c => c.id === colId);
    }
    // Search for task
    return columns.find(c => c.tasks.some(t => t.id === id));
  };

  const handleDragStart = (event: DragStartEvent) => {
    const { active } = event;
    const task = active.data.current?.task;
    if (task) setActiveTask(task);
  };

  const handleDragOver = async (event: DragOverEvent) => {
    const { active, over } = event;
    if (!over) return;

    const activeId = active.id;
    const overId = over.id;

    if (activeId === overId) return;

    const activeContainer = findContainer(activeId);
    const overContainer = findContainer(overId);

    if (!activeContainer || !overContainer || activeContainer === overContainer) {
      return;
    }

    // Move task between containers in local state for immediate feedback
    setColumns(prev => {
      const activeTasks = [...activeContainer.tasks];
      const overTasks = [...overContainer.tasks];

      const activeIndex = activeTasks.findIndex(t => t.id === activeId);
      const movedTask = { ...activeTasks[activeIndex], column_id: overContainer.id };
      
      activeTasks.splice(activeIndex, 1);
      overTasks.push(movedTask);

      return prev.map(c => {
        if (c.id === activeContainer.id) return { ...c, tasks: activeTasks };
        if (c.id === overContainer.id) return { ...c, tasks: overTasks };
        return c;
      });
    });
  };

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveTask(null);

    if (!over) return;

    const activeId = active.id as number;
    const overContainer = findContainer(over.id);

    if (!overContainer) return;

    // Persist all column states (to handle both order and column changes)
    try {
      // 1. Find the current column of the task in local state
      const currentTask = columns.flatMap(c => c.tasks).find(t => t.id === activeId);
      if (currentTask) {
        // 2. Update column_id if changed
        await api.updateTask(activeId, { column_id: overContainer.id });
        
        // 3. Batch reorder for all tasks in the container to be safe
        const taskIds = overContainer.tasks.map(t => t.id);
        await api.reorderTasks(taskIds, overContainer.id);
      }
    } catch (err) {
      console.error("Save failed", err);
    }
    
    fetchData(); // Sync with backend
  };


  const handleAddTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTaskTitle.trim()) return;

    try {
      const taskData = {
        title: newTaskTitle,
        description: newTaskDesc,
        expected_result: newTaskExpectedResult || undefined,
        subtasks: newTaskSubtasks.filter(s => s.description.trim() !== ''),
        workflow_ids: selectedWorkflowIds
      };

      if (isEditMode && editingTaskId) {
        await api.updateTask(editingTaskId, taskData);
      } else {
        const firstCol = columns[0];
        if (firstCol) {
          await api.createTask({
            ...taskData,
            column_id: firstCol.id,
          });
        }
      }
      
      resetModal();
      fetchData();
    } catch (err) {
      console.error("Failed to save task", err);
    }
  };

  const resetModal = () => {
    setNewTaskTitle('');
    setNewTaskDesc('');
    setNewTaskExpectedResult('');
    setNewTaskSubtasks([{ title: '', description: '', instruction: '', definition_of_done: '', whats_next: '', agent_id: '', review_required: false, status: 'pending' }]);
    setSelectedWorkflowIds([]);
    setIsModalOpen(false);
    setIsEditMode(false);
    setEditingTaskId(null);
    setExpandedSubtaskIndices([]);
  };

  const handleEditTask = (task: Task) => {
    setNewTaskTitle(task.title);
    setNewTaskDesc(task.description || '');
    setNewTaskExpectedResult(task.expected_result || '');
    setNewTaskSubtasks(task.subtasks && task.subtasks.length > 0 ? task.subtasks : [{ title: '', description: '', instruction: '', definition_of_done: '', whats_next: '', agent_id: '', review_required: false, status: 'pending' }]);
    setSelectedWorkflowIds(task.workflow_ids || []);
    setEditingTaskId(task.id);
    setExpandedSubtaskIndices([]);
    setIsEditMode(true);
    setIsModalOpen(true);
  };

  const handleDeleteTask = (id: number) => {
    const task = columns.flatMap(c => c.tasks).find(t => t.id === id);
    if (task) {
      setTaskToDelete(task);
      setIsDeleteModalOpen(true);
    }
  };

  const confirmDeleteTask = async () => {
    if (!taskToDelete) return;
    try {
      await api.delete_task(taskToDelete.id);
      setIsDeleteModalOpen(false);
      setTaskToDelete(null);
      fetchData();
    } catch (err) {
      console.error("Failed to delete task", err);
    }
  };

  return (
    <div className="app-container">
      <header className="header">
        <div>
          <h1>OpenClaw Kanban</h1>
          <p className="subtitle">Manage projects efficiently for your AI agent</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
          <div className="theme-switcher" style={{ display: 'flex', gap: '8px', background: 'var(--glass-bg)', padding: '6px', borderRadius: '12px', border: '1px solid var(--glass-border)' }}>
            {[
              { id: 'default', color: '#6366f1', label: 'Deep Sea' },
              { id: 'midnight', color: '#a855f7', label: 'Midnight' },
              { id: 'forest', color: '#10b981', label: 'Forest' },
              { id: 'sunset', color: '#f97316', label: 'Sunset' },
              { id: 'light', color: '#ffffff', label: 'Light Sky' },
            ].map(t => (
              <button 
                key={t.id}
                onClick={() => setTheme(t.id)}
                title={t.label}
                style={{ 
                  width: '24px', 
                  height: '24px', 
                  borderRadius: '50%', 
                  backgroundColor: t.color, 
                  border: theme === t.id ? '2px solid white' : '2px solid transparent',
                  cursor: 'pointer',
                  padding: 0,
                  transition: 'transform 0.2s'
                }}
                className={theme === t.id ? 'active-theme' : ''}
              />
            ))}
          </div>
          <button className="btn btn-primary" onClick={() => setIsModalOpen(true)}>
            <Plus size={20} />
            New Project
          </button>
        </div>
      </header>

      <main>
        <DndContext
          sensors={sensors}
          collisionDetection={closestCorners}
          onDragStart={handleDragStart}
          onDragOver={handleDragOver}
          onDragEnd={handleDragEnd}
        >
          <div className="kanban-board">
            {columns.length > 0 ? (
              columns.map(col => (
                <KanbanColumn 
                  key={col.id} 
                  column={col} 
                  tasks={col.tasks || []} 
                  onDeleteTask={handleDeleteTask}
                  onEditTask={handleEditTask}
                  onRefresh={fetchData}
                />
              ))
            ) : (
              <div style={{ 
                width: '100%', 
                height: '400px', 
                display: 'flex', 
                flexDirection: 'column', 
                alignItems: 'center', 
                justifyContent: 'center',
                background: 'var(--glass-bg)',
                borderRadius: 'var(--radius)',
                border: '1px dashed var(--glass-border)',
                gap: '20px'
              }}>
                <div style={{ color: 'var(--text-muted)', fontSize: '1.2rem' }}>No columns found.</div>
                <button 
                  className="btn btn-primary" 
                  onClick={async () => {
                    await api.fixColumns();
                    fetchData();
                  }}
                >
                  <Plus size={20} />
                  Initialize Default Columns
                </button>
              </div>
            )}
          </div>

          <DragOverlay dropAnimation={{
            sideEffects: defaultDropAnimationSideEffects({
              styles: {
                active: {
                  opacity: '0.5',
                },
              },
            }),
          }}>
            {activeTask ? (
              <div className="task-card drag-overlay">
                <h4>
                  <span style={{ color: 'var(--primary)', opacity: 0.8, marginRight: '8px', fontSize: '0.9em', fontWeight: 500 }}>
                    #{activeTask.id}
                  </span>
                  {activeTask.title}
                </h4>
                {activeTask.description && <p>{activeTask.description}</p>}
              </div>
            ) : null}
          </DragOverlay>
        </DndContext>
      </main>

      <AnimatePresence>
        {isModalOpen && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="modal-overlay"
            onClick={() => setIsModalOpen(false)}
          >
            <motion.div 
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: 20, opacity: 0 }}
              className="modal-content"
              style={{ maxWidth: '650px' }}
              onClick={e => e.stopPropagation()}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                <h2 style={{ margin: 0 }}>{isEditMode ? `Edit Project #${editingTaskId}` : 'Create New Project'}</h2>
              </div>

              <form onSubmit={handleAddTask}>
                <div style={{ maxHeight: '70vh', overflowY: 'auto', paddingRight: '1rem', margin: '0 -1rem' }}>
                  <div className="form-sections" style={{ display: 'flex', flexDirection: 'column', gap: '2rem', padding: '0 1rem' }}>
                  {/* Task Details Section */}
                  <div className="task-details-section">
                    <div className="form-group">
                      <label htmlFor="title">Title</label>
                      <input 
                        id="title"
                        className="form-input" 
                        value={newTaskTitle} 
                        onChange={e => setNewTaskTitle(e.target.value)} 
                        placeholder="Project title"
                        autoFocus
                      />
                    </div>
                    <div className="form-group">
                      <label htmlFor="desc">Description (Context)</label>
                      <textarea 
                        id="desc"
                        className="form-input" 
                        rows={4}
                        value={newTaskDesc} 
                        onChange={e => setNewTaskDesc(e.target.value)} 
                        placeholder="Project description..."
                      />
                    </div>
                    <div className="form-group">
                      <label htmlFor="expected">Expected Result (Definition of Done)</label>
                      <textarea 
                        id="expected"
                        className="form-input" 
                        rows={4}
                        value={newTaskExpectedResult} 
                        onChange={e => setNewTaskExpectedResult(e.target.value)} 
                        placeholder="What should the result be?"
                      />
                    </div>
                    
                    <div className="form-group">
                      <label>Workflow Stages (Required Columns)</label>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', marginTop: '8px' }}>
                        {columns.map(col => (
                          <label key={col.id} style={{ 
                            display: 'flex', 
                            alignItems: 'center', 
                            gap: '8px', 
                            background: 'rgba(255,255,255,0.05)', 
                            padding: '6px 12px', 
                            borderRadius: '8px',
                            cursor: 'pointer',
                            fontSize: '0.85rem'
                          }}>
                            <input 
                              type="checkbox" 
                              checked={selectedWorkflowIds.includes(col.id)}
                              disabled={col.name === 'Done'}
                              onChange={(e) => {
                                if (e.target.checked) {
                                  setSelectedWorkflowIds([...selectedWorkflowIds, col.id].sort());
                                } else {
                                  setSelectedWorkflowIds(selectedWorkflowIds.filter(id => id !== col.id));
                                }
                              }}
                            />
                            {col.name}
                            {col.name === 'Done' && <span style={{ fontSize: '0.7rem', opacity: 0.6 }}>(Required)</span>}
                          </label>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Subtasks Section */}
                  <div className="subtasks-section" style={{ borderTop: '1px solid var(--glass-border)', paddingTop: '2rem' }}>
                    <div className="form-group">
                      <label style={{ marginBottom: '1rem' }}>
                        <span style={{ fontSize: '1.1rem', fontWeight: 600 }}>Tasks</span>
                      </label>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                        {newTaskSubtasks.map((sub, idx) => {
                          const isExpanded = expandedSubtaskIndices.includes(idx);
                          return (
                            <div key={idx} style={{ 
                              background: 'rgba(255,255,255,0.03)', 
                              borderRadius: '16px',
                              border: '1px solid var(--glass-border)',
                              overflow: 'hidden',
                              transition: 'all 0.3s ease'
                            }}>
                              {/* Subtask Header (Toggle Area) */}
                              <div 
                                onClick={() => {
                                  if (isExpanded) {
                                    setExpandedSubtaskIndices(expandedSubtaskIndices.filter(i => i !== idx));
                                  } else {
                                    setExpandedSubtaskIndices([...expandedSubtaskIndices, idx]);
                                  }
                                }}
                                style={{ 
                                  padding: '1.2rem 1.5rem', 
                                  display: 'flex', 
                                  justifyContent: 'space-between', 
                                  alignItems: 'center',
                                  cursor: 'pointer',
                                  background: isExpanded ? 'rgba(255,255,255,0.05)' : 'transparent',
                                  borderBottom: isExpanded ? '1px solid var(--glass-border)' : 'none'
                                }}
                              >
                                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                                  <div style={{ 
                                    width: '24px', 
                                    height: '24px', 
                                    borderRadius: '6px', 
                                    background: 'var(--primary)', 
                                    color: 'white', 
                                    display: 'flex', 
                                    alignItems: 'center', 
                                    justifyContent: 'center',
                                    fontSize: '0.75rem',
                                    fontWeight: 700
                                  }}>
                                    {idx + 1}
                                  </div>
                                  <span style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text)' }}>
                                    Task {idx + 1}: {sub.title || 'Untitled Task'}
                                  </span>
                                </div>
                                <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }} onClick={e => e.stopPropagation()}>
                                   <div className="column-assignee-toggle" style={{ background: 'rgba(255,255,255,0.08)', padding: '4px 10px', borderRadius: '6px' }}>
                                      <select 
                                        value={sub.agent_id || ''} 
                                        onChange={e => {
                                          const newSubs = [...newTaskSubtasks];
                                          newSubs[idx].agent_id = e.target.value;
                                          setNewTaskSubtasks(newSubs);
                                        }}
                                        style={{ 
                                          background: 'transparent', 
                                          border: 'none', 
                                          color: 'var(--primary)', 
                                          fontSize: '0.75rem',
                                          fontWeight: 600,
                                          outline: 'none',
                                          cursor: 'pointer'
                                        }}
                                      >
                                        <option value="">Agent: Auto</option>
                                        {agents.map(a => (
                                          <option key={a.id} value={a.id}>{a.name || a.id}</option>
                                        ))}
                                      </select>
                                   </div>
                                   {newTaskSubtasks.length > 1 && (
                                    <button 
                                      type="button" 
                                      onClick={() => {
                                        if (window.confirm(`Are you sure you want to remove Task ${idx + 1} "${sub.title || 'Untitled'}"?`)) {
                                          setNewTaskSubtasks(newTaskSubtasks.filter((_, i) => i !== idx));
                                        }
                                      }}
                                      className="btn-icon"
                                      style={{ color: '#ef4444' }}
                                    >
                                      <X size={16} />
                                    </button>
                                  )}
                                  <ChevronDown size={20} style={{ transform: isExpanded ? 'rotate(180deg)' : 'rotate(0)', transition: 'transform 0.3s ease', opacity: 0.5 }} />
                                </div>
                              </div>
                              
                              {/* Subtask Details (Collapsible Area) */}
                              <AnimatePresence>
                                {isExpanded && (
                                  <motion.div 
                                    initial={{ height: 0, opacity: 0 }}
                                    animate={{ height: 'auto', opacity: 1 }}
                                    exit={{ height: 0, opacity: 0 }}
                                    transition={{ duration: 0.3 }}
                                    style={{ overflow: 'hidden' }}
                                  >
                                    <div style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '15px' }}>
                                      <div style={{ display: 'flex', gap: '15px', alignItems: 'flex-start' }}>
                                        <div style={{ flex: 1 }}>
                                          <label style={{ fontSize: '0.75rem', marginBottom: '6px', display: 'block', fontWeight: 500 }}>Title</label>
                                          <input 
                                            className="form-input" 
                                            style={{ padding: '10px 12px', fontSize: '0.9rem' }}
                                            value={sub.title} 
                                            onChange={(e) => {
                                              const newSubs = [...newTaskSubtasks];
                                              newSubs[idx].title = e.target.value;
                                              setNewTaskSubtasks(newSubs);
                                            }} 
                                            placeholder="Task title..."
                                          />
                                        </div>
                                        <div style={{ minWidth: '120px' }}>
                                          <label style={{ fontSize: '0.75rem', marginBottom: '6px', display: 'block', fontWeight: 500 }}>Status</label>
                                          <select 
                                            className={`status-select ${sub.status}`}
                                            style={{ width: '100%', height: '38px', fontSize: '0.8rem' }}
                                            value={sub.status}
                                            onChange={(e) => {
                                              const newSubs = [...newTaskSubtasks];
                                              newSubs[idx].status = e.target.value as 'open' | 'pending' | 'closed';
                                              setNewTaskSubtasks(newSubs);
                                            }}
                                          >
                                            <option value="open">Open</option>
                                            <option value="pending">Pending</option>
                                            <option value="closed">Closed</option>
                                          </select>
                                        </div>
                                      </div>
                                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                        <input 
                                          type="checkbox" 
                                          id={`review_req_${idx}`}
                                          checked={!!sub.review_required}
                                          onChange={(e) => {
                                            const newSubs = [...newTaskSubtasks];
                                            newSubs[idx].review_required = e.target.checked;
                                            setNewTaskSubtasks(newSubs);
                                          }}
                                        />
                                        <label htmlFor={`review_req_${idx}`} style={{ fontSize: '0.85rem', fontWeight: 500, margin: 0, cursor: 'pointer' }}>Require Review</label>
                                      </div>
                                      <div>
                                        <label style={{ fontSize: '0.75rem', marginBottom: '6px', display: 'block', fontWeight: 500 }}>Description</label>
                                        <textarea 
                                          className="form-input" 
                                          style={{ padding: '10px 12px', fontSize: '0.9rem', minHeight: '40px' }}
                                          rows={1}
                                          value={sub.description} 
                                          onChange={(e) => {
                                            const newSubs = [...newTaskSubtasks];
                                            newSubs[idx].description = e.target.value;
                                            setNewTaskSubtasks(newSubs);
                                          }} 
                                          placeholder="Task goal..."
                                        />
                                      </div>
                                      <div>
                                        <label style={{ fontSize: '0.75rem', marginBottom: '6px', display: 'block', fontWeight: 500 }}>Instruction</label>
                                        <textarea 
                                          className="form-input" 
                                          style={{ padding: '10px 12px', fontSize: '0.9rem', minHeight: '60px' }}
                                          rows={2}
                                          value={sub.instruction} 
                                          onChange={(e) => {
                                            const newSubs = [...newTaskSubtasks];
                                            newSubs[idx].instruction = e.target.value;
                                            setNewTaskSubtasks(newSubs);
                                          }} 
                                          placeholder="Execution steps..."
                                        />
                                      </div>
                                      <div>
                                        <label style={{ fontSize: '0.75rem', marginBottom: '6px', display: 'block', fontWeight: 500 }}>Definition of Done</label>
                                        <textarea 
                                          className="form-input" 
                                          style={{ padding: '10px 12px', fontSize: '0.9rem', minHeight: '40px' }}
                                          rows={1}
                                          value={sub.definition_of_done} 
                                          onChange={(e) => {
                                            const newSubs = [...newTaskSubtasks];
                                            newSubs[idx].definition_of_done = e.target.value;
                                            setNewTaskSubtasks(newSubs);
                                          }} 
                                          placeholder="Success criteria..."
                                        />
                                      </div>
                                      <div>
                                        <label style={{ fontSize: '0.75rem', marginBottom: '6px', display: 'block', fontWeight: 500 }}>What's Next</label>
                                        <textarea 
                                          className="form-input" 
                                          style={{ padding: '10px 12px', fontSize: '0.9rem', minHeight: '40px' }}
                                          rows={1}
                                          value={sub.whats_next} 
                                          onChange={(e) => {
                                            const newSubs = [...newTaskSubtasks];
                                            newSubs[idx].whats_next = e.target.value;
                                            setNewTaskSubtasks(newSubs);
                                          }} 
                                          placeholder="Next steps guidance..."
                                        />
                                      </div>
                                    </div>
                                  </motion.div>
                                )}
                              </AnimatePresence>
                            </div>
                          );
                        })}
                        <button 
                          type="button" 
                          onClick={() => {
                            setNewTaskSubtasks([...newTaskSubtasks, { title: '', description: '', instruction: '', definition_of_done: '', whats_next: '', agent_id: '', review_required: false, status: 'pending' }]);
                            setExpandedSubtaskIndices([...expandedSubtaskIndices, newTaskSubtasks.length]);
                          }}
                          className="btn btn-primary"
                          style={{ padding: '8px 16px', fontSize: '0.9rem', width: 'fit-content', alignSelf: 'center', marginTop: '1rem' }}
                        >
                          <Plus size={16} style={{ marginRight: '6px' }} /> Add Task
                        </button>
                      </div>
                    </div>
                  </div>
                  </div>
                </div>

                <div className="form-actions" style={{ marginTop: '2rem' }}>
                  <button type="button" className="btn" onClick={resetModal}>Cancel</button>
                  <button type="submit" className="btn btn-primary" style={{ padding: '0.6rem 2rem' }}>
                    {isEditMode ? 'Update Project' : 'Create Project'}
                  </button>
                </div>
              </form>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {isDeleteModalOpen && taskToDelete && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="modal-overlay"
            onClick={() => setIsDeleteModalOpen(false)}
          >
            <motion.div 
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="modal-content"
              style={{ maxWidth: '400px', textAlign: 'center' }}
              onClick={e => e.stopPropagation()}
            >
              <div style={{ color: 'var(--danger)', marginBottom: '1rem' }}>
                <Trash2 size={48} style={{ margin: '0 auto' }} />
              </div>
              <h2 style={{ marginTop: 0 }}>Delete Project?</h2>
              <p style={{ color: 'var(--text-muted)', marginBottom: '2rem' }}>
                Are you sure you want to delete project <strong>#{taskToDelete.id} "{taskToDelete.title}"</strong>? 
                This action cannot be undone.
              </p>
              <div className="form-actions" style={{ justifyContent: 'center' }}>
                <button 
                  className="btn" 
                  onClick={() => setIsDeleteModalOpen(false)}
                >
                  Keep It
                </button>
                <button 
                  className="btn" 
                  style={{ backgroundColor: 'var(--danger)', color: 'white' }}
                  onClick={confirmDeleteTask}
                >
                  Yes, Delete
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
      
      <footer style={{ marginTop: '3rem', textAlign: 'center', color: '#64748b', fontSize: '0.9rem' }}>
        <p>MCP Enabled • Powered by FastAPI & SQLite</p>
      </footer>
    </div>
  );
}
