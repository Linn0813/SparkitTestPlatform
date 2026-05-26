export interface RequirementListFilterState {
  q: string;
  status_keys: string[];
  priorities: string[];
  req_types: string[];
  version_id: string | null;
}

export function emptyRequirementListFilters(): RequirementListFilterState {
  return {
    q: '',
    status_keys: [],
    priorities: [],
    req_types: [],
    version_id: null,
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
    default:
      return state;
  }
}
