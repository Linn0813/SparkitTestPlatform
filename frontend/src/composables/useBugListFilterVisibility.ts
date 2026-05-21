import { computed, ref, watch, type Ref } from 'vue';
import {
  buildFieldCatalog,
  clearBugFilterValue,
  DEFAULT_BUG_FILTER_VISIBLE_KEYS,
  sanitizeVisibleFilterKeys,
  type FieldCatalogItem,
} from '@/schemas/entityFieldSchema';
import type { BugListFilterState } from '@/composables/useBugListFilters';
import type { TemplateField } from '@/types/business';

const STORAGE_PREFIX = 'sparkit:bugListFilterVisible:';

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

export function useBugListFilterVisibility(
  projectId: Ref<string | null>,
  templateFields: Ref<TemplateField[]>,
  filters: Ref<BugListFilterState>
) {
  const visibleKeys = ref<string[]>([...DEFAULT_BUG_FILTER_VISIBLE_KEYS]);

  const catalog = computed<FieldCatalogItem[]>(() =>
    buildFieldCatalog('bug', templateFields.value)
  );

  function applyStoredVisibility(pid: string | null) {
    if (!pid) {
      visibleKeys.value = [...DEFAULT_BUG_FILTER_VISIBLE_KEYS];
      return;
    }
    const stored = loadVisibleKeys(pid);
    const base = stored ?? [...DEFAULT_BUG_FILTER_VISIBLE_KEYS];
    visibleKeys.value = sanitizeVisibleFilterKeys(base, catalog.value);
  }

  function sanitizeVisibleKeys() {
    const prev = new Set(visibleKeys.value);
    const next = sanitizeVisibleFilterKeys(visibleKeys.value, catalog.value);
    const removed = [...prev].filter((k) => !next.includes(k));
    visibleKeys.value = next;
    if (removed.length) {
      let state = filters.value;
      for (const key of removed) {
        state = clearBugFilterValue(state, key);
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
        state = clearBugFilterValue(state, key);
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
