import { computed, ref, watch, type Ref } from 'vue';
import {
  allVisibleFilterKeys,
  buildFieldCatalog,
  clearCaseFilterValue,
  sanitizeVisibleFilterKeys,
  type FieldCatalogItem,
} from '@/schemas/entityFieldSchema';
import type { CaseListFilterState } from '@/composables/useCaseListFilters';
import type { TemplateField } from '@/types/business';

const STORAGE_PREFIX = 'sparkit:caseListFilterVisible:';

function storageKey(projectId: string): string {
  return `${STORAGE_PREFIX}${projectId}`;
}

function loadVisibleKeys(projectId: string): string[] | null {
  try {
    const raw = localStorage.getItem(storageKey(projectId));
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return null;
    return parsed.filter((k): k is string => typeof k === 'string');
  } catch {
    return null;
  }
}

function saveVisibleKeys(projectId: string, keys: string[]) {
  localStorage.setItem(storageKey(projectId), JSON.stringify(keys));
}

export function useCaseListFilterVisibility(
  projectId: Ref<string | null>,
  templateFields: Ref<TemplateField[]>,
  filters: Ref<CaseListFilterState>
) {
  const visibleKeys = ref<string[]>([]);

  const catalog = computed<FieldCatalogItem[]>(() =>
    buildFieldCatalog('functional_case', templateFields.value)
  );

  function hasStoredVisibility(pid: string | null): boolean {
    return pid != null && loadVisibleKeys(pid) !== null;
  }

  function defaultVisibleKeys(): string[] {
    return allVisibleFilterKeys(catalog.value);
  }

  function applyStoredVisibility(pid: string | null) {
    if (!pid) {
      visibleKeys.value = defaultVisibleKeys();
      return;
    }
    const stored = loadVisibleKeys(pid);
    visibleKeys.value = stored
      ? sanitizeVisibleFilterKeys(stored, catalog.value)
      : defaultVisibleKeys();
  }

  function sanitizeVisibleKeys() {
    if (!hasStoredVisibility(projectId.value)) {
      visibleKeys.value = defaultVisibleKeys();
      return;
    }
    const prev = new Set(visibleKeys.value);
    const next = sanitizeVisibleFilterKeys(visibleKeys.value, catalog.value);
    const removed = [...prev].filter((k) => !next.includes(k));
    visibleKeys.value = next;
    if (removed.length) {
      let state = filters.value;
      for (const key of removed) {
        state = clearCaseFilterValue(state, key);
      }
      filters.value = state;
    }
    if (projectId.value) {
      saveVisibleKeys(projectId.value, next);
    }
  }

  function setVisibleKeys(next: string[]) {
    const prev = new Set(visibleKeys.value);
    const sanitized = sanitizeVisibleFilterKeys(next, catalog.value);
    const removed = [...prev].filter((k) => !sanitized.includes(k));
    visibleKeys.value = sanitized;
    if (removed.length) {
      let state = filters.value;
      for (const key of removed) {
        state = clearCaseFilterValue(state, key);
      }
      filters.value = state;
    }
    if (projectId.value) {
      saveVisibleKeys(projectId.value, sanitized);
    }
  }

  watch(projectId, (pid) => applyStoredVisibility(pid), { immediate: true });

  watch(catalog, () => sanitizeVisibleKeys());

  return {
    visibleKeys,
    catalog,
    setVisibleKeys,
    sanitizeVisibleKeys,
  };
}
