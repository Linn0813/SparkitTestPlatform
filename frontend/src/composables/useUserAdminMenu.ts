import type { DropdownOption } from 'naive-ui';
import { USER_ADMIN_MENU_ITEMS } from '@/config/sidebarMenu';

/** 顶栏用户下拉中的管理与配置项（所有登录用户可见，写权限由页面内控制） */
export function useUserAdminMenu() {
  function buildUserMenuOptions(): DropdownOption[] {
    const options: DropdownOption[] = [{ label: '我的资料', key: 'profile' }];
    options.push({ type: 'divider', key: 'admin-divider' });
    for (const item of USER_ADMIN_MENU_ITEMS) {
      options.push({ label: item.label, key: item.key });
    }
    options.push({ type: 'divider', key: 'logout-divider' });
    options.push({ label: '退出登录', key: 'logout' });
    return options;
  }

  return { buildUserMenuOptions, hasAdminMenu: true };
}
