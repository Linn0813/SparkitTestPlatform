<template>
  <div class="schedule-grid-wrap" :class="{ 'schedule-grid-wrap--header': headerOnly, 'schedule-grid-wrap--body': bodyOnly }">
    <div class="schedule-grid-scroll" ref="scrollRef" @scroll="onScroll">
      <div class="schedule-grid" :style="gridStyle">
        <div
          v-if="!bodyOnly"
          class="schedule-grid__header"
          :style="{ height: `${headerHeight}px` }"
        >
          <div
            v-for="day in days"
            :key="day"
            class="schedule-grid__head-cell"
            :class="headCellClass(day)"
          >
            <template v-if="day === today">
              <span class="schedule-grid__today-tag">今天</span>
              <span class="schedule-grid__date">{{ formatDayHeader(day, today).label }}</span>
            </template>
            <template v-else>
              <span class="schedule-grid__weekday">{{ formatDayHeader(day, today).weekday }}</span>
              <span class="schedule-grid__date">{{ formatDayHeader(day, today).label }}</span>
            </template>
          </div>
        </div>

        <div
          v-for="(member, rowIndex) in members"
          v-show="!headerOnly"
          :key="member.user_id"
          class="schedule-grid__row"
          :class="{ 'schedule-grid__row--alt': rowIndex % 2 === 1 }"
          :style="{ height: `${rowHeight(member)}px` }"
        >
          <div
            v-for="day in days"
            :key="`${member.user_id}-${day}`"
            class="schedule-grid__cell"
            :class="cellClass(day)"
          />
          <template v-for="bar in rowLayoutFor(member).singles" :key="bar.item.id">
            <button
              type="button"
              class="schedule-bar"
              :style="barStyle(bar, member)"
              @click="emit('open-item', bar.item)"
            >
              <span
                class="schedule-bar__accent"
                :style="{ background: itemAccentColor(bar.item) }"
              />
              <span class="schedule-bar__body">
                <span class="schedule-bar__title">{{ barDisplayTitle(bar) }}</span>
                <span v-if="barSubtitleText(bar)" class="schedule-bar__phase">
                  {{ barSubtitleText(bar) }}
                </span>
                <span v-if="bar.item.estimate_points != null" class="schedule-bar__points-inline">
                  {{ formatPoints(bar.item.estimate_points) }}
                </span>
              </span>
            </button>
          </template>

          <template v-for="group in rowLayoutFor(member).groups" :key="group.requirement_id">
            <div class="schedule-bar schedule-bar--group" :style="groupBarStyle(group, member)">
              <span
                class="schedule-bar__accent"
                :style="{ background: requirementAccentColor(group.requirement_id) }"
              />
              <button
                type="button"
                class="schedule-bar__main-btn"
                @click="emit('open-item', group.items[0])"
              >
                <span class="schedule-bar__body">
                  <span class="schedule-bar__title">{{ groupDisplayTitle(group) }}</span>
                  <span class="schedule-bar__phase">{{ group.items.length }} 项</span>
                  <span class="schedule-bar__points-inline">
                    {{ formatPoints(group.total_estimate_points) }}
                  </span>
                </span>
              </button>
              <button
                type="button"
                class="schedule-bar__expand"
                :aria-expanded="isGroupExpanded(member.user_id, group.requirement_id)"
                :aria-label="isGroupExpanded(member.user_id, group.requirement_id) ? '收起任务' : '展开任务'"
                @click.stop="onToggleGroup(member.user_id, group.requirement_id)"
              >
                {{ isGroupExpanded(member.user_id, group.requirement_id) ? '▲' : '▼' }}
              </button>
            </div>

            <template v-if="isGroupExpanded(member.user_id, group.requirement_id)">
              <button
                v-for="(child, childIndex) in group.children"
                :key="child.item.id"
                type="button"
                class="schedule-bar schedule-bar--child"
                :style="childBarStyle(group, child, childIndex, member)"
                @click="emit('open-item', child.item)"
              >
                <span
                  class="schedule-bar__accent"
                  :style="{ background: itemAccentColor(child.item) }"
                />
                <span class="schedule-bar__body">
                  <span class="schedule-bar__title">{{ childDisplayTitle(child) }}</span>
                  <span v-if="child.item.estimate_points != null" class="schedule-bar__points-inline">
                    {{ formatPoints(child.item.estimate_points) }}
                  </span>
                </span>
              </button>
            </template>
          </template>
        </div>
        <div
          v-if="!headerOnly && todayColIndex >= 0"
          class="schedule-grid__today-line"
          :style="todayLineStyle"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import type { MemberScheduleItem, MemberScheduleRow } from '@/types/business';
