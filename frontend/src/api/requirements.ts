import http from './http';
import type {
  Requirement,
  RequirementActivity,
  RequirementComment,
  RequirementNodeState,
  RequirementPriority,
  RequirementStatus,
  RequirementType,
} from '@/types/business';

export type RequirementNodeAction = 'start' | 'complete' | 'skip' | 'reopen' | 'reject';

export function listRequirements(params?: {
  version_id?: string;
  status?: RequirementStatus;
  priority?: RequirementPriority;
  req_type?: RequirementType;
  frontend_rd_id?: string;
  backend_rd_id?: string;
  pm_id?: string;
  qa_id?: string;
}) {
  return http.get<Requirement[]>('/requirements', { params });
}

export function getRequirement(id: string) {
  return http.get<Requirement>(`/requirements/${id}`);
}

export function createRequirement(data: {
  title: string;
  external_url?: string | null;
  version_id?: string | null;
  priority?: RequirementPriority;
  req_type?: RequirementType;
  frontend_rd_id?: string | null;
  backend_rd_id?: string | null;
  pm_id?: string | null;
  tech_owner_id?: string | null;
  qa_id?: string | null;
  designer_id?: string | null;
  role_assignee_ids?: Record<string, string[]>;
  enabled?: Record<string, boolean>;
  custom_fields?: Record<string, unknown>;
}) {
  return http.post<Requirement>('/requirements', data);
}

export function updateRequirement(
  id: string,
  data: {
    title?: string;
    external_url?: string | null;
    version_id?: string | null;
    priority?: RequirementPriority;
    req_type?: RequirementType;
    frontend_rd_id?: string | null;
    backend_rd_id?: string | null;
    pm_id?: string | null;
    tech_owner_id?: string | null;
    qa_id?: string | null;
    designer_id?: string | null;
    role_assignee_ids?: Record<string, string[]>;
    custom_fields?: Record<string, unknown>;
  }
) {
  return http.patch<Requirement>(`/requirements/${id}`, data);
}

export function deleteRequirement(id: string) {
  return http.delete(`/requirements/${id}`);
}

export function requirementNodeAction(id: string, nodeKey: string, action: RequirementNodeAction) {
  return http.post<Requirement>(`/requirements/${id}/nodes/${nodeKey}`, { action });
}

export function reopenRejectedRequirement(id: string) {
  return http.post<Requirement>(`/requirements/${id}/reopen-rejected`);
}

export function closeRequirement(id: string) {
  return http.post<Requirement>(`/requirements/${id}/close`);
}

export function reopenClosedRequirement(id: string) {
  return http.post<Requirement>(`/requirements/${id}/reopen-closed`);
}

export function syncRequirementStatus(id: string) {
  return http.post<Requirement>(`/requirements/${id}/sync-status`);
}

export function listRequirementActivities(id: string) {
  return http.get<RequirementActivity[]>(`/requirements/${id}/activities`);
}

export function listRequirementComments(id: string) {
  return http.get<RequirementComment[]>(`/requirements/${id}/comments`);
}

export function createRequirementComment(id: string, body: string) {
  return http.post<RequirementComment>(`/requirements/${id}/comments`, { body });
}

export function nodeStateLabel(state: RequirementNodeState): string {
  const map: Record<RequirementNodeState, string> = {
    pending: '未开始',
    in_progress: '进行中',
    completed: '已完成',
    skipped: '已跳过',
  };
  return map[state] ?? state;
}
