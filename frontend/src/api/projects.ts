import http from './http';
import type { Project, ProjectMember } from '@/types';

export function listProjects() {
  return http.get<Project[]>('/projects');
}

export function createProject(data: { name: string }) {
  return http.post<Project>('/projects', data);
}

export function updateProject(id: string, data: Partial<Project>) {
  return http.patch<Project>(`/projects/${id}`, data);
}

export function deleteProject(id: string) {
  return http.delete(`/projects/${id}`);
}

export function listProjectMembers(projectId: string) {
  return http.get<ProjectMember[]>(`/projects/${projectId}/members`);
}

export function addProjectMember(projectId: string, data: { user_id: string; role: string }) {
  return http.post<ProjectMember>(`/projects/${projectId}/members`, data);
}

export function removeProjectMember(projectId: string, memberId: string) {
  return http.delete(`/projects/${projectId}/members/${memberId}`);
}

export function uploadProjectFile(projectId: string, file: File) {
  const form = new FormData();
  form.append('file', file);
  return http.post<{
    object_key: string;
    filename: string;
    size: number;
    content_type: string;
    kind: string;
    url: string;
  }>(`/projects/${projectId}/uploads`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
}

export function getProjectFileUrl(projectId: string, objectKey: string) {
  return http.get<{ url: string }>(`/projects/${projectId}/files/url`, {
    params: { object_key: objectKey },
  });
}
