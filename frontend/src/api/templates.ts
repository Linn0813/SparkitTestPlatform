import http from './http';
import type { BugStatusDef, FieldTemplate, WecomIntegration } from '@/types/business';

export function getTemplate(projectId: string, scene: 'functional_case' | 'bug') {
  return http.get<FieldTemplate>(`/projects/${projectId}/templates/${scene}`);
}

export function updateTemplate(projectId: string, scene: 'functional_case' | 'bug', fields: unknown[]) {
  return http.patch<FieldTemplate>(`/projects/${projectId}/templates/${scene}`, { fields });
}

export function listBugStatuses(projectId: string) {
  return http.get<BugStatusDef[]>(`/projects/${projectId}/bug-statuses`);
}

export function createBugStatus(projectId: string, data: Partial<BugStatusDef>) {
  return http.post<BugStatusDef>(`/projects/${projectId}/bug-statuses`, data);
}

export function updateBugStatus(projectId: string, statusId: string, data: Partial<BugStatusDef>) {
  return http.patch<BugStatusDef>(`/projects/${projectId}/bug-statuses/${statusId}`, data);
}

export function deleteBugStatus(projectId: string, statusId: string) {
  return http.delete(`/projects/${projectId}/bug-statuses/${statusId}`);
}

export function getWecom(projectId: string) {
  return http.get<WecomIntegration>(`/projects/${projectId}/integrations/wecom`);
}

export function updateWecom(projectId: string, data: Partial<WecomIntegration>) {
  return http.patch<WecomIntegration>(`/projects/${projectId}/integrations/wecom`, data);
}

export function testWecom(projectId: string, message?: string) {
  return http.post(`/projects/${projectId}/integrations/wecom/test`, { message });
}
