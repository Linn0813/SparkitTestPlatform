export const REQUIREMENT_PRIORITY_OPTIONS = [
  { label: 'P00', value: 'p00' },
  { label: 'P0', value: 'p0' },
  { label: 'P1', value: 'p1' },
] as const;

export function requirementPriorityLabel(key: string): string {
  return REQUIREMENT_PRIORITY_OPTIONS.find((o) => o.value === key)?.label ?? key;
}
