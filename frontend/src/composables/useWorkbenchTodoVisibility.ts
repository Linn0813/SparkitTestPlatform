import { computed, ref, watch, type Ref } from 'vue';

export const TODO_SECTION_KEYS = ['plan', 'requirement', 'fixed_bug', 'follower_bug'] as const;
export type TodoSectionKey = (typeof TODO_SECTION_KEYS)[number];

export const TODO_SECTION_LABELS: Record<TodoSectionKey, string> = {
  plan: '计划',
  requirement: '需求',
  fixed_bug: '已修复缺陷',
  follower_bug: '我跟进的缺陷',
};

const STORAGE_PREFIX = 'sparkit:workbenchTodoVisible:';

function storageKey(projectId: string): string {
  return `${STORAGE_PREFIX}${projectId}`;
}

function defaultVisibleSections(): Record<TodoSectionKey, boolean> {
  return {
    plan: true,
    requirement: true,
    fixed_bug: true,
    follower_bug: true,
  };
}

function loadVisibleSections(projectId: string): Record<TodoSectionKey, boolean> | null {
  try {
    const raw = localStorage.getItem(storageKey(projectId));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== 'object') return null;
    const next = defaultVisibleSections();
    for (const key of TODO_SECTION_KEYS) {
      const value = (parsed as Record<string, unknown>)[key];
      if (typeof value === 'boolean') next[key] = value;
    }
    return next;
  } catch {
    return null;
  }
}

function saveVisibleSections(projectId: string, sections: Record<TodoSectionKey, boolean>) {
  localStorage.setItem(storageKey(projectId), JSON.stringify(sections));
}

export function useWorkbenchTodoVisibility(projectId: Ref<string | null>) {
  const visibleSections = ref<Record<TodoSectionKey, boolean>>(defaultVisibleSections());

  function applyStoredVisibility(pid: string | null) {
    if (!pid) {
      visibleSections.value = defaultVisibleSections();
      return;
    }
    visibleSections.value = loadVisibleSections(pid) ?? defaultVisibleSections();
  }

  function setSectionVisible(key: TodoSectionKey, visible: boolean) {
    visibleSections.value = { ...visibleSections.value, [key]: visible };
    if (projectId.value) {
      saveVisibleSections(projectId.value, visibleSections.value);
    }
  }

  function setVisibleSections(next: Record<TodoSectionKey, boolean>) {
    visibleSections.value = { ...next };
    if (projectId.value) {
      saveVisibleSections(projectId.value, visibleSections.value);
    }
  }

  const showPlanTodo = computed(() => visibleSections.value.plan);
  const showReqTodo = computed(() => visibleSections.value.requirement);
  const showFixedBugTodo = computed(() => visibleSections.value.fixed_bug);
  const showFollowerBugTodo = computed(() => visibleSections.value.follower_bug);

  const hasVisibleSection = computed(
    () =>
      showPlanTodo.value ||
      showReqTodo.value ||
      showFixedBugTodo.value ||
      showFollowerBugTodo.value
  );

  watch(projectId, (pid) => applyStoredVisibility(pid), { immediate: true });

  return {
    visibleSections,
    showPlanTodo,
    showReqTodo,
    showFixedBugTodo,
    showFollowerBugTodo,
    hasVisibleSection,
    setSectionVisible,
    setVisibleSections,
  };
}
