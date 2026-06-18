import http from './http';
import type {
  MobileApp,
  UIElement,
  UIRunner,
  UITestCase,
  UITestCaseListItem,
  UITestRun,
  UITestRunListItem,
} from '@/types/business';

// 元素库
export function listElements(params?: { platform?: string }) {
  return http.get<UIElement[]>('/ui-automation/elements', { params });
}

export function createElement(data: Partial<UIElement>) {
  return http.post<UIElement>('/ui-automation/elements', data);
}

export function updateElement(id: string, data: Partial<UIElement>) {
  return http.patch<UIElement>(`/ui-automation/elements/${id}`, data);
}

export function deleteElement(id: string) {
  return http.delete(`/ui-automation/elements/${id}`);
}

export function uploadElementScreenshot(id: string, file: File) {
  const form = new FormData();
  form.append('file', file);
  return http.post<UIElement>(`/ui-automation/elements/${id}/screenshot`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
}

export function deleteElementScreenshot(id: string) {
  return http.delete(`/ui-automation/elements/${id}/screenshot`);
}

// 用例
export function listUICases(params?: { platform?: string }) {
  return http.get<UITestCaseListItem[]>('/ui-automation/cases', { params });
}

export function getUICase(id: string) {
  return http.get<UITestCase>(`/ui-automation/cases/${id}`);
}

export function createUICase(data: Partial<UITestCase>) {
  return http.post<UITestCase>('/ui-automation/cases', data);
}

export function updateUICase(id: string, data: Partial<UITestCase>) {
  return http.patch<UITestCase>(`/ui-automation/cases/${id}`, data);
}

export function deleteUICase(id: string) {
  return http.delete(`/ui-automation/cases/${id}`);
}

// App 包
export function listMobileApps(params?: { platform?: string }) {
  return http.get<MobileApp[]>('/ui-automation/apps', { params });
}

export function uploadMobileApp(platform: string, version: string, file: File) {
  const form = new FormData();
  form.append('file', file);
  return http.post<MobileApp>('/ui-automation/apps', form, {
    params: { platform, version },
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 300_000,
  });
}

export function deleteMobileApp(id: string) {
  return http.delete(`/ui-automation/apps/${id}`);
}

// Runner
export function listRunners() {
  return http.get<UIRunner[]>('/ui-automation/runners');
}

export function createRunner(data: { name: string; platform: string }) {
  return http.post<UIRunner & { token: string }>('/ui-automation/runners', data);
}

export function deleteRunner(id: string) {
  return http.delete(`/ui-automation/runners/${id}`);
}

// 执行
export function triggerRun(data: { case_id: string; app_id: string }) {
  return http.post<UITestRun>('/ui-automation/runs', data);
}

export function listRuns(params?: { case_id?: string }) {
  return http.get<UITestRunListItem[]>('/ui-automation/runs', { params });
}

export function getRun(id: string) {
  return http.get<UITestRun>(`/ui-automation/runs/${id}`);
}
