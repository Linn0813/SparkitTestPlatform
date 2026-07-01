import type { MemberScheduleItem } from '@/types/business';
import { diffDays } from '@/utils/scheduleRange';

export interface ScheduleBarLayout {
  item: MemberScheduleItem;
  startCol: number;
  spanCols: number;
  lane: number;
}

export interface ScheduleRequirementGroup {
  requirement_id: string;
  requirement_num: number;
  requirement_title: string;
  items: MemberScheduleItem[];
  children: ScheduleBarLayout[];
  startCol: number;
  spanCols: number;
  lane: number;
  total_estimate_points: number;
}

export interface ScheduleRowLayout {
  singles: ScheduleBarLayout[];
  groups: ScheduleRequirementGroup[];
}

interface ClippedItem {
  item: MemberScheduleItem;
  startCol: number;
  spanCols: number;
  endCol: number;
}

function estimateValue(points: number | null | undefined): number {
  return points != null ? Number(points) : 0;
}

function clipItem(
  item: MemberScheduleItem,
  rangeStart: string,
  rangeEnd: string
): ClippedItem | null {
  const s = item.scheduled_start?.slice(0, 10);
  const e = item.scheduled_end?.slice(0, 10);
  if (!s || !e) return null;
  const visibleStart = diffDays(s, rangeStart) < 0 ? rangeStart : s;
  const visibleEnd = diffDays(e, rangeEnd) > 0 ? rangeEnd : e;
  if (diffDays(visibleStart, visibleEnd) > 0) return null;
  return {
    item,
    startCol: diffDays(visibleStart, rangeStart),
    spanCols: diffDays(visibleEnd, visibleStart) + 1,
    endCol: diffDays(visibleEnd, rangeStart),
  };
}

type LaneSegment =
  | { kind: 'single'; clipped: ClippedItem; startCol: number; endCol: number }
  | { kind: 'group'; clipped: ClippedItem[]; startCol: number; endCol: number; spanCols: number };

function assignLanes(segments: LaneSegment[]): Map<LaneSegment, number> {
  const sorted = [...segments].sort((a, b) => a.startCol - b.startCol || a.endCol - b.endCol);
  const laneEnds: number[] = [];
  const lanes = new Map<LaneSegment, number>();

  for (const seg of sorted) {
    let lane = 0;
    while (lane < laneEnds.length && seg.startCol <= laneEnds[lane]) {
      lane += 1;
    }
    if (lane === laneEnds.length) laneEnds.push(seg.endCol);
    else laneEnds[lane] = seg.endCol;
    lanes.set(seg, lane);
  }

  return lanes;
}

export function layoutScheduleRow(
  items: MemberScheduleItem[],
  rangeStart: string,
  rangeEnd: string
): ScheduleRowLayout {
  const clipped = items
    .map((item) => clipItem(item, rangeStart, rangeEnd))
    .filter((c): c is ClippedItem => c != null);

  // 按需求 ID 分组所有 items（包括未排期/视窗外的），用于判断是否应显示为 group
  const allByReq = new Map<string, MemberScheduleItem[]>();
  for (const item of items) {
    const reqId = item.requirement_id;
    if (!reqId) continue;
    const list = allByReq.get(reqId) ?? [];
    list.push(item);
    allByReq.set(reqId, list);
  }

  // 视窗内可见的 clipped items，按需求 ID 分组
  const clippedByReq = new Map<string, ClippedItem[]>();
  for (const c of clipped) {
    const reqId = c.item.requirement_id;
    if (!reqId) continue;
    const list = clippedByReq.get(reqId) ?? [];
    list.push(c);
    clippedByReq.set(reqId, list);
  }

  const segments: LaneSegment[] = [];

  // 无需求 ID 的 items（bug 等）直接作为 single
  for (const c of clipped) {
    if (c.item.requirement_id) continue;
    segments.push({ kind: 'single', clipped: c, startCol: c.startCol, endCol: c.endCol });
  }

  // 有需求 ID 的：全部作为 group（包括只有 1 个任务的），统一可展开查看
  const processedReqs = new Set<string>();
  for (const c of clipped) {
    const reqId = c.item.requirement_id;
    if (!reqId || processedReqs.has(reqId)) continue;
    processedReqs.add(reqId);

    const allItems = allByReq.get(reqId) ?? [];
    const visibleClipped = clippedByReq.get(reqId) ?? [];

    if (visibleClipped.length === 0) continue;
    const startCol = Math.min(...visibleClipped.map((c) => c.startCol));
    const endCol = Math.max(...visibleClipped.map((c) => c.endCol));
    segments.push({
      kind: 'group',
      clipped: visibleClipped,
      startCol,
      endCol,
      spanCols: endCol - startCol + 1,
    });
  }

  const laneMap = assignLanes(segments);

  const singles: ScheduleBarLayout[] = [];
  const groups: ScheduleRequirementGroup[] = [];

  for (const seg of segments) {
    const lane = laneMap.get(seg) ?? 0;
    if (seg.kind === 'single') {
      const c = seg.clipped;
      singles.push({
        item: c.item,
        startCol: c.startCol,
        spanCols: c.spanCols,
        lane,
      });
    } else {
      const reqId = seg.clipped[0].item.requirement_id!;
      const allItems = allByReq.get(reqId) ?? [];
      const sortedVisible = [...seg.clipped].sort(
        (a, b) => a.startCol - b.startCol || a.endCol - b.endCol
      );
      const first = allItems[0];
      groups.push({
        requirement_id: reqId,
        requirement_num: first.requirement_num ?? 0,
        requirement_title: first.requirement_title ?? '',
        // items 包含所有任务（用于显示 "N项"）
        items: allItems,
        // children 只包含视窗内可见的任务（用于展开渲染）
        children: sortedVisible.map((c) => ({
          item: c.item,
          startCol: c.startCol,
          spanCols: c.spanCols,
          lane: 0,
        })),
        startCol: seg.startCol,
        spanCols: seg.spanCols,
        lane,
        total_estimate_points: allItems.reduce((sum, item) => sum + estimateValue(item.estimate_points), 0),
      });
    }
  }

  return { singles, groups };
}

