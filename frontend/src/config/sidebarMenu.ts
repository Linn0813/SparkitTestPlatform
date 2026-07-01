export interface SidebarMenuItem {
  label: string;
  key: string;
  /** 详情页等路由也高亮该菜单项 */
  activeAliases?: string[];
}

/** 侧栏：日常测试工作流（扁平，无分组标题） */
export const SIDEBAR_MAIN_ITEMS: SidebarMenuItem[] = [
  { label: '工作台', key: 'workbench' },
  { label: '需求管理', key: 'requirements' },
  { label: '人员排期', key: 'member-schedule' },
  { label: '版本管理', key: 'versions' },
  { label: '模块管理', key: 'case-modules' },
  { label: '测试用例', key: 'cases' },
  { label: '测试计划', key: 'plans', activeAliases: ['plan-detail'] },
  { label: 'UI 自动化', key: 'ui-automation', activeAliases: ['ui-run-detail'] },
  { label: '质量指标', key: 'quality' },
  { label: '缺陷管理', key: 'bugs' },
  { label: '项目配置', key: 'setting-project-config' },
];

/** 用户菜单：管理与配置（按权限显示） */
export const USER_ADMIN_MENU_ITEMS: SidebarMenuItem[] = [
  { label: '项目管理', key: 'setting-projects-manage' },
  { label: '系统用户', key: 'setting-users' },
];

export function allNavItems(): SidebarMenuItem[] {
  return [...SIDEBAR_MAIN_ITEMS, ...USER_ADMIN_MENU_ITEMS];
}

export function findMenuLabel(menuKey: string): string | undefined {
  return allNavItems().find((i) => i.key === menuKey)?.label;
}
