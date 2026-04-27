import axios from 'axios';

// Use the current hostname so it works over LAN/Network
const API_URL = `http://${window.location.hostname}:8000`;

const api = axios.create({
  baseURL: API_URL,
});

export interface SubTask {
  title: string;
  description: string;
  instruction: string;
  definition_of_done: string;
  whats_next: string;
  agent_id?: string;
  review_required?: boolean;
  status: 'open' | 'pending' | 'closed';
}

export interface Task {
  id: number;
  title: string;
  description: string | null;
  column_id: number;
  expected_result?: string;
  subtasks?: SubTask[];
  workflow_ids?: number[];
  order: number;
  created_at: string;
  updated_at: string;
}

export interface Column {
  id: number;
  name: string;
  default_agent_id?: string;
  expected_result?: string;
  steps?: string[];
  order: number;
  tasks: Task[];
}

export interface Agent {
  id: string;
  name?: string;
  workspace?: string;
}

export const getColumns = () => api.get<Column[]>('/columns');
export const updateColumn = (id: number, column: Partial<Column>) => api.put<Column>(`/columns/${id}`, column);
export const getAgents = () => api.get<Agent[]>('/agents');
export const createTask = (task: Partial<Task>) => api.post<Task>('/tasks', task);
export const updateTask = (id: number, task: Partial<Task>) => api.put<Task>(`/tasks/${id}`, task);
export const delete_task = (id: number) => api.delete(`/tasks/${id}`);
export const reorderTasks = (taskIds: number[], columnId: number) => api.post('/tasks/reorder', taskIds, { params: { column_id: columnId } });
export const fixColumns = () => api.get('/health/fix-columns');

export const uploadAttachment = (taskId: number, file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  return api.post(`/tasks/${taskId}/attachments`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
};

export const getAttachments = (taskId: number) => api.get<string[]>(`/tasks/${taskId}/attachments`);
export const closeSubtask = (taskId: number, subtaskIndex: number) => api.post<Task>(`/tasks/${taskId}/subtasks/${subtaskIndex}/close`);
export const reopenSubtask = (taskId: number, subtaskIndex: number) => api.post<Task>(`/tasks/${taskId}/subtasks/${subtaskIndex}/reopen`);

export default api;
