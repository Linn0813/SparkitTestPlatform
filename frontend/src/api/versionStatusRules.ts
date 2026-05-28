import http from './http';
import type { VersionStatusRule } from '@/types/business';

export function listVersionStatusRules(projectId: string) {
  return http.get<VersionStatusRule[]>(`/projects/${projectId}/version-status-rules`);
}

export function saveVersionStatusRules(
  projectId: string,
  rules: {
    status: string;
    node_keys: string[];
    sort: number;
    trigger_type: string;
  }[]
) {
  return http.put<VersionStatusRule[]>(`/projects/${projectId}/version-status-rules`, { rules });
}

export function syncProjectVersionStatuses(projectId: string) {
  return http.post<{ updated_count: number }>(`/projects/${projectId}/versions/sync-statuses`);
}
