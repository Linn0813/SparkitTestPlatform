import http from './http';
import type { RequirementStatusRule } from '@/types/business';

export function listRequirementStatusRules(projectId: string) {
  return http.get<RequirementStatusRule[]>(`/projects/${projectId}/requirement-status-rules`);
}

export function saveRequirementStatusRules(
  projectId: string,
  rules: {
    status: string;
    node_keys: string[];
    sort: number;
    trigger_type: string;
  }[]
) {
  return http.put<RequirementStatusRule[]>(`/projects/${projectId}/requirement-status-rules`, { rules });
}
