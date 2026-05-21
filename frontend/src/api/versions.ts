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
