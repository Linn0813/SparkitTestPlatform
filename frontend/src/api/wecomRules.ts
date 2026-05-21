import http from './http';
import type { WecomNotifyRule } from '@/types/business';

export function listWecomNotifyRules(projectId: string) {
  return http.get<WecomNotifyRule[]>(`/projects/${projectId}/wecom-notify-rules`);
}

export function createWecomNotifyRule(
  projectId: string,
  data: {
    kind?: 'create' | 'transition';
    from_status_key?: string;
    to_status_key?: string;
    message_template: string;
    notify_roles?: string[];
    enabled?: boolean;
  }
) {
  return http.post<WecomNotifyRule>(`/projects/${projectId}/wecom-notify-rules`, data);
}

export function updateWecomNotifyRule(
  projectId: string,
  ruleId: string,
  data: Partial<{
    from_status_key: string;
    to_status_key: string;
    message_template: string;
    notify_roles: string[];
    enabled: boolean;
  }>
) {
  return http.patch<WecomNotifyRule>(`/projects/${projectId}/wecom-notify-rules/${ruleId}`, data);
}

export function deleteWecomNotifyRule(projectId: string, ruleId: string) {
  return http.delete(`/projects/${projectId}/wecom-notify-rules/${ruleId}`);
}

export function upsertCreateWecomRule(
  projectId: string,
  data: {
    message_template?: string;
    notify_roles?: string[];
    enabled?: boolean;
  }
) {
  return http.put<WecomNotifyRule>(`/projects/${projectId}/wecom-notify-rules/create`, data);
}