export function scheduleGroupKey(memberId: string, requirementId: string): string {
  return `${memberId}:${requirementId}`;
}

export function countRowLanes(
  layout: ScheduleRowLayout,
  memberId: string,
  expandedKeys: Set<string>
): number {
  // 展开的 groups 按 lane 升序，用来计算偏移
  const expandedGroups = layout.groups
    .filter(g => expandedKeys.has(scheduleGroupKey(memberId, g.requirement_id)))
    .sort((a, b) => a.lane - b.lane);

  function resolvedLane(originalLane: number): number {
    let offset = 0;
    for (const g of expandedGroups) {
      if (originalLane > g.lane) offset += childLaneCount(g.children);
    }
    return originalLane + offset;
  }

  let maxLane = 0;

  for (const s of layout.singles) {
    maxLane = Math.max(maxLane, resolvedLane(s.lane) + 1);
  }

  for (const g of layout.groups) {
    const isExpanded = expandedKeys.has(scheduleGroupKey(memberId, g.requirement_id));
    const resolvedGroupLane = resolvedLane(g.lane);
    const used = isExpanded ? resolvedGroupLane + 1 + childLaneCount(g.children) : resolvedGroupLane + 1;
    maxLane = Math.max(maxLane, used);
  }

  return maxLane;
}

/**
 * 对子任务列表分配 lane，时间不重叠的子任务共享同一 lane。
 * 返回每个 childIndex 对应的 lane offset（相对于 group lane + 1）。
 */
function assignChildLaneOffsets(children: ScheduleBarLayout[]): number[] {
  const laneEnds: number[] = [];
  const offsets: number[] = new Array(children.length).fill(0);
  for (let i = 0; i < children.length; i++) {
    const c = children[i];
    const endCol = c.startCol + c.spanCols - 1;
    let lane = 0;
    while (lane < laneEnds.length && c.startCol <= laneEnds[lane]) {
      lane += 1;
    }
    if (lane === laneEnds.length) laneEnds.push(endCol);
    else laneEnds[lane] = endCol;
    offsets[i] = lane;
  }
  return offsets;
}

/** 展开一个 group 时，子任务实际占用的 lane 数（考虑时间重叠压缩） */
function childLaneCount(children: ScheduleBarLayout[]): number {
  if (children.length === 0) return 0;
  const offsets = assignChildLaneOffsets(children);
  return Math.max(...offsets) + 1;
}


