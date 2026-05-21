import { type Ref, watch } from 'vue';

const PROJECT_KEY = 'sparkit_scope_project_id';

/** 记住设置页内选中的项目，避免刷新后回到顶栏上下文导致列表对不上 */
export function useSettingScope(projectId: Ref<string | null>) {
  function restoreProject(validIds: string[], fallback: string | null) {
    const saved = sessionStorage.getItem(PROJECT_KEY);
    projectId.value = saved && validIds.includes(saved) ? saved : fallback;
  }

  watch(projectId, (id) => {
    if (id) sessionStorage.setItem(PROJECT_KEY, id);
  });

  return { restoreProject };
}
