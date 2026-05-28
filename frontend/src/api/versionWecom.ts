import http from './http';
import type { VersionWecomIntegration, VersionWecomNotifyRule } from '@/types/business';

export function getVersionWecom(projectId: string) {
  return http.get<VersionWecomIntegration>(`/projects/${projectId}/integrations/version-wecom`);
}

export function updateVersionWecom(projectId: string, data: Partial<VersionWecomIntegration>) {
  return http.patch<VersionWecomIntegration>(
    `/projects/${projectId}/integrations/version-wecom`,
    data
  );
}

export function testVersionWecom(projectId: string, message?: string) {
  return http.post(`/projects/${projectId}/integrations/version-wecom/test`, { message });
}

export function listVersionWecomRules(projectId: string) {
  return http.get<VersionWecomNotifyRule[]>(`/projects/${projectId}/version-wecom-notify-rules`);
}

export function updateVersionWecomRule(
  projectId: string,
  eventKey: string,
  data: { message_template?: string; notify_user_ids?: string[]; enabled?: boolean }
) {
  return http.put<VersionWecomNotifyRule>(
    `/projects/${projectId}/version-wecom-notify-rules/${eventKey}`,
    data
  );
}
