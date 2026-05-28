import http from './http';
import type { ProjectVersion } from '@/types/business';

export function listVersions() {
  return http.get<ProjectVersion[]>('/versions');
}

export function getVersion(id: string) {
  return http.get<ProjectVersion>(`/versions/${id}`);
}

export type VersionPayload = {
  name: string;
  released_at?: string | null;
};

export function createVersion(data: VersionPayload) {
  return http.post<ProjectVersion>('/versions', data);
}

export function updateVersion(id: string, data: VersionPayload) {
  return http.patch<ProjectVersion>(`/versions/${id}`, data);
}

export function deleteVersion(id: string) {
  return http.delete(`/versions/${id}`);
}

export type VersionNodeCompleteResult = {
  version: ProjectVersion;
  wecom_mention_count?: number | null;
};

export function completeVersionNode(id: string, nodeKey: string) {
  return http.post<VersionNodeCompleteResult>(`/versions/${id}/nodes/${nodeKey}/complete`);
}

export function reopenVersionNode(id: string, nodeKey: string) {
  return http.post<ProjectVersion>(`/versions/${id}/nodes/${nodeKey}/reopen`);
}
