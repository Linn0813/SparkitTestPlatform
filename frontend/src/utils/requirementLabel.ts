import { requirementStatusLabel } from '@/constants/requirementStatus';
import type { Requirement, RequirementTodoBrief } from '@/types/business';

export function requirementOptionLabel(
  r: Pick<Requirement, 'num' | 'title' | 'status'>,
  opts?: { showNum?: boolean }
): string {
  const prefix = opts?.showNum === false ? '' : `#${r.num} · `;
  return `${prefix}${r.title}（${requirementStatusLabel(r.status)}）`;
}

export function requirementTodoDisplayLabel(r: RequirementTodoBrief): string {
  return `#${r.num} · ${r.title}`;
}
