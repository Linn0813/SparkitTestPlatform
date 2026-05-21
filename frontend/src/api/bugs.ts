import http from './http';
import type { BugActivity, BugComment, BugItem } from '@/types/business';

export interface ListBugsParams {
  status_key?: string;
  assignee_id?: string;
  reporter_id?: string;
  follower_id?: string;
  plan_version_id?: string;
  found_version_id?: string;
  requirement_id?: string;
  plan_id?: string;
  q?: string;
  /** JSON: { fieldId: value | __empty__ } */
  custom_filters?: string;
}

export function listBugs(params?: ListBugsParams) {
  return http.get<BugItem[]>('/bugs', { params });
}

export function getBug(id: string) {
  return http.get<BugItem>(`/bugs/${id}`);
}

export function createBug(data: {
  title: string;
  status_key?: string;
  description?: string;
  custom_fields?: Record<string, unknown>;
  case_ids?: string[];
  requirement_ids?: string[];
  plan_ids?: string[];
  plan_version_id?: string | null;
  found_version_id?: string | null;
  reporter_id?: string;
  follower_ids?: string[];
}) {
  return http.post<BugItem>('/bugs', data);
}

export function updateBug(
  id: string,
  data: Partial<{
    title: string;
    status_key: string;
    description: string;
    custom_fields: Record<string, unknown>;
    requirement_ids: string[];
    plan_ids: string[];
    plan_version_id: string | null;
    found_version_id: string | null;
    reporter_id: string;
    follower_ids: string[];
  }>
) {
  return http.patch<BugItem>(`/bugs/${id}`, data);
}

export function deleteBug(id: string) {
  return http.delete(`/bugs/${id}`);
}

export function listBugComments(bugId: string) {
  return http.get<BugComment[]>(`/bugs/${bugId}/comments`);
}

export function createBugComment(bugId: string, body: string) {
  return http.post<BugComment>(`/bugs/${bugId}/comments`, { body });
}

export function listBugActivities(bugId: string) {
  return http.get<BugActivity[]>(`/bugs/${bugId}/activities`);
}

export function uploadAttachment(bugId: string, file: File) {
  const form = new FormData();
  form.append('file', file);
  return http.post(`/bugs/${bugId}/attachments`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
}
