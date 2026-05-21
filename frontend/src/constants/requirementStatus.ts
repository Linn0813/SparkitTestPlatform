export const REQUIREMENT_STATUS_OPTIONS = [
  { label: '未转测', value: 'not_tested' },
  { label: '测试中', value: 'testing' },
  { label: '已验收', value: 'accepted' },
] as const;

export function requirementStatusLabel(key: string): string {
  return REQUIREMENT_STATUS_OPTIONS.find((o) => o.value === key)?.label ?? key;
}