import {
  SCHEDULE_BAR_GAP,
  SCHEDULE_BAR_LANE_HEIGHT,
  SCHEDULE_COL_MIN_WIDTH,
  SCHEDULE_HEADER_HEIGHT,
  SCHEDULE_ROW_PADDING_Y,
  rowHeightForMember,
} from '@/views/schedule/scheduleMetrics';
import {
  itemAccentColor,
  layoutScheduleRow,
  requirementAccentColor,
  scheduleGroupKey,
  computeRenderLanes,
  type ScheduleBarLayout,
  type ScheduleRequirementGroup,
} from '@/utils/scheduleLayout';
import { eachDayInRange, formatDayHeader, isWeekendDay } from '@/utils/scheduleRange';

const props = withDefaults(
  defineProps<{
    members: MemberScheduleRow[];
    rangeStart: string;
    rangeEnd: string;
    today: string;
    headerOnly?: boolean;
    bodyOnly?: boolean;
    expandedGroupKeys?: Set<string>;
  }>(),
  {
    headerOnly: false,
    bodyOnly: false,
    expandedGroupKeys: () => new Set(),
  }
);

const emit = defineEmits<{
  'open-item': [item: MemberScheduleItem];
  'toggle-group': [memberId: string, requirementId: string];
  scroll: [event: Event];
}>();

const scrollRef = ref<HTMLDivElement | null>(null);

function onScroll(event: Event) {
  emit('scroll', event);
}

defineExpose({
  getScrollElement: () => scrollRef.value,
});

const headerHeight = SCHEDULE_HEADER_HEIGHT;

const days = computed(() => eachDayInRange(props.rangeStart, props.rangeEnd));
const dayCount = computed(() => Math.max(days.value.length, 1));
const todayColIndex = computed(() => days.value.indexOf(props.today));

const gridStyle = computed(() => {
  const n = days.value.length;
  return {
    '--day-count': String(n || 1),
    width: '100%',
    minWidth: n > 0 ? `${n * SCHEDULE_COL_MIN_WIDTH}px` : undefined,
  };
});

const todayLineStyle = computed(() => {
  if (todayColIndex.value < 0) return { display: 'none' };
  const n = dayCount.value;
  const center = todayColIndex.value + 0.5;
  return { left: `calc(100% * ${center} / ${n})` };
});

function spanOffsetStyle(
  startCol: number,
  spanCols: number,
  insetStart: number,
  insetTotal: number
): { left: string; width: string } {
  const n = dayCount.value;
  return {
    left: `calc(100% * ${startCol} / ${n} + ${insetStart}px)`,
    width: `calc(100% * ${spanCols} / ${n} - ${insetTotal}px)`,
  };
}

function headCellClass(day: string) {
  return {
    'schedule-grid__head-cell--today': day === props.today,
    'schedule-grid__head-cell--weekend': isWeekendDay(day),
  };
}

function cellClass(day: string) {
  return {
    'schedule-grid__cell--today': day === props.today,
    'schedule-grid__cell--weekend': isWeekendDay(day),
  };
}

function rowHeight(member: MemberScheduleRow): number {
  return rowHeightForMember(
    member,
    props.rangeStart,
    props.rangeEnd,
    props.expandedGroupKeys
  );
}

// 缓存每个 member 的 layout 和 renderLanes，避免模板里重复计算
const rowLayoutMap = computed(() => {
  const map = new Map<string, ReturnType<typeof layoutScheduleRow>>();
  for (const member of props.members) {
    map.set(member.user_id, layoutScheduleRow(member.scheduled_items, props.rangeStart, props.rangeEnd));
  }
  return map;
});

const renderLanesMap = computed(() => {
  const map = new Map<string, ReturnType<typeof computeRenderLanes>>();
  for (const member of props.members) {
    const layout = rowLayoutMap.value.get(member.user_id)!;
    map.set(member.user_id, computeRenderLanes(layout, member.user_id, props.expandedGroupKeys));
  }
  return map;
});

function rowLayoutFor(member: MemberScheduleRow) {
  return rowLayoutMap.value.get(member.user_id)
    ?? layoutScheduleRow(member.scheduled_items, props.rangeStart, props.rangeEnd);
}

function renderLanesFor(member: MemberScheduleRow) {
  return renderLanesMap.value.get(member.user_id)
    ?? computeRenderLanes(rowLayoutFor(member), member.user_id, props.expandedGroupKeys);
}

function isGroupExpanded(memberId: string, requirementId: string): boolean {
  return props.expandedGroupKeys.has(scheduleGroupKey(memberId, requirementId));
}

function onToggleGroup(memberId: string, requirementId: string) {
  emit('toggle-group', memberId, requirementId);
}

function laneTop(lane: number): number {
  return SCHEDULE_ROW_PADDING_Y + lane * (SCHEDULE_BAR_LANE_HEIGHT + SCHEDULE_BAR_GAP);
}

