import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import type { MenuOption } from 'naive-ui';
import { SIDEBAR_MAIN_ITEMS, findMenuLabel } from '@/config/sidebarMenu';
import { usePermissions } from '@/composables/usePermissions';
import { useContextStore } from '@/stores/context';

function buildRouteToMenuKey(): Map<string, string> {
  const map = new Map<string, string>();
  for (const item of SIDEBAR_MAIN_ITEMS) {
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
  const {
    isSystemAdmin,
    isProjectMember,
    canAccessCasesModule,
    canAccessBugsModule,
    canManageProjectConfig,
  } = usePermissions();

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
      case 'versions':
        return isSystemAdmin.value || isProjectMember(projectId);
      case 'case-modules':
      case 'cases':
      case 'plans':
        return canAccessCasesModule(projectId);
      case 'bugs':
        return canAccessBugsModule(projectId);
      case 'setting-project-config':
        return canManageProjectConfig(projectId);
      default:
        return true;
    }
  }

  const menuOptions = computed<MenuOption[]>(() =>
    SIDEBAR_MAIN_ITEMS.filter((item) => isVisible(item.key)).map((item) => ({
      label: item.label,
      key: item.key,
    }))
  );

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
