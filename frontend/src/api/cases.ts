import http from './http';
import type { CaseModule, TestCase } from '@/types/business';

export function listModules() {
  return http.get<CaseModule[]>('/cases/modules');
}

export function createModule(data: { name: string; parent_id?: string | null; sort?: number }) {
  return http.post<CaseModule>('/cases/modules', data);
}

export function updateModule(id: string, data: Partial<CaseModule>) {
  return http.patch<CaseModule>(`/cases/modules/${id}`, data);
}

export function deleteModule(id: string) {
  return http.delete(`/cases/modules/${id}`);
}

export interface CaseListPage {
  items: TestCase[];
  total: number;
  page: number;
  page_size: number;
}

export interface ListCasesParams {
  module_id?: string;
  include_submodules?: boolean;
  requirement_id?: string;
  priority?: string;
  q?: string;
  custom_filters?: string;
  page?: number;
  page_size?: number;
}

export function listCases(params?: ListCasesParams) {
  const query: Record<string, string | boolean | number> = {
    page: params?.page ?? 1,
    page_size: params?.page_size ?? 20,
  };
  if (params?.module_id) {
    query.module_id = params.module_id;
    if (params.include_submodules) {
      query.include_submodules = true;
    }
  }
  if (params?.requirement_id) {
    query.requirement_id = params.requirement_id;
  }
  if (params?.priority) {
    query.priority = params.priority;
  }
  if (params?.q?.trim()) {
    query.q = params.q.trim();
  }
  if (params?.custom_filters) {
    query.custom_filters = params.custom_filters;
  }
  return http.get<CaseListPage>('/cases', { params: query });
}

export function getCase(id: string) {
  return http.get<TestCase>(`/cases/${id}`);
}

export function createCase(data: Partial<TestCase>) {
  return http.post<TestCase>('/cases', data);
}

export function updateCase(id: string, data: Partial<TestCase>) {
  return http.patch<TestCase>(`/cases/${id}`, data);
}

export function deleteCase(id: string) {
  return http.delete(`/cases/${id}`);
}

export interface CaseImportResult {
  created: number;
  errors: { row: number; message: string }[];
}

export async function downloadCaseImportTemplate() {
  const { data } = await http.get<Blob>('/cases/import/template', { responseType: 'blob' });
  const url = window.URL.createObjectURL(data);
  const link = document.createElement('a');
  link.href = url;
  link.download = '用例导入模板.xlsx';
  link.click();
  window.URL.revokeObjectURL(url);
}

export function importCases(file: File) {
  const form = new FormData();
  form.append('file', file);
  return http.post<CaseImportResult>('/cases/import', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  });
}
