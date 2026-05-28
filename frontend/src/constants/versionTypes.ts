import type { VersionType } from '@/types/business';

export const VERSION_TYPE_LABELS: Record<VersionType, string> = {
  app_release: '应用发版',
  hotfix: '热修',
};

export const VERSION_TYPE_OPTIONS = (Object.keys(VERSION_TYPE_LABELS) as VersionType[]).map(
  (value) => ({
    label: VERSION_TYPE_LABELS[value],
    value,
  })
);

export function versionTypeLabel(type: VersionType | string): string {
  return VERSION_TYPE_LABELS[type as VersionType] ?? type;
}
