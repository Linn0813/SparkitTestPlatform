<template>
  <div class="schedule-sidebar" :style="sidebarStyle">
    <div
      v-if="!hideCorner"
      class="schedule-sidebar__corner"
      :style="{ height: `${headerHeight}px` }"
    />
    <div
      v-for="(member, index) in members"
      :key="member.user_id"
      class="schedule-sidebar__row"
      :class="{ 'schedule-sidebar__row--alt': index % 2 === 1 }"
      :style="{ height: `${rowHeight(member)}px` }"
    >
      <div class="schedule-sidebar__main">
        <div class="schedule-sidebar__user">
          <n-avatar round size="small" class="schedule-sidebar__avatar">
            {{ avatarInitial(member.name) }}
          </n-avatar>
          <n-tooltip v-if="nameOverflow(member.name)" trigger="hover" :show-arrow="false">
            <template #trigger>
              <span class="schedule-sidebar__name">{{ member.name }}</span>
            </template>
            {{ member.name }}
          </n-tooltip>
          <span v-else class="schedule-sidebar__name">{{ member.name }}</span>
        </div>
        <dl class="schedule-sidebar__stats">
          <div class="schedule-sidebar__stat">
            <dt class="schedule-sidebar__stat-label">已排期项</dt>
            <dd class="schedule-sidebar__stat-value">{{ member.scheduled_count }}</dd>
          </div>
          <div class="schedule-sidebar__stat">
            <dt class="schedule-sidebar__stat-label">总估分</dt>
            <dd class="schedule-sidebar__stat-value">{{ formatPoints(member.total_estimate_points) }}</dd>
          </div>
          <div class="schedule-sidebar__stat">
            <dt class="schedule-sidebar__stat-label">未排期</dt>
            <dd class="schedule-sidebar__stat-value schedule-sidebar__stat-value--row">
              <span>{{ member.unscheduled_count }}</span>
              <n-button
                v-if="member.unscheduled_count > 0"
                text
                type="primary"
                size="tiny"
                class="schedule-sidebar__view-btn"
                @click="emit('view-unscheduled', member)"
              >
                查看
              </n-button>
            </dd>
          </div>
        </dl>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { NAvatar, NButton, NTooltip } from 'naive-ui';
import type { MemberScheduleRow } from '@/types/business';
import {
  SCHEDULE_HEADER_HEIGHT,
  SCHEDULE_SIDEBAR_WIDTH,
  rowHeightForMember,
} from '@/views/schedule/scheduleMetrics';

const props = withDefaults(
  defineProps<{
    members: MemberScheduleRow[];
    rangeStart: string;
    rangeEnd: string;
    headerHeight?: number;
    hideCorner?: boolean;
    expandedGroupKeys?: Set<string>;
  }>(),
  { hideCorner: false, expandedGroupKeys: () => new Set() }
);

const emit = defineEmits<{
  'view-unscheduled': [member: MemberScheduleRow];
}>();

const headerHeight = computed(() => props.headerHeight ?? SCHEDULE_HEADER_HEIGHT);

const sidebarStyle = computed(() => ({
  width: `${SCHEDULE_SIDEBAR_WIDTH}px`,
}));

function avatarInitial(name: string): string {
  const t = name.trim();
  return t ? t.slice(0, 1) : '?';
}

function formatPoints(v: number): string {
  return Number.isInteger(v) ? String(v) : v.toFixed(1);
}

function nameOverflow(name: string): boolean {
  return name.trim().length > 10;
}

function rowHeight(member: MemberScheduleRow): number {
  return rowHeightForMember(
    member,
    props.rangeStart,
    props.rangeEnd,
    props.expandedGroupKeys
  );
}
</script>

<style scoped>
.schedule-sidebar {
  flex-shrink: 0;
  background: var(--schedule-sidebar-bg, #fff);
  border-right: 1px solid var(--schedule-border, #e5e6eb);
}
.schedule-sidebar__corner {
  flex-shrink: 0;
  background: var(--schedule-header-bg, #f5f6f8);
  border-bottom: 1px solid var(--schedule-border, #e5e6eb);
}
.schedule-sidebar__row {
  display: flex;
  align-items: flex-start;
  overflow: hidden;
  padding: 8px 10px;
  box-sizing: border-box;
  border-bottom: 1px solid var(--schedule-border, #e5e6eb);
  background: var(--schedule-row-bg, #fff);
}
.schedule-sidebar__row--alt {
  background: var(--schedule-row-alt-bg, #fafbfc);
}
.schedule-sidebar__main {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
  min-width: 0;
}
.schedule-sidebar__user {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.schedule-sidebar__avatar {
  flex-shrink: 0;
  background: var(--schedule-brand, #18a058) !important;
  color: #fff !important;
  font-size: 12px;
}
.schedule-sidebar__name {
  font-weight: 600;
  font-size: 14px;
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.schedule-sidebar__stats {
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 11px;
}
.schedule-sidebar__stat {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin: 0;
}
.schedule-sidebar__stat-label {
  margin: 0;
  color: var(--n-text-color-3);
  white-space: nowrap;
  font-weight: 400;
}
.schedule-sidebar__stat-value {
  margin: 0;
  font-variant-numeric: tabular-nums;
  color: var(--n-text-color-1);
  font-weight: 600;
  font-size: 12px;
}
.schedule-sidebar__stat-value--row {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.schedule-sidebar__view-btn {
  padding: 0 !important;
  height: auto !important;
  font-size: 12px !important;
}
</style>
