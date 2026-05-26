import type { TagProps } from 'naive-ui';

export const REQUIREMENT_PRIORITY_OPTIONS = [
  { label: 'P00', value: 'p00' },
  { label: 'P0', value: 'p0' },
  { label: 'P1', value: 'p1' },
] as const;

export function requirementPriorityLabel(key: string): string {
  return REQUIREMENT_PRIORITY_OPTIONS.find((o) => o.value === key)?.label ?? key;
}

/** 需求优先级 Tag 颜色：P00 最高，依次减弱 */
export function requirementPriorityTagType(key: string): TagProps['type'] {
  if (key === 'p00') return 'error';
  if (key === 'p0') return 'warning';
  if (key === 'p1') return 'info';
  return 'default';
}
