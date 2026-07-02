import type { DropdownOption } from 'naive-ui';

/** 顶栏用户下拉（只保留个人操作，管理入口已移至左侧导航栏） */
export function useUserAdminMenu() {
  function buildUserMenuOptions(): DropdownOption[] {
    return [
      { label: '我的资料', key: 'profile' },
      { type: 'divider', key: 'logout-divider' },
      { label: '退出登录', key: 'logout' },
    ];
  }

  return { buildUserMenuOptions, hasAdminMenu: false };
}
