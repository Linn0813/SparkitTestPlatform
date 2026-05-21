import type { TemplateField } from '@/types/business';

export interface BugListFilterState {
  status_key: string | null;
  reporter_id: string | null;
  follower_id: string | null;
  plan_version_id: string | null;
  found_version_id: string | null;
  requirement_id: string | null;
  plan_id: string | null;
  q: string;
  custom: Record<string, string | null>;
}

export function emptyBugListFilters(templateFields: TemplateField[] = []): BugListFilterState {
  const custom: Record<string, string | null> = {};
  for (const f of templateFields) {
    custom[f.id] = null;
  }
  return {
    status_key: null,
    reporter_id: null,
    follower_id: null,
    plan_version_id: null,
    found_version_id: null,
    requirement_id: null,
    plan_id: null,
    q: '',
    custom,
  };
}

export function syncCustomFilterKeys(
  state: BugListFilterState,
  templateFields: TemplateField[]
): BugListFilterState {
  const next = { ...state.custom };
  for (const f of templateFields) {
    if (!(f.id in next)) next[f.id] = null;
  }
  for (const id of Object.keys(next)) {
    if (!templateFields.some((f) => f.id === id)) delete next[id];
  }
  return { ...state, custom: next };
}
