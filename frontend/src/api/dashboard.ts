import http from './http';
import type { DashboardWorkbench } from '@/types/business';

export function fetchWorkbench(versionId?: string | null) {
  const params = versionId ? { version_id: versionId } : undefined;
  return http.get<DashboardWorkbench>('/dashboard', { params });
}
