import http from './http';
import type { BugActivity, BugAttachment, BugComment, BugItem } from '@/types/business';

export interface BugListPage {
  items: BugItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface ListBugsParams {
  /** 逗号分隔多值，同字段 OR 匹配；兼容单值 */
  status_key?: string;
  /** 逗号分隔多值，排除对应状态 */
  exclude_status_key?: string;
  assignee_id?: string;
  /** 逗号分隔多值，同字段 OR 匹配 */
  reporter_id?: string;
  /** 逗号分隔多值，同字段 OR 匹配；含 __empty__ 表示无跟进人 */
  follower_id?: string;
  /** 逗号分隔多值，同字段 OR 匹配；含 __empty__ 表示未设置版本 */
  plan_version_id?: string;
  found_version_id?: string;
  /** 逗号分隔多值，同字段 OR 匹配；含 __empty__ 表示未关联需求 */
  requirement_id?: string;
  /** 逗号分隔多值，同字段 OR 匹配；含 __empty__ 表示未关联计划 */
  plan_id?: string;
  q?: string;
  /** 创建日期 YYYY-MM-DD，按 UTC+8 日历日筛选 */
  created_date?: string;
  /** severity=按严重程度（致命优先） */
  sort_by?: 'severity';
  /** JSON: { fieldId: value | value[] | __empty__ }，多值 OR 匹配 */
  custom_filters?: string;
  page?: number;
  page_size?: number;
}

export function listBugs(params?: ListBugsParams) {
  return http.get<BugListPage>('/bugs', { params });
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

export interface BugImportResult {
  created: number;
  errors: { row: number; message: string }[];
}

export async function downloadBugImportTemplate() {
  const { data } = await http.get<Blob>('/bugs/import/template', { responseType: 'blob' });
  const url = window.URL.createObjectURL(data);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'bug_import_template.xlsx';
  link.click();
  window.URL.revokeObjectURL(url);
}

export function importBugs(file: File) {
  const form = new FormData();
  form.append('file', file);
  return http.post<BugImportResult>('/bugs/import', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  });
}

export function uploadAttachment(bugId: string, file: File) {
  const form = new FormData();
  form.append('file', file);
  return http.post<BugAttachment>(`/bugs/${bugId}/attachments`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
}

export function listBugAttachments(bugId: string) {
  return http.get<BugAttachment[]>(`/bugs/${bugId}/attachments`);
}

export function deleteBugAttachment(bugId: string, attachmentId: string) {
  return http.delete(`/bugs/${bugId}/attachments/${attachmentId}`);
}
