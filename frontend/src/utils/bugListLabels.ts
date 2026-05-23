import type { TagProps } from 'naive-ui';
import type { BugItem } from '@/types/business';
import {
  bugFollowerTagType,
  bugPlanVersionTagType,
  bugSeverityTagType,
  bugSourceTagType,
} from '@/constants/bugStatus';
import { formatVersionDisplay } from '@/utils/versionLabel';

export type BugListColumn = { label: string; value: string; type?: TagProps['type'] };

function fieldOrDash(value: unknown): string {
  if (value == null || value === '') return '—';
  return String(value);
}

export function bugScheduleColumns(b: BugItem): BugListColumn[] {
  const source = fieldOrDash(b.custom_fields?.field_source);
  const severity = fieldOrDash(b.custom_fields?.field_severity);
  const followers = b.followers?.map((f) => f.name).filter(Boolean).join('、') || '—';
  return [
    { label: '来源', value: source, type: bugSourceTagType(source) },
    { label: '跟进', value: followers, type: bugFollowerTagType(followers) },
    { label: '严重', value: severity, type: bugSeverityTagType(severity) },
  ];
}

export function bugPlanVersionColumn(b: BugItem): BugListColumn {
  const value = b.plan_version ? formatVersionDisplay(b.plan_version) : '—';
  return { label: '规划', value, type: bugPlanVersionTagType(value) };
}

export function bugFollowerTodoColumns(b: BugItem): BugListColumn[] {
  return [bugPlanVersionColumn(b)];
}
