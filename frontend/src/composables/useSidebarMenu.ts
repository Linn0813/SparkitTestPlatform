import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import type { MenuOption } from 'naive-ui';
import { SIDEBAR_MENU, flatMenuItems, findMenuLabel } from '@/config/sidebarMenu';
import { usePermissions } from '@/composables/usePermissions';
import { useContextStore } from '@/stores/context';

function buildRouteToMenuKey(): Map<string, string> {
  const map = new Map<string, string>();
  for (const item of flatMenuItems()) {
    map.set(item.key, item.key);
    for (const alias of item.activeAliases ?? []) {
      map.set(alias, item.key);
    }
  }
  map.set('setting-project-members', 'setting-project-config');
  map.set('setting-templates', 'setting-project-config');
  return map;
}

const routeToMenuKey = buildRouteToMenuKey();

export function useSidebarMenu() {
  const route = useRoute();
  const router = useRouter();
  const ctx = useContextStore();
  const { isSystemAdmin, isProjectMember } = usePermissions();

  const activeKey = computed(
    () => routeToMenuKey.get(route.name as string) ?? ''
  );

  const activeLabel = computed(() => {
    const name = route.name as string;
    return findMenuLabel(name) ?? findMenuLabel(activeKey.value);
  });

  function isVisible(key: string): boolean {
    const projectId = ctx.projectId;
    if (!projectId && !isSystemAdmin.value) return key === 'workbench';
    switch (key) {
      case 'workbench':
      case 'requirements':
      case 'member-schedule':
      case 'versions':
      case 'case-modules':
      case 'cases':
      case 'plans':
      case 'bugs':
      case 'setting-project-config':
      case 'setting-projects-manage':
      case 'setting-users':
        return isSystemAdmin.value || isProjectMember(projectId);
      default:
        return true;
    }
  }

  const menuOptions = computed<MenuOption[]>(() => {
    const result: MenuOption[] = [];
    for (const entry of SIDEBAR_MENU) {
      if ('type' in entry && entry.type === 'group') {
        const visibleChildren = entry.children
          .filter((c) => isVisible(c.key))
          .map((c) => ({ label: c.label, key: c.key }));
        if (visibleChildren.length > 0) {
          result.push({
            type: 'group',
            label: entry.label,
            key: entry.key,
            children: visibleChildren,
          });
        }
      } else {
        const item = entry as { label: string; key: string };
        if (isVisible(item.key)) {
          result.push({ label: item.label, key: item.key });
        }
      }
    }
    return result;
  });

  function onMenu(key: string) {
    router.push({ name: key });
  }

  return {
    menuOptions,
    activeKey,
    activeLabel,
    onMenu,
  };
}
