import type { TemplateField } from '@/types/business';

export interface CaseListFilterState {
  module_id: string | null;
  include_submodules: boolean;
  q: string;
  priority: string | null;
  requirement_id: string | null;
  custom: Record<string, string | null>;
}

export function emptyCaseListFilters(templateFields: TemplateField[] = []): CaseListFilterState {
  const custom: Record<string, string | null> = {};
  for (const f of templateFields) {
    custom[f.id] = null;
  }
  return {
    module_id: null,
    include_submodules: false,
    q: '',
    priority: null,
    requirement_id: null,
    custom,
  };
}

export function syncCustomFilterKeys(
  state: CaseListFilterState,
  templateFields: TemplateField[]
): CaseListFilterState {
  const next = { ...state.custom };
  for (const f of templateFields) {
    if (!(f.id in next)) next[f.id] = null;
  }
  for (const id of Object.keys(next)) {
    if (!templateFields.some((f) => f.id === id)) delete next[id];
  }
  return { ...state, custom: next };
}
