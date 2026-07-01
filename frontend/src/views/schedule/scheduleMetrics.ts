import type { MemberScheduleRow } from '@/types/business';
import { countRowLanes, layoutScheduleRow } from '@/utils/scheduleLayout';

export const SCHEDULE_HEADER_HEIGHT = 52;
export const SCHEDULE_BAR_LANE_HEIGHT = 42;       // group bar 高度
export const SCHEDULE_BAR_CHILD_LANE_HEIGHT = 32; // child bar 高度（视觉上矮，但占用同样的 lane 空间）
export const SCHEDULE_BAR_GAP = 6;
export const SCHEDULE_ROW_PADDING_Y = 10;
/** 列宽自适应时的最小列宽，过窄时启用横向滚动 */
export const SCHEDULE_COL_MIN_WIDTH = 100;
export const SCHEDULE_SIDEBAR_WIDTH = 220;

/** 与 ScheduleMemberSidebar 样式一致，保证左右行高相同 */
const SIDEBAR_PADDING_Y = 16;
const SIDEBAR_USER_BLOCK = 34;
const SIDEBAR_BLOCK_GAP = 6;
const SIDEBAR_STAT_LINE = 16;
const SIDEBAR_STAT_LINES = 3;
const SIDEBAR_STAT_GAP = 4;

export function sidebarContentHeight(_member: MemberScheduleRow): number {
  const statsBlock =
    SIDEBAR_STAT_LINES * SIDEBAR_STAT_LINE + (SIDEBAR_STAT_LINES - 1) * SIDEBAR_STAT_GAP;
  return SIDEBAR_PADDING_Y + SIDEBAR_USER_BLOCK + SIDEBAR_BLOCK_GAP + statsBlock;
}

/** lane top 偏移，所有 lane 统一用 SCHEDULE_BAR_LANE_HEIGHT 间距 */
export function laneTopForIndex(lane: number): number {
  return SCHEDULE_ROW_PADDING_Y + lane * (SCHEDULE_BAR_LANE_HEIGHT + SCHEDULE_BAR_GAP);
}

function timelineContentHeight(
  member: MemberScheduleRow,
  rangeStart: string,
  rangeEnd: string,
  expandedGroupKeys: Set<string>
): number {
  const layout = layoutScheduleRow(member.scheduled_items, rangeStart, rangeEnd);
  const { totalLanes } = countRowLanes(layout, member.user_id, expandedGroupKeys);
  if (totalLanes === 0) return 0;
  return SCHEDULE_ROW_PADDING_Y * 2 + totalLanes * (SCHEDULE_BAR_LANE_HEIGHT + SCHEDULE_BAR_GAP);
}

export function rowHeightForMember(
  member: MemberScheduleRow,
  rangeStart: string,
  rangeEnd: string,
  expandedGroupKeys: Set<string> = new Set()
): number {
  return Math.max(
    sidebarContentHeight(member),
    timelineContentHeight(member, rangeStart, rangeEnd, expandedGroupKeys)
  );
}