export function computeRenderLanes(
  layout: ScheduleRowLayout,
  memberId: string,
  expandedKeys: Set<string>
): {
  singleLanes: Map<string, number>;   // item.id -> render lane
  groupLanes: Map<string, number>;    // requirement_id -> render lane
  childLanes: Map<string, number[]>;  // requirement_id -> [child0 lane, child1 lane, ...]
} {
  // 收集展开的 groups，按 lane 升序处理
  const expandedGroups = layout.groups
    .filter(g => expandedKeys.has(scheduleGroupKey(memberId, g.requirement_id)))
    .sort((a, b) => a.lane - b.lane);

  // 对每个原始 lane 计算累积偏移
  // 展开 lane=X 的 group（子任务实际占 M 个 lane），则所有原始 lane > X 的 bar 偏移 +M
  function resolvedLane(originalLane: number): number {
    let offset = 0;
    for (const g of expandedGroups) {
      if (originalLane > g.lane) {
        offset += childLaneCount(g.children);
      }
    }
    return originalLane + offset;
  }

  const singleLanes = new Map<string, number>();
  const groupLanes = new Map<string, number>();
  const childLanes = new Map<string, number[]>();

  for (const s of layout.singles) {
    singleLanes.set(s.item.id, resolvedLane(s.lane));
  }

  for (const g of layout.groups) {
    const resolvedGroupLane = resolvedLane(g.lane);
    groupLanes.set(g.requirement_id, resolvedGroupLane);
    const isExpanded = expandedKeys.has(scheduleGroupKey(memberId, g.requirement_id));
    if (isExpanded) {
      // 用 assignChildLaneOffsets 让时间不重叠的子任务共享同一 lane
      const offsets = assignChildLaneOffsets(g.children);
      childLanes.set(g.requirement_id, offsets.map(offset => resolvedGroupLane + 1 + offset));
    }
  }

  return { singleLanes, groupLanes, childLanes };
}

/** @deprecated Use layoutScheduleRow; kept for flat lane helpers */
export function layoutScheduleBars(
  items: MemberScheduleItem[],
  rangeStart: string,
  rangeEnd: string
): ScheduleBarLayout[] {
  const row = layoutScheduleRow(items, rangeStart, rangeEnd);
  const out: ScheduleBarLayout[] = [...row.singles];
  for (const g of row.groups) {
    out.push({
      item: g.items[0],
      startCol: g.startCol,
      spanCols: g.spanCols,
      lane: g.lane,
    });
    for (const c of g.children) {
      out.push({ ...c, lane: g.lane });
    }
  }
  return out;
}

export function maxLaneCount(layouts: ScheduleBarLayout[]): number {
  if (!layouts.length) return 0;
  return Math.max(...layouts.map((l) => l.lane)) + 1;
}

const BAR_COLORS = [
  '#7c3aed',
  '#2563eb',
  '#059669',
  '#d97706',
  '#db2777',
  '#0891b2',
];

export function barAccentColor(nodeKey: string): string {
  let hash = 0;
  for (let i = 0; i < nodeKey.length; i++) hash = (hash + nodeKey.charCodeAt(i)) % 997;
  return BAR_COLORS[hash % BAR_COLORS.length];
}

export function requirementAccentColor(requirementId: string): string {
  return barAccentColor(`req:${requirementId}`);
}

export function bugAccentColor(bugId: string): string {
  return barAccentColor(`bug:${bugId}`);
}

export function itemAccentColor(item: MemberScheduleItem): string {
  if (item.item_type === 'bug' && item.bug_id) return bugAccentColor(item.bug_id);
  return barAccentColor(item.node_key ?? item.id);
}

export interface UnscheduledDisplayGroup {
  key: string;
  kind: 'requirement' | 'bug';
  title: string;
  items: MemberScheduleItem[];
  requirement_id?: string;
  bug_id?: string;
}

/** 未排期列表：同一需求的多条节点任务合并为一组，缺陷仍一条一组。 */
export function groupUnscheduledItems(items: MemberScheduleItem[]): UnscheduledDisplayGroup[] {
  const groups: UnscheduledDisplayGroup[] = [];
  const reqGroupIndex = new Map<string, number>();

  for (const item of items) {
    if (item.item_type === 'bug') {
      const bugId = item.bug_id ?? item.id;
      groups.push({
        key: `bug:${bugId}`,
        kind: 'bug',
        title: item.bug_title ?? item.title,
        items: [item],
        bug_id: item.bug_id ?? undefined,
      });
      continue;
    }

    const reqId = item.requirement_id;
    if (reqId) {
      const idx = reqGroupIndex.get(reqId);
      if (idx !== undefined) {
        groups[idx].items.push(item);
      } else {
        reqGroupIndex.set(reqId, groups.length);
        groups.push({
          key: `req:${reqId}`,
          kind: 'requirement',
          title: item.requirement_title ?? item.title,
          items: [item],
          requirement_id: reqId,
        });
      }
      continue;
    }

    groups.push({
      key: `task:${item.id}`,
      kind: 'requirement',
      title: item.requirement_title ?? item.title,
      items: [item],
    });
  }

  return groups;
}
