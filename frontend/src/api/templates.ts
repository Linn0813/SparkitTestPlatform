import http from './http';
import type {
  BugStatusDef,
  FieldTemplate,
  RequirementOptionDef,
  RequirementRoleDef,
  WecomIntegration,
} from '@/types/business';

export type { RequirementRoleDef, RequirementOptionDef };

export function getTemplate(projectId: string, scene: 'functional_case' | 'bug' | 'requirement') {
  return http.get<FieldTemplate>(`/projects/${projectId}/templates/${scene}`);
}

export function updateTemplate(
  projectId: string,
  scene: 'functional_case' | 'bug' | 'requirement',
  fields: unknown[]
) {
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

export function listRequirementRoles(projectId: string) {
  return http.get<RequirementRoleDef[]>(`/projects/${projectId}/requirement-roles`);
}

export function createRequirementRole(projectId: string, data: Partial<RequirementRoleDef>) {
  return http.post<RequirementRoleDef>(`/projects/${projectId}/requirement-roles`, data);
}

export function updateRequirementRole(projectId: string, roleId: string, data: Partial<RequirementRoleDef>) {
  return http.patch<RequirementRoleDef>(`/projects/${projectId}/requirement-roles/${roleId}`, data);
}

export function deleteRequirementRole(projectId: string, roleId: string) {
  return http.delete(`/projects/${projectId}/requirement-roles/${roleId}`);
}

export function listRequirementOptions(projectId: string, category?: 'priority' | 'req_type') {
  return http.get<RequirementOptionDef[]>(`/projects/${projectId}/requirement-options`, {
    params: category ? { category } : undefined,
  });
}

export function createRequirementOption(projectId: string, data: Partial<RequirementOptionDef>) {
  return http.post<RequirementOptionDef>(`/projects/${projectId}/requirement-options`, data);
}

export function updateRequirementOption(
  projectId: string,
  optionId: string,
  data: Partial<RequirementOptionDef>
) {
  return http.patch<RequirementOptionDef>(`/projects/${projectId}/requirement-options/${optionId}`, data);
}

export function deleteRequirementOption(projectId: string, optionId: string) {
  return http.delete(`/projects/${projectId}/requirement-options/${optionId}`);
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
