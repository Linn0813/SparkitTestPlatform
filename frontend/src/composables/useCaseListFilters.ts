import type { TemplateField } from '@/types/business';

export interface CaseListFilterState {
  module_id: string | null;
  include_submodules: boolean;
  q: string;
  priorities: string[];
  requirement_ids: string[];
  custom: Record<string, string[]>;
}

export function emptyCaseListFilters(templateFields: TemplateField[] = []): CaseListFilterState {
  const custom: Record<string, string[]> = {};
  for (const f of templateFields) {
    custom[f.id] = [];
  }
  return {
    module_id: null,
    include_submodules: false,
    q: '',
    priorities: [],
    requirement_ids: [],
    custom,
  };
}

export function syncCustomFilterKeys(
  state: CaseListFilterState,
  templateFields: TemplateField[]
): CaseListFilterState {
  const next = { ...state.custom };
  for (const f of templateFields) {
    if (!(f.id in next)) next[f.id] = [];
  }
  for (const id of Object.keys(next)) {
    if (!templateFields.some((f) => f.id === id)) delete next[id];
  }
  return { ...state, custom: next };
}
