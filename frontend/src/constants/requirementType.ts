export const REQUIREMENT_TYPE_OPTIONS = [
  { label: '需求开发', value: 'feature' },
  { label: '技术优化', value: 'tech_optimization' },
] as const;

export function requirementTypeLabel(key: string): string {
  return REQUIREMENT_TYPE_OPTIONS.find((o) => o.value === key)?.label ?? key;
}
