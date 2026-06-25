/** ECharts colors for workbench charts */

/** 概览区缺陷/计划图统一高度（px） */
export const WORKBENCH_OVERVIEW_CHART_HEIGHT = 320;

/** 版本维度内嵌小图高度（px） */
export const WORKBENCH_VERSION_FOCUS_CHART_HEIGHT = 220;

/** 缺陷概览图：按版本堆叠的配色 */
export const VERSION_STACK_COLORS = [
  '#3370FF',
  '#00C261',
  '#FFA200',
  '#811FA3',
  '#50CEFB',
  '#FF9964',
  '#783887',
  '#ED0303',
  '#AEAEB2',
  '#2D9CDB',
];

export const BUG_STATUS_COLORS = [
  '#811FA3',
  '#3370FF',
  '#00C261',
  '#FF9964',
  '#ED0303',
  '#FFA200',
  '#50CEFB',
];

export const EXECUTE_RESULT_COLORS: Record<string, string> = {
  not_run: '#AEAEB2',
  pass: '#00C261',
  fail: '#ED0303',
  block: '#FFA200',
  skip: '#3370FF',
};

export const REQUIREMENT_BAR_COLOR = '#783887';

export const REQUIREMENT_STATUS_COLORS: Record<string, string> = {
  draft: '#AEAEB2',
  pending_review: '#FFA200',
  designing: '#50CEFB',
  developing: '#3370FF',
  testing: '#811FA3',
  pending_release: '#FF9964',
  released: '#00C261',
  completed: '#00C261',
  closed: '#AEAEB2',
};

export const PLAN_STATUS_COLORS: Record<string, string> = {
  draft: '#AEAEB2',
  active: '#3370FF',
  archived: '#783887',
};

/** 类目少时加大右侧留白，柱组靠左 */
export function workbenchCategoryGridRight(categoryCount: number): number | string {
  if (categoryCount <= 1) return '52%';
  if (categoryCount <= 2) return '40%';
  if (categoryCount <= 4) return '28%';
  return 16;
}
