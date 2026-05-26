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

  const byReq = new Map<string, ClippedItem[]>();
  for (const c of clipped) {
    const reqId = c.item.requirement_id;
    if (!reqId) continue;
    const list = byReq.get(reqId) ?? [];
    list.push(c);
    byReq.set(reqId, list);
  }

  const segments: LaneSegment[] = [];

  for (const c of clipped) {
    if (c.item.requirement_id) continue;
    segments.push({ kind: 'single', clipped: c, startCol: c.startCol, endCol: c.endCol });
  }

  for (const [, list] of byReq) {
    if (list.length === 1) {
      const c = list[0];
      segments.push({ kind: 'single', clipped: c, startCol: c.startCol, endCol: c.endCol });
    } else {
      const startCol = Math.min(...list.map((c) => c.startCol));
      const endCol = Math.max(...list.map((c) => c.endCol));
      segments.push({
        kind: 'group',
        clipped: list,
        startCol,
        endCol,
        spanCols: endCol - startCol + 1,
      });
    }
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
      const sorted = [...seg.clipped].sort(
        (a, b) => a.startCol - b.startCol || a.endCol - b.endCol
      );
      const first = sorted[0].item;
      groups.push({
        requirement_id: first.requirement_id!,
        requirement_num: first.requirement_num ?? 0,
        requirement_title: first.requirement_title ?? '',
        items: sorted.map((c) => c.item),
        children: sorted.map((c) => ({
          item: c.item,
          startCol: c.startCol,
          spanCols: c.spanCols,
          lane: 0,
        })),
        startCol: seg.startCol,
        spanCols: seg.spanCols,
        lane,
        total_estimate_points: sorted.reduce((sum, c) => sum + estimateValue(c.item.estimate_points), 0),
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
  let maxLane = 0;

  for (const s of layout.singles) {
    maxLane = Math.max(maxLane, s.lane + 1);
  }

  for (const g of layout.groups) {
    const expanded = expandedKeys.has(scheduleGroupKey(memberId, g.requirement_id));
    const used = expanded ? g.lane + 1 + g.children.length : g.lane + 1;
    maxLane = Math.max(maxLane, used);
  }

  return maxLane;
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
