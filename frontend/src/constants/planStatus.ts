import type { TagProps } from 'naive-ui';

export const PLAN_STATUS_OPTIONS = [
  { label: '未开始', value: 'draft' },
  { label: '进行中', value: 'active' },
  { label: '已归档', value: 'archived' },
];

export const PLAN_RESULT_OPTIONS = [
  { label: '未执行', value: 'not_run' },
  { label: '通过', value: 'pass' },
  { label: '失败', value: 'fail' },
  { label: '阻塞', value: 'block' },
  { label: '跳过', value: 'skip' },
];

export type PlanStatusValue = 'draft' | 'active' | 'archived';

export function planStatusLabel(status: string | null | undefined): string {
  return PLAN_STATUS_OPTIONS.find((o) => o.value === status)?.label ?? status ?? '—';
}

export function planStatusTagType(status: string | null | undefined): TagProps['type'] {
  if (status === 'active') return 'info';
  if (status === 'archived') return 'default';
  return 'warning';
}

export function isPlanArchived(status: string | null | undefined): boolean {
  return status === 'archived';
}

export function planResultLabel(result: string | null | undefined): string {
  return PLAN_RESULT_OPTIONS.find((o) => o.value === result)?.label ?? result ?? '—';
}

export function planResultTagType(result: string | null | undefined): TagProps['type'] {
  if (result === 'pass') return 'success';
  if (result === 'fail') return 'error';
  if (result === 'block') return 'warning';
  return 'default';
}

/** 列表用：无已执行用例时无通过率 */
export function formatPlanPassRate(plan: {
  case_total?: number;
  not_run_count?: number;
  pass_rate?: number;
}): string {
  const total = plan.case_total ?? 0;
  const notRun = plan.not_run_count ?? 0;
  const executed = total - notRun;
  if (!executed) return '—';
  return `${plan.pass_rate ?? 0}%`;
}

export function formatPlanProgress(plan: {
  case_total?: number;
  pass_count?: number;
  not_run_count?: number;
}): string {
  const total = plan.case_total ?? 0;
  if (!total) return '0/0';
  return `${plan.pass_count ?? 0}/${total}`;
}