function barStyle(bar: ScheduleBarLayout, member: MemberScheduleRow): Record<string, string> {
  const { left, width } = spanOffsetStyle(bar.startCol, bar.spanCols, 8, 16);
  const lane = renderLanesFor(member).singleLanes.get(bar.item.id) ?? bar.lane;
  return {
    left,
    width: `max(${width}, 72px)`,
    top: `${laneTop(lane)}px`,
    zIndex: String(10 + lane),
  };
}

function groupBarStyle(group: ScheduleRequirementGroup, member: MemberScheduleRow): Record<string, string> {
  const { left, width } = spanOffsetStyle(group.startCol, group.spanCols, 8, 16);
  const lane = renderLanesFor(member).groupLanes.get(group.requirement_id) ?? group.lane;
  return {
    left,
    width: `max(${width}, 88px)`,
    top: `${laneTop(lane)}px`,
    zIndex: String(10 + lane),
  };
}

function childBarStyle(
  group: ScheduleRequirementGroup,
  child: ScheduleBarLayout,
  childIndex: number,
  member: MemberScheduleRow
): Record<string, string> {
  const { left, width } = spanOffsetStyle(child.startCol, child.spanCols, 12, 20);
  const childLanesForGroup = renderLanesFor(member).childLanes.get(group.requirement_id);
  const lane = childLanesForGroup?.[childIndex] ?? (group.lane + 1 + childIndex);
  return {
    left,
    width: `max(${width}, 68px)`,
    top: `${laneTop(lane)}px`,
    zIndex: String(10 + lane),
  };
}

function isBugItem(item: MemberScheduleItem): boolean {
  return item.item_type === 'bug';
}

function groupDisplayTitle(group: ScheduleRequirementGroup): string {
  return group.requirement_title || '';
}

function childDisplayTitle(bar: ScheduleBarLayout): string {
  if (isBugItem(bar.item)) {
    return bar.item.bug_title ?? bar.item.title;
  }
  const phase = bar.item.node_label?.trim();
  const task = bar.item.title?.trim();
  if (phase && task && phase === task) return phase;
  if (phase && task) return `${phase} · ${task}`;
  return phase || task || bar.item.requirement_title || '';
}

function barDisplayTitle(bar: ScheduleBarLayout): string {
  if (isBugItem(bar.item)) {
    return bar.item.bug_title ?? bar.item.title;
  }
  return bar.item.requirement_title || '';
}

function barSubtitleText(bar: ScheduleBarLayout): string | null {
  if (isBugItem(bar.item)) return '缺陷修复';
  const phase = bar.item.node_label?.trim();
  const task = bar.item.title?.trim();
  if (phase && task && phase === task) return null;
  return phase || task || null;
}

function formatPoints(v: number): string {
  return Number.isInteger(v) ? String(v) : v.toFixed(1);
}
</script>

