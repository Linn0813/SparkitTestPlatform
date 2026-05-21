import http from './http';
import type { MeResponse, TokenResponse } from '@/types';

export function login(email: string, password: string) {
  return http.post<TokenResponse>('/auth/login', { email, password }, { skipGlobalLoading: true });
}

export function fetchMe() {
  return http.get<MeResponse>('/auth/me');
}

export function switchContext(projectId?: string | null) {
  return http.post<MeResponse>('/auth/switch-context', {
    project_id: projectId ?? undefined,
  });
}

export function changePassword(oldPassword: string, newPassword: string) {
  return http.post('/auth/change-password', {
    old_password: oldPassword,
    new_password: newPassword,
  });
}
