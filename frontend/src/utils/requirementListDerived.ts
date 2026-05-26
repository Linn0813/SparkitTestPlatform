import { DEVELOPMENT_NODE_KEYS } from '@/constants/requirementNodes';
import type { Requirement } from '@/types/business';
import { formatDateOnly } from '@/utils/formatDateOnly';

export function formatRequirementDevelopers(req: Requirement): string {
  const names = (req.developers ?? []).map((d) => d.name).filter(Boolean);
  if (names.length) return names.join('、');
  return '—';
}

export function formatDevHandoffDate(req: Requirement): string {
  if (req.dev_handoff_date) return formatDateOnly(req.dev_handoff_date);
  const ends = (req.nodes ?? [])
    .filter((n) => DEVELOPMENT_NODE_KEYS.includes(n.node_key as (typeof DEVELOPMENT_NODE_KEYS)[number]))
    .filter((n) => n.enabled !== false && n.planned_schedule_end)
    .map((n) => n.planned_schedule_end as string);
  if (!ends.length) return '—';
  return formatDateOnly(ends.sort().at(-1)!);
}
