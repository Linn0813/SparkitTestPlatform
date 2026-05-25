import { computed } from 'vue';
import type { DropdownOption } from 'naive-ui';
import { USER_ADMIN_MENU_ITEMS } from '@/config/sidebarMenu';
import { usePermissions } from '@/composables/usePermissions';

/** 顶栏用户下拉中的管理与配置项（按角色过滤） */
export function useUserAdminMenu() {
  const { isSystemAdmin } = usePermissions();

  const visibleAdminKeys = computed(() => {
    const keys: string[] = [];
    for (const item of USER_ADMIN_MENU_ITEMS) {
      if (item.key === 'setting-projects-manage' || item.key === 'setting-users') {
        if (isSystemAdmin.value) keys.push(item.key);
      }
    }
    return keys;
  });

  const hasAdminMenu = computed(() => visibleAdminKeys.value.length > 0);

  function buildUserMenuOptions(): DropdownOption[] {
    const options: DropdownOption[] = [{ label: '我的资料', key: 'profile' }];
    if (hasAdminMenu.value) {
      options.push({ type: 'divider', key: 'admin-divider' });
      for (const item of USER_ADMIN_MENU_ITEMS) {
        if (visibleAdminKeys.value.includes(item.key)) {
          options.push({ label: item.label, key: item.key });
        }
      }
    }
    options.push({ type: 'divider', key: 'logout-divider' });
    options.push({ label: '退出登录', key: 'logout' });
    return options;
  }

  return { buildUserMenuOptions, hasAdminMenu };
}
