import http from './http';
import type {
  VersionWecomIntegration,
  VersionWecomNotifyRule,
  VersionWecomNotifyRuleOption,
} from '@/types/business';

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

export function listVersionWecomRuleOptions(projectId: string) {
  return http.get<VersionWecomNotifyRuleOption[]>(
    `/projects/${projectId}/version-wecom-notify-rule-options`
  );
}

export function createVersionWecomRule(
  projectId: string,
  data: {
    node_key: string;
    message_template: string;
    notify_user_ids?: string[];
    enabled?: boolean;
  }
) {
  return http.post<VersionWecomNotifyRule>(
    `/projects/${projectId}/version-wecom-notify-rules`,
    data
  );
}

export function patchVersionWecomRule(
  projectId: string,
  ruleId: string,
  data: { message_template?: string; notify_user_ids?: string[]; enabled?: boolean }
) {
  return http.patch<VersionWecomNotifyRule>(
    `/projects/${projectId}/version-wecom-notify-rules/${ruleId}`,
    data
  );
}

export function deleteVersionWecomRule(projectId: string, ruleId: string) {
  return http.delete(`/projects/${projectId}/version-wecom-notify-rules/${ruleId}`);
}

export function updateVersionWecomRuleByNode(
  projectId: string,
  nodeKey: string,
  data: { message_template?: string; notify_user_ids?: string[]; enabled?: boolean }
) {
  return http.put<VersionWecomNotifyRule>(
    `/projects/${projectId}/version-wecom-notify-rules/by-node/${nodeKey}`,
    data
  );
}
