import type { TagProps } from 'naive-ui';
import type { BugStatusDef } from '@/types/business';

export function bugStatusTagType(
  statusKey: string | null | undefined,
  statuses: Pick<BugStatusDef, 'key' | 'is_terminal'>[] = []
): TagProps['type'] {
  if (!statusKey) return 'default';
  const row = statuses.find((s) => s.key === statusKey);
  if (row?.is_terminal) return 'success';
  if (statusKey === 'fixed') return 'success';
  if (statusKey === 'rejected') return 'error';
  if (statusKey === 'pending_confirm' || statusKey === 'new') return 'warning';
  if (statusKey === 'in_progress' || statusKey === 'processing') return 'info';
  if (statusKey === 'suspended') return 'default';
  return 'default';
}

export function bugSeverityTagType(severity: string | null | undefined): TagProps['type'] {
  if (!severity || severity === '—') return 'default';
  if (severity === '致命') return 'error';
  if (severity === '严重') return 'warning';
  return 'default';
}

export function bugSourceTagType(source: string | null | undefined): TagProps['type'] {
  if (!source || source === '—') return 'default';
  if (source === '线上反馈') return 'error';
  if (source === '内部体验') return 'info';
  if (source === '需求测试') return 'success';
  return 'default';
}

export function bugFollowerTagType(value: string): TagProps['type'] {
  return value === '—' ? 'default' : 'info';
}

export function bugPlanVersionTagType(value: string): TagProps['type'] {
  return value === '—' ? 'default' : 'info';
}
