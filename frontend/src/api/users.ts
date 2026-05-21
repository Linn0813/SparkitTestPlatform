import http from './http';
import type { User } from '@/types';

export function listUsers() {
  return http.get<User[]>('/users');
}

export function createUser(data: {
  email: string;
  name: string;
  password: string;
  is_active?: boolean;
  is_system_admin?: boolean;
}) {
  return http.post<User>('/users', data);
}

export function updateUser(
  id: string,
  data: Partial<{ name: string; is_active: boolean; is_system_admin: boolean; password: string }>
) {
  return http.patch<User>(`/users/${id}`, data);
}

export function updateMyProfile(data: { wecom_mobile?: string | null; wecom_userid?: string | null }) {
  return http.patch<User>('/users/me', data);
}
