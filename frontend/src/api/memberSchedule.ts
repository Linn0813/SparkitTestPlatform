import http from './http';
import type { MemberSchedule } from '@/types/business';

export function fetchMemberSchedule(start: string, end: string) {
  return http.get<MemberSchedule>('/dashboard/member-schedule', {
    params: { start, end },
  });
}
