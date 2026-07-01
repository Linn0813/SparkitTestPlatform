import http from './http';

export interface VersionBrief {
  id: string;
  num: number;
  name: string;
}

export interface RequirementBugDensityItem {
  requirement_id: string;
  requirement_num: number;
  title: string;
  priority: string;
  bug_count: number;
  estimate_points: number;
  density: number | null;
}

export interface StaleRequirementItem {
  requirement_id: string;
  requirement_num: number;
  title: string;
  priority: string;
  status: string;
  stale_days: number;
  warning_level: 'warning' | 'danger';
  frontend_rd_name: string | null;
  backend_rd_name: string | null;
  qa_name: string | null;
}

export interface VersionDeliveryHealth {
  version_id: string;
  version_name: string;
  version_status: string;
  total_requirements: number;
  completed_requirements: number;
  incomplete_requirements: number;
  completion_rate: number;
  at_risk: boolean;
}

export interface LeakageRateOut {
  total_bugs: number;
  online_bugs: number;
  leakage_rate: number;
  by_version: { version_name: string; total: number; online: number; rate: number }[];
}

export interface BugReflowRateOut {
  resolved_bugs: number;
  reflowed_bugs: number;
  reflow_rate: number;
  reflow_bug_list: { bug_num: number; title: string; reflow_count: number; assignee_name: string | null }[];
}

export interface DeveloperBugRateItem {
  user_id: string;
  user_name: string;
  requirement_count: number;
  bug_count: number;
  estimate_points: number;
  bug_rate: number | null;
}

export interface BugResponseTimeItem {
  bug_id: string;
  bug_num: number;
  title: string;
  severity: string;
  created_at: string;
  first_response_hours: number | null;
  warning_level: 'ok' | 'warning' | 'danger' | 'unhandled';
  assignee_name: string | null;
}

export interface BugResponseTimeOut {
  avg_response_hours: number | null;
  items: BugResponseTimeItem[];
}

export interface BugSourceTrendItem {
  label: string;
  online: number;
  internal: number;
  testing: number;
  other: number;
}

function versionParams(versionIds?: string[]) {
  return versionIds && versionIds.length > 0 ? { params: { version_ids: versionIds } } : {};
}

export const qualityApi = {
  getVersions: () =>
    http.get<VersionBrief[]>('/quality/versions'),

  getRequirementBugDensity: (versionIds?: string[]) =>
    http.get<RequirementBugDensityItem[]>('/quality/requirement-bug-density', versionParams(versionIds)),

  getStaleRequirements: () =>
    http.get<StaleRequirementItem[]>('/quality/stale-requirements'),

  getVersionDeliveryHealth: (versionIds?: string[]) =>
    http.get<VersionDeliveryHealth[]>('/quality/version-delivery-health', versionParams(versionIds)),

  getLeakageRate: (versionIds?: string[]) =>
    http.get<LeakageRateOut>('/quality/leakage-rate', versionParams(versionIds)),

  getReflowRate: (versionIds?: string[]) =>
    http.get<BugReflowRateOut>('/quality/reflow-rate', versionParams(versionIds)),

  getDeveloperBugRate: (versionIds?: string[]) =>
    http.get<DeveloperBugRateItem[]>('/quality/developer-bug-rate', versionParams(versionIds)),

  getBugResponseTime: (versionIds?: string[]) =>
    http.get<BugResponseTimeOut>('/quality/bug-response-time', versionParams(versionIds)),

  getBugSourceTrend: (versionIds?: string[]) =>
    http.get<BugSourceTrendItem[]>('/quality/bug-source-trend', versionParams(versionIds)),
};
