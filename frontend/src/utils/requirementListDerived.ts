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

const TESTING_NODE_KEYS = ['req_test', 'product_experience', 'ui_restoration'] as const;
const TESTING_ROLE_KEYS = ['qa'];
const DEVELOPMENT_ROLE_KEYS = ['frontend_rd', 'backend_rd', 'tech_owner'];

function isTestingNode(n: { node_key: string; role_keys?: string[] }): boolean {
  if ((TESTING_NODE_KEYS as readonly string[]).includes(n.node_key)) return true;
  if (n.role_keys?.some((r) => TESTING_ROLE_KEYS.includes(r))) return true;
  return false;
}

function isDevelopmentNode(n: { node_key: string; role_keys?: string[] }): boolean {
  if (DEVELOPMENT_NODE_KEYS.includes(n.node_key as (typeof DEVELOPMENT_NODE_KEYS)[number])) return true;
  if (n.role_keys?.some((r) => DEVELOPMENT_ROLE_KEYS.includes(r))) return true;
  return false;
}

/** 预计完成：优先用后端计算的 estimated_completion_date，降级才自己推算 */
export function formatEstimatedCompletion(req: Requirement): string {
  if (req.estimated_completion_date) return formatDateOnly(req.estimated_completion_date);

  // 降级：自己推算（详情页场景，后端没有返回 estimated_completion_date）
  const testingNodeEnds = (req.nodes ?? [])
    .filter((n) => n.enabled !== false && n.planned_schedule_end && isTestingNode(n))
    .map((n) => n.planned_schedule_end as string);
  if (testingNodeEnds.length) return formatDateOnly(testingNodeEnds.sort().at(-1)!);

  const testingTaskEnds = (req.node_tasks ?? [])
    .filter((t) => isTestingNode({ node_key: t.node_key, role_keys: [] }) && t.scheduled_end)
    .map((t) => t.scheduled_end as string);
  if (testingTaskEnds.length) return formatDateOnly(testingTaskEnds.sort().at(-1)!);

  if (req.dev_handoff_date) return formatDateOnly(req.dev_handoff_date);
  const devEnds = (req.nodes ?? [])
    .filter((n) => n.enabled !== false && n.planned_schedule_end && isDevelopmentNode(n))
    .map((n) => n.planned_schedule_end as string);
  if (!devEnds.length) return '—';
  return formatDateOnly(devEnds.sort().at(-1)!);
}