<style scoped>
.schedule-grid-wrap {
  flex: 1;
  min-width: 0;
}
.schedule-grid-wrap--header {
  flex: 1;
  min-width: 0;
  width: 100%;
}
.schedule-grid-wrap--header .schedule-grid-scroll {
  overflow-x: auto;
  overflow-y: hidden;
  width: 100%;
}
.schedule-grid-wrap--body {
  flex: 1;
  min-width: 0;
  width: 100%;
  height: 100%;
}
.schedule-grid-wrap--body .schedule-grid-scroll {
  overflow-x: auto;
  overflow-y: visible;
  width: 100%;
  height: 100%;
}
.schedule-grid-scroll {
  overflow-x: auto;
  overflow-y: visible;
  width: 100%;
}
.schedule-grid {
  position: relative;
  display: flex;
  flex-direction: column;
  width: 100%;
}
.schedule-grid__header {
  display: grid;
  grid-template-columns: repeat(var(--day-count), minmax(0, 1fr));
  width: 100%;
  background: var(--schedule-header-bg, #f5f6f8);
  border-bottom: 1px solid var(--schedule-border, #e5e6eb);
}
.schedule-grid__head-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  font-size: 12px;
  padding: 8px 4px;
  border-right: 1px solid var(--schedule-border, #e5e6eb);
  background: var(--schedule-header-bg, #f5f6f8);
}
.schedule-grid__head-cell--weekend {
  background: var(--schedule-weekend-bg, #f3f4f6);
}
.schedule-grid__head-cell--today {
  background: var(--schedule-today-bg, #eef5ff);
}
.schedule-grid__weekday {
  color: var(--n-text-color-3);
  font-size: 11px;
  line-height: 1.2;
}
.schedule-grid__today-tag {
  font-size: 11px;
  font-weight: 600;
  line-height: 1.2;
  color: var(--schedule-today-line, #2080f0);
}
.schedule-grid__head-cell--today .schedule-grid__date {
  font-weight: 600;
  color: var(--schedule-today-line, #2080f0);
}
.schedule-grid__date {
  font-size: 12px;
  line-height: 1.3;
  color: var(--n-text-color-1);
}
.schedule-grid__row {
  position: relative;
  display: grid;
  grid-template-columns: repeat(var(--day-count), minmax(0, 1fr));
  width: 100%;
  border-bottom: 1px solid var(--schedule-border, #e5e6eb);
  box-sizing: border-box;
  overflow: hidden;
  background: var(--schedule-row-bg, #fff);
}
.schedule-grid__row--alt {
  background: var(--schedule-row-alt-bg, #fafbfc);
}
.schedule-grid__cell {
  border-right: 1px solid var(--schedule-border, #e5e6eb);
  background: inherit;
}
.schedule-grid__cell--weekend {
  background: var(--schedule-weekend-bg, #f3f4f6);
}
.schedule-grid__row--alt .schedule-grid__cell--weekend {
  background: color-mix(in srgb, var(--schedule-weekend-bg, #f3f4f6) 85%, var(--schedule-row-alt-bg, #fafbfc));
}
.schedule-grid__cell--today {
  background: var(--schedule-today-bg, #eef5ff);
}
.schedule-grid__row--alt .schedule-grid__cell--today {
  background: color-mix(in srgb, var(--schedule-today-bg, #eef5ff) 90%, var(--schedule-row-alt-bg, #fafbfc));
}
.schedule-grid__today-line {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 2px;
  margin-left: -1px;
  background: var(--schedule-today-line, #2080f0);
  opacity: 0.65;
  pointer-events: none;
  z-index: 6;
}
.schedule-bar {
  position: absolute;
  display: flex;
  align-items: stretch;
  min-height: 36px;
  padding: 0;
  border: 1px solid var(--schedule-border, #e5e6eb);
  border-radius: 8px;
  background: #fff;
  box-shadow: var(--schedule-bar-shadow, 0 1px 3px rgba(15, 23, 42, 0.08));
  cursor: pointer;
  text-align: left;
  overflow: hidden;
  transition: box-shadow 0.15s ease, border-color 0.15s ease, transform 0.15s ease;
}
.schedule-bar:hover {
  border-color: var(--schedule-today-line, #2080f0);
  box-shadow: var(--schedule-bar-shadow-hover, 0 2px 8px rgba(15, 23, 42, 0.12));
  transform: translateY(-1px);
}
.schedule-bar__accent {
  width: 4px;
  flex-shrink: 0;
  border-radius: 8px 0 0 8px;
}
.schedule-bar__body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 6px;
  padding: 6px 8px 6px 10px;
  line-height: 1.35;
}
.schedule-bar__title {
  flex: 1;
  min-width: 0;
  font-weight: 600;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.schedule-bar__phase {
  flex-shrink: 0;
  font-size: 11px;
  color: var(--n-text-color-3);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 40%;
}
.schedule-bar__points-inline {
  flex-shrink: 0;
  padding: 2px 6px;
  font-size: 11px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  line-height: 1.3;
  color: var(--n-text-color-2);
  background: var(--schedule-header-bg, #f5f6f8);
  border-radius: 6px;
  border: 1px solid var(--schedule-border, #e5e6eb);
}
.schedule-bar--group {
  min-height: 38px;
  background: color-mix(in srgb, var(--schedule-today-bg, #eef5ff) 35%, #fff);
  padding: 0;
}
.schedule-bar--group:hover {
  transform: none;
}
.schedule-bar--group .schedule-bar__main-btn {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: stretch;
  margin: 0;
  padding: 0;
  border: none;
  background: transparent;
  cursor: pointer;
  text-align: left;
  font: inherit;
  color: inherit;
}
.schedule-bar--group .schedule-bar__main-btn:hover {
  opacity: 0.92;
}
.schedule-bar--group .schedule-bar__phase {
  max-width: none;
}
.schedule-bar__expand {
  flex-shrink: 0;
  align-self: stretch;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  margin: 0;
  padding: 0;
  border: none;
  border-left: 1px solid var(--schedule-border, #e5e6eb);
  background: transparent;
  color: var(--n-text-color-3);
  font-size: 10px;
  cursor: pointer;
}
.schedule-bar__expand:hover {
  background: var(--schedule-header-bg, #f5f6f8);
  color: var(--n-text-color-1);
}
.schedule-bar--child {
  min-height: 36px;
  opacity: 0.98;
}
.schedule-bar--child .schedule-bar__body {
  padding-left: 12px;
}
.schedule-bar--child .schedule-bar__title {
  flex: 1;
  font-weight: 500;
  font-size: 12px;
}
</style>
