import http from './http';
import type {
  Requirement,
  RequirementActivity,
  RequirementComment,
  RequirementNodeState,
  RequirementPriority,
  RequirementType,
} from '@/types/business';

export type RequirementNodeAction = 'start' | 'complete' | 'skip' | 'reopen' | 'reject';

export interface RequirementListPage {
  items: Requirement[];
  total: number;
  page: number;
  page_size: number;
}

/** 下拉/筛选器用轻量需求选项 */
export interface RequirementSelectOption {
  id: string;
  num: number;
  title: string;
  status: Requirement['status'];
  external_url?: string | null;
}

export interface ListRequirementOptionsParams {
  q?: string;
  version_id?: string;
  ids?: string;
  limit?: number;
}

export interface ListRequirementsParams {
  q?: string;
  version_id?: string;
  status?: string;
  priority?: string;
  req_type?: string;
  frontend_rd_id?: string;
  backend_rd_id?: string;
  pm_id?: string;
  qa_id?: string;
  developer_id?: string;
  dev_handoff_from?: string;
  dev_handoff_to?: string;
  page?: number;
  page_size?: number;
}

export function listRequirements(params?: ListRequirementsParams) {
  return http.get<RequirementListPage>('/requirements', { params });
}

export function listRequirementOptions(params?: ListRequirementOptionsParams) {
  return http.get<RequirementSelectOption[]>('/requirements/options', { params });
}

/** 便捷封装：返回 options 数组 */
export async function fetchRequirementOptions(
  params?: ListRequirementOptionsParams
): Promise<RequirementSelectOption[]> {
  const { data } = await listRequirementOptions(params);
  return data;
}

/** 打开详情/编辑时：最近 N 条 + 已关联 id 的标签 */
export function requirementOptionsParams(
  linkedIds: string[] | undefined,
  extra?: Omit<ListRequirementOptionsParams, 'ids'>
): ListRequirementOptionsParams {
  const ids = (linkedIds ?? []).filter(Boolean);
  return {
    limit: 100,
    ...extra,
    ...(ids.length ? { ids: ids.join(',') } : {}),
  };
}

/** 下拉选项等场景：分页拉取全部需求（数据量大时优先用 listRequirementOptions） */
export async function listAllRequirements(
  params?: Omit<ListRequirementsParams, 'page' | 'page_size'>
): Promise<Requirement[]> {
  const pageSize = 100;
  let page = 1;
  const items: Requirement[] = [];
  while (true) {
    const { data } = await listRequirements({ ...params, page, page_size: pageSize });
    items.push(...data.items);
    if (items.length >= data.total) break;
    page += 1;
  }
  return items;
}

export function getRequirement(id: string) {
  return http.get<Requirement>(`/requirements/${id}`);
}

export function createRequirement(data: {
  title: string;
  external_url?: string | null;
  version_id?: string | null;
  priority?: RequirementPriority;
  req_type?: RequirementType;
  frontend_rd_id?: string | null;
  backend_rd_id?: string | null;
  pm_id?: string | null;
  tech_owner_id?: string | null;
  qa_id?: string | null;
  designer_id?: string | null;
  role_assignee_ids?: Record<string, string[]>;
  selected_role_keys?: string[];
  enabled?: Record<string, boolean>;
  custom_fields?: Record<string, unknown>;
}) {
  return http.post<Requirement>('/requirements', data);
}

export function updateRequirement(
  id: string,
  data: {
    title?: string;
    external_url?: string | null;
    version_id?: string | null;
    priority?: RequirementPriority;
    req_type?: RequirementType;
    frontend_rd_id?: string | null;
    backend_rd_id?: string | null;
    pm_id?: string | null;
    tech_owner_id?: string | null;
    qa_id?: string | null;
    designer_id?: string | null;
    role_assignee_ids?: Record<string, string[]>;
    selected_role_keys?: string[];
    custom_fields?: Record<string, unknown>;
    expected_updated_at?: string;
  }
) {
  return http.patch<Requirement>(`/requirements/${id}`, data);
}

export function deleteRequirement(id: string) {
  return http.delete(`/requirements/${id}`);
}

export function requirementNodeAction(id: string, nodeKey: string, action: RequirementNodeAction) {
  return http.post<Requirement>(`/requirements/${id}/nodes/${nodeKey}`, { action });
}

export function closeRequirement(id: string) {
  return http.post<Requirement>(`/requirements/${id}/close`);
}

export function completeRequirement(id: string) {
  return http.post<Requirement>(`/requirements/${id}/complete`);
}

export function reopenClosedRequirement(id: string) {
  return http.post<Requirement>(`/requirements/${id}/reopen-closed`);
}

export function syncRequirementStatus(id: string) {
  return http.post<Requirement>(`/requirements/${id}/sync-status`);
}

export function listRequirementActivities(id: string) {
  return http.get<RequirementActivity[]>(`/requirements/${id}/activities`);
}

export function listRequirementComments(id: string) {
  return http.get<RequirementComment[]>(`/requirements/${id}/comments`);
}

export function createRequirementComment(id: string, body: string) {
  return http.post<RequirementComment>(`/requirements/${id}/comments`, { body });
}

export function nodeStateLabel(state: RequirementNodeState): string {
  const map: Record<RequirementNodeState, string> = {
    pending: '未开始',
    in_progress: '进行中',
    completed: '已完成',
    skipped: '已跳过',
  };
  return map[state] ?? state;
}
