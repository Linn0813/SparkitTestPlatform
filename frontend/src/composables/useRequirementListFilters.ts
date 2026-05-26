export interface RequirementListFilterState {
  q: string;
  status_keys: string[];
  priorities: string[];
  req_types: string[];
  version_id: string | null;
  developer_ids: string[];
  dev_handoff_from: string | null;
  dev_handoff_to: string | null;
}

export function emptyRequirementListFilters(): RequirementListFilterState {
  return {
    q: '',
    status_keys: [],
    priorities: [],
    req_types: [],
    version_id: null,
    developer_ids: [],
    dev_handoff_from: null,
    dev_handoff_to: null,
  };
}

export function clearRequirementFilterField(
  state: RequirementListFilterState,
  key: keyof RequirementListFilterState
): RequirementListFilterState {
  switch (key) {
    case 'q':
      return { ...state, q: '' };
    case 'status_keys':
      return { ...state, status_keys: [] };
    case 'priorities':
      return { ...state, priorities: [] };
    case 'req_types':
      return { ...state, req_types: [] };
    case 'version_id':
      return { ...state, version_id: null };
    case 'developer_ids':
      return { ...state, developer_ids: [] };
    case 'dev_handoff_from':
      return { ...state, dev_handoff_from: null };
    case 'dev_handoff_to':
      return { ...state, dev_handoff_to: null };
    default:
      return state;
  }
}
