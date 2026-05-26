import type { RouteLocationRaw } from 'vue-router';
import {
  MEMBER_FOLLOWER_TODO_STATUS_QUERY,
  TESTER_FIXED_BUG_STATUS_QUERY,
  TESTER_PLAN_TODO_STATUS_QUERY,
  TESTER_TODO_ALL_REQUIREMENT_STATUS_QUERY,
} from '@/constants/dashboardTodo';
import { FILTER_EMPTY_VALUE } from '@/schemas/entityFieldSchema';
import type { RequirementTodoBrief } from '@/types/business';

function compactQuery(entries: Record<string, string | undefined>): Record<string, string> {
  const q: Record<string, string> = {};
  for (const [k, v] of Object.entries(entries)) {
    if (v != null && v !== '') q[k] = v;
  }
  return q;
}

export function requirementListLink(query: {
  status?: string;
  version_id?: string;
  id?: string;
}): RouteLocationRaw {
  return {
    name: 'requirements',
    query: compactQuery({
      status: query.status,
      version_id: query.version_id,
      id: query.id,
    }),
  };
}

export function bugListLink(query: Record<string, string | undefined>): RouteLocationRaw {
  return { name: 'bugs', query: compactQuery(query) };
}

export function planListLink(query?: { status?: string; version_id?: string }): RouteLocationRaw {
  return {
    name: 'plans',
    query: compactQuery({
      status: query?.status,
      version_id: query?.version_id,
    }),
  };
}

export function requirementTodoRowLink(r: RequirementTodoBrief): RouteLocationRaw {
  return requirementListLink({
    status: r.status,
    version_id: r.version?.id,
  });
}

export function requirementTodoViewAllLink(): RouteLocationRaw {
  return requirementListLink({ status: TESTER_TODO_ALL_REQUIREMENT_STATUS_QUERY });
}

export function planTodoViewAllLink(): RouteLocationRaw {
  return planListLink({ status: TESTER_PLAN_TODO_STATUS_QUERY });
}

export function fixedBugsTodoViewAllLink(): RouteLocationRaw {
  return bugListLink({ status_key: TESTER_FIXED_BUG_STATUS_QUERY });
}

export function memberFollowerTodoViewAllLink(followerUserId: string): RouteLocationRaw {
  return bugListLink({
    follower_id: followerUserId,
    status_key: MEMBER_FOLLOWER_TODO_STATUS_QUERY,
  });
}

export function versionFocusRequirementLink(
  versionId: string,
  statusKey: string
): RouteLocationRaw {
  return requirementListLink({ version_id: versionId, status: statusKey });
}

export function versionFocusBugLink(versionId: string, statusKey: string): RouteLocationRaw {
  return bugListLink({
    plan_version_id: versionId,
    status_key: statusKey,
  });
}

export function bugOverviewChartCellLink(
  statusKey: string,
  versionId: string | null
): RouteLocationRaw {
  return bugListLink({
    status_key: statusKey,
    plan_version_id: versionId ?? FILTER_EMPTY_VALUE,
  });
}

export function bugFollowerChartCellLink(
  followerId: string | null,
  versionId: string | null
): RouteLocationRaw {
  return bugListLink({
    follower_id: followerId ?? FILTER_EMPTY_VALUE,
    plan_version_id: versionId ?? FILTER_EMPTY_VALUE,
    status_key: MEMBER_FOLLOWER_TODO_STATUS_QUERY,
  });
}
