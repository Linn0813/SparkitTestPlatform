import { requirementStatusLabel } from '@/constants/requirementStatus';
import type { Requirement, RequirementTodoBrief } from '@/types/business';

export function requirementOptionLabel(
  r: Pick<Requirement, 'num' | 'title' | 'status'>
): string {
  return `#${r.num} · ${r.title}（${requirementStatusLabel(r.status)}）`;
}

export function requirementTodoDisplayLabel(r: RequirementTodoBrief): string {
  return `#${r.num} · ${r.title}`;
}
