import http from './http';
import type { VersionStatusRule, VersionType } from '@/types/business';

function versionTypeQuery(versionType: VersionType): string {
  return `version_type=${encodeURIComponent(versionType)}`;
}

export function listVersionStatusRules(projectId: string, versionType: VersionType) {
  return http.get<VersionStatusRule[]>(
    `/projects/${projectId}/version-status-rules?${versionTypeQuery(versionType)}`
  );
}

export function saveVersionStatusRules(
  projectId: string,
  versionType: VersionType,
  rules: {
    status: string;
    node_keys: string[];
    sort: number;
    trigger_type: string;
  }[]
) {
  return http.put<VersionStatusRule[]>(
    `/projects/${projectId}/version-status-rules?${versionTypeQuery(versionType)}`,
    { rules }
  );
}

export function syncProjectVersionStatuses(projectId: string) {
  return http.post<{ updated_count: number }>(`/projects/${projectId}/versions/sync-statuses`);
}
