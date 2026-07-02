export interface SidebarMenuItem {
  label: string;
  key: string;
  /** 详情页等路由也高亮该菜单项 */
  activeAliases?: string[];
}

export interface SidebarMenuGroup {
  type: 'group';
  label: string;
  key: string;
  children: SidebarMenuItem[];
}

export type SidebarMenuEntry = SidebarMenuItem | SidebarMenuGroup;

/** 侧栏主菜单（分组） */
export const SIDEBAR_MENU: SidebarMenuEntry[] = [
  { label: '工作台', key: 'workbench' },
  {
    type: 'group',
    label: '项目管理',
    key: 'group-project',
    children: [
      { label: '需求管理', key: 'requirements' },
      { label: '版本管理', key: 'versions' },
      { label: '缺陷管理', key: 'bugs' },
      { label: '人员排期', key: 'member-schedule' },
    ],
  },
  {
    type: 'group',
    label: '测试管理',
    key: 'group-testing',
    children: [
      { label: '模块管理', key: 'case-modules' },
      { label: '测试用例', key: 'cases' },
      { label: '测试计划', key: 'plans', activeAliases: ['plan-detail'] },
      { label: 'UI 自动化', key: 'ui-automation', activeAliases: ['ui-run-detail'] },
    ],
  },
  {
    type: 'group',
    label: '系统设置',
    key: 'group-admin',
    children: [
      { label: '项目配置', key: 'setting-project-config' },
      { label: '项目管理', key: 'setting-projects-manage' },
      { label: '系统用户', key: 'setting-users' },
    ],
  },
];

/** 兼容旧逻辑：展开所有叶子节点 */
export function flatMenuItems(): SidebarMenuItem[] {
  const items: SidebarMenuItem[] = [];
  for (const entry of SIDEBAR_MENU) {
    if ('type' in entry && entry.type === 'group') {
      items.push(...entry.children);
    } else {
      items.push(entry as SidebarMenuItem);
    }
  }
  return items;
}

// 兼容旧代码引用
export const SIDEBAR_MAIN_ITEMS = flatMenuItems();

/** 用户菜单：管理与配置（按权限显示） */
export const USER_ADMIN_MENU_ITEMS: SidebarMenuItem[] = [
  { label: '项目管理', key: 'setting-projects-manage' },
  { label: '系统用户', key: 'setting-users' },
];

export function allNavItems(): SidebarMenuItem[] {
  return [...flatMenuItems(), ...USER_ADMIN_MENU_ITEMS];
}

export function findMenuLabel(menuKey: string): string | undefined {
  return allNavItems().find((i) => i.key === menuKey)?.label;
}
