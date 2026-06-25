import type { TagProps } from 'naive-ui';

export const REQUIREMENT_STATUS_OPTIONS = [
  { label: '草稿', value: 'draft' },
  { label: '待评审', value: 'pending_review' },
  { label: '设计中', value: 'designing' },
  { label: '开发中', value: 'developing' },
  { label: '测试中', value: 'testing' },
  { label: '待发版', value: 'pending_release' },
  { label: '已发版', value: 'released' },
  { label: '已完成', value: 'completed' },
  { label: '已关闭', value: 'closed' },
] as const;

export function requirementStatusLabel(key: string): string {
  return REQUIREMENT_STATUS_OPTIONS.find((o) => o.value === key)?.label ?? key;
}

export function requirementStatusTagType(key: string): TagProps['type'] {
  if (key === 'released' || key === 'completed') return 'success';
  if (key === 'closed') return 'default';
  if (key === 'testing' || key === 'pending_release') return 'info';
  if (key === 'developing' || key === 'designing') return 'warning';
  if (key === 'pending_review') return 'warning';
  return 'default';
}
