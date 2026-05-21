import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import type { MenuOption } from 'naive-ui';
import { SIDEBAR_MAIN_ITEMS, findMenuLabel } from '@/config/sidebarMenu';

function buildRouteToMenuKey(): Map<string, string> {
  const map = new Map<string, string>();
  for (const item of SIDEBAR_MAIN_ITEMS) {
    map.set(item.key, item.key);
    for (const alias of item.activeAliases ?? []) {
      map.set(alias, item.key);
    }
  }
  return map;
}

const routeToMenuKey = buildRouteToMenuKey();

export function useSidebarMenu() {
  const route = useRoute();
  const router = useRouter();

  const activeKey = computed(
    () => routeToMenuKey.get(route.name as string) ?? ''
  );

  const activeLabel = computed(() => {
    const name = route.name as string;
    return findMenuLabel(name) ?? findMenuLabel(activeKey.value);
  });

  const menuOptions = computed<MenuOption[]>(() =>
    SIDEBAR_MAIN_ITEMS.map((item) => ({
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
