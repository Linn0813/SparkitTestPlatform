import http from './http';
import type { Requirement, RequirementStatus } from '@/types/business';

export function listRequirements(params?: { version_id?: string; status?: RequirementStatus }) {
  return http.get<Requirement[]>('/requirements', { params });
}

export function getRequirement(id: string) {
  return http.get<Requirement>(`/requirements/${id}`);
}

export function createRequirement(data: {
  title: string;
  external_url?: string | null;
  version_id?: string | null;
  status?: RequirementStatus;
}) {
  return http.post<Requirement>('/requirements', data);
}

export function updateRequirement(
  id: string,
  data: {
    title?: string;
    external_url?: string | null;
    version_id?: string | null;
    status?: RequirementStatus;
  }
) {
  return http.patch<Requirement>(`/requirements/${id}`, data);
}

export function deleteRequirement(id: string) {
  return http.delete(`/requirements/${id}`);
}
