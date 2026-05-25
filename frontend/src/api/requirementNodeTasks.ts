import http from './http';
import type { Requirement, RequirementNodeTask } from '@/types/business';

export function listRequirementNodeTasks(requirementId: string) {
  return http.get<RequirementNodeTask[]>(`/requirements/${requirementId}/node-tasks`);
}

export function createRequirementNodeTask(
  requirementId: string,
  nodeKey: string,
  data: {
    title: string;
    role_key: string;
    assignee_id?: string | null;
    estimate_points?: number | null;
    scheduled_start?: string | null;
    scheduled_end?: string | null;
  }
) {
  return http.post<Requirement>(`/requirements/${requirementId}/nodes/${nodeKey}/tasks`, data);
}

export function updateRequirementNodeTask(
  requirementId: string,
  nodeKey: string,
  taskId: string,
  data: {
    title?: string;
    role_key?: string;
    assignee_id?: string | null;
    estimate_points?: number | null;
    scheduled_start?: string | null;
    scheduled_end?: string | null;
    sort?: number;
  }
) {
  return http.patch<Requirement>(
    `/requirements/${requirementId}/nodes/${nodeKey}/tasks/${taskId}`,
    data
  );
}

export function deleteRequirementNodeTask(requirementId: string, nodeKey: string, taskId: string) {
  return http.delete<Requirement>(`/requirements/${requirementId}/nodes/${nodeKey}/tasks/${taskId}`);
}
