import type { TemplateField } from '@/types/business';

export interface BugListFilterState {
  status_keys: string[];
  reporter_ids: string[];
  follower_ids: string[];
  plan_version_ids: string[];
  found_version_ids: string[];
  requirement_ids: string[];
  plan_ids: string[];
  q: string;
  custom: Record<string, string[]>;
}

export function emptyBugListFilters(templateFields: TemplateField[] = []): BugListFilterState {
  const custom: Record<string, string[]> = {};
  for (const f of templateFields) {
    custom[f.id] = [];
  }
  return {
    status_keys: [],
    reporter_ids: [],
    follower_ids: [],
    plan_version_ids: [],
    found_version_ids: [],
    requirement_ids: [],
    plan_ids: [],
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
    if (!(f.id in next)) next[f.id] = [];
  }
  for (const id of Object.keys(next)) {
    if (!templateFields.some((f) => f.id === id)) delete next[id];
  }
  return { ...state, custom: next };
}
