<template>
  <div class="member-schedule">
    <n-card :bordered="false" class="member-schedule__card">
      <template #header>
        <ScheduleToolbar
          page-title="人员排期"
          :title="rangeTitle"
          :subtitle="rangeSubtitle"
          :loading="loading"
          @prev="shiftRange(-1)"
          @next="shiftRange(1)"
        >
          <template v-if="ctx.projectId && apiMembers.length" #extra>
            <n-popover trigger="click" placement="bottom-end">
              <template #trigger>
                <n-button size="small" quaternary>人员设置</n-button>
              </template>
              <ScheduleMemberSettingsPanel
                :members="orderedMembers"
                :is-visible="isMemberVisible"
                @update-visible="setMemberVisible"
                @move="moveMember"
                @select-all="setAllVisible(true)"
                @select-none="setAllVisible(false)"
              />
            </n-popover>
          </template>
        </ScheduleToolbar>
      </template>
      <n-spin :show="loading">
        <template v-if="!ctx.projectId">
          <n-empty description="请先选择项目" />
        </template>
        <template v-else>

          <div v-if="!apiMembers.length && !loading" class="schedule-empty">
            <n-empty description="暂无项目成员" />
          </div>

          <n-alert
            v-else-if="!hasVisibleMember"
            type="info"
            :bordered="false"
            class="schedule-hidden-all"
          >
            已隐藏全部成员，可通过「人员设置」恢复显示
          </n-alert>

          <div v-else class="schedule-board">
            <div class="schedule-board__head">
              <div
                class="schedule-board__head-corner"
                :style="headCornerStyle"
              />
              <ScheduleTimelineGrid
                ref="headGridRef"
                header-only
                :members="displayMembers"
                :range-start="rangeStart"
                :range-end="rangeEnd"
                :today="today"
                @scroll="syncScrollFromHead"
              />
            </div>
            <div class="schedule-board__body">
              <div class="schedule-body">
                <ScheduleMemberSidebar
                  hide-corner
                  :members="displayMembers"
                  :range-start="rangeStart"
                  :range-end="rangeEnd"
                  :expanded-group-keys="expandedGroupKeys"
                  @view-unscheduled="openUnscheduled"
                />
                <ScheduleTimelineGrid
                  ref="bodyGridRef"
                  body-only
                  :members="displayMembers"
                  :range-start="rangeStart"
                  :range-end="rangeEnd"
                  :today="today"
                  :expanded-group-keys="expandedGroupKeys"
                  @open-item="openScheduleItem"
                  @toggle-group="toggleScheduleGroup"
                  @scroll="syncScrollFromBody"
                />
              </div>
            </div>
          </div>
        </template>
      </n-spin>

      <ScheduleUnscheduledDrawer
        v-model:show="unscheduledVisible"
        :member="unscheduledMember"
        @open-item="onUnscheduledOpen"
      />

      <n-drawer
        v-model:show="detailDrawerVisible"
        :width="'min(1200px, 85vw)'"
        placement="right"
        :trap-focus="false"
        @update:show="onDetailDrawerShowChange"
      >
        <n-drawer-content :closable="false" body-content-style="padding: 0">
          <RequirementDetailPanel
            v-if="activeRequirementId"
            :requirement-id="activeRequirementId"
            :has-prev="false"
            :has-next="false"
            @close="closeDetailDrawer"
            @deleted="onDetailDeleted"
            @updated="onDetailUpdated"
          />
          <BugDetailPanel
            v-else-if="activeBugId"
            :bug-id="activeBugId"
            :has-prev="false"
            :has-next="false"
            @close="closeDetailDrawer"
            @deleted="onDetailDeleted"
            @updated="onBugDetailUpdated"
          />
        </n-drawer-content>
      </n-drawer>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, toRef, watch } from 'vue';
import { NAlert, NButton, NCard, NDrawer, NDrawerContent, NEmpty, NPopover, NSpin, useMessage } from 'naive-ui';
import RequirementDetailPanel from '@/components/RequirementDetailPanel.vue';
import BugDetailPanel from '@/components/BugDetailPanel.vue';
import { fetchMemberSchedule } from '@/api/memberSchedule';
import type { MemberSchedule, MemberScheduleItem, MemberScheduleRow, Requirement } from '@/types/business';
import { useMemberScheduleMemberPrefs } from '@/composables/useMemberScheduleMemberPrefs';
import { useContextStore } from '@/stores/context';
import {
  addDays,
  defaultScheduleRange,
  diffDays,
  formatRangeSubtitle,
  formatRangeTitle,
} from '@/utils/scheduleRange';
import { todayInUtcPlus8 } from '@/utils/timezone';
import ScheduleMemberSidebar from './components/ScheduleMemberSidebar.vue';
import ScheduleTimelineGrid from './components/ScheduleTimelineGrid.vue';
import {
  SCHEDULE_HEADER_HEIGHT,
  SCHEDULE_SIDEBAR_WIDTH,
} from './scheduleMetrics';
import { scheduleGroupKey } from '@/utils/scheduleLayout';
import ScheduleMemberSettingsPanel from './components/ScheduleMemberSettingsPanel.vue';
import ScheduleToolbar from './components/ScheduleToolbar.vue';
import ScheduleUnscheduledDrawer from './components/ScheduleUnscheduledDrawer.vue';
import './scheduleTheme.css';

const ctx = useContextStore();
const message = useMessage();

const loading = ref(false);
const data = ref<MemberSchedule | null>(null);
const today = todayInUtcPlus8();

const initial = defaultScheduleRange(today);
const rangeStart = ref(initial.start);
const rangeEnd = ref(initial.end);

const rangeTitle = computed(() => formatRangeTitle(rangeStart.value, rangeEnd.value));
const rangeSubtitle = computed(() => formatRangeSubtitle(rangeStart.value, rangeEnd.value));

const apiMembers = computed(() => data.value?.members ?? []);

const {
  orderedMembers,
  displayMembers,
  hasVisibleMember,
  isMemberVisible,
  setMemberVisible,
  setAllVisible,
  moveMember,
} = useMemberScheduleMemberPrefs(toRef(ctx, 'projectId'), apiMembers);

const unscheduledVisible = ref(false);
const unscheduledMember = ref<MemberScheduleRow | null>(null);

const detailDrawerVisible = ref(false);
const activeRequirementId = ref<string | null>(null);
const activeBugId = ref<string | null>(null);

const expandedGroupKeys = ref<Set<string>>(new Set());

const headGridRef = ref<InstanceType<typeof ScheduleTimelineGrid> | null>(null);
const bodyGridRef = ref<InstanceType<typeof ScheduleTimelineGrid> | null>(null);
let syncingScroll = false;

const headCornerStyle = {
  width: `${SCHEDULE_SIDEBAR_WIDTH}px`,
  height: `${SCHEDULE_HEADER_HEIGHT}px`,
};

function syncScrollFromBody(event: Event) {
  if (syncingScroll) return;
  const left = (event.target as HTMLElement).scrollLeft;
  const headEl = headGridRef.value?.getScrollElement();
  if (!headEl || headEl.scrollLeft === left) return;
  syncingScroll = true;
  headEl.scrollLeft = left;
  syncingScroll = false;
}

function syncScrollFromHead(event: Event) {
  if (syncingScroll) return;
  const left = (event.target as HTMLElement).scrollLeft;
  const bodyEl = bodyGridRef.value?.getScrollElement();
  if (!bodyEl || bodyEl.scrollLeft === left) return;
  syncingScroll = true;
  bodyEl.scrollLeft = left;
  syncingScroll = false;
}

function shiftRange(days: number) {
  const span = diffDays(rangeEnd.value, rangeStart.value) + 1;
  const delta = days > 0 ? span : -span;
  rangeStart.value = addDays(rangeStart.value, delta);
  rangeEnd.value = addDays(rangeEnd.value, delta);
}

async function load() {
  if (!ctx.projectId) {
    data.value = null;
    return;
  }
  loading.value = true;
  try {
    const { data: res } = await fetchMemberSchedule(rangeStart.value, rangeEnd.value);
    data.value = res;
    rangeStart.value = res.range_start;
    rangeEnd.value = res.range_end;
  } catch {
    message.error('加载人员排期失败');
    data.value = null;
  } finally {
    loading.value = false;
  }
}

function openScheduleItem(item: MemberScheduleItem) {
  if (item.item_type === 'bug' && item.bug_id) {
    activeBugId.value = item.bug_id;
    activeRequirementId.value = null;
    detailDrawerVisible.value = true;
    return;
  }
  if (item.requirement_id) {
    activeRequirementId.value = item.requirement_id;
    activeBugId.value = null;
    detailDrawerVisible.value = true;
  }
}

function closeDetailDrawer() {
  detailDrawerVisible.value = false;
  activeRequirementId.value = null;
  activeBugId.value = null;
}

function onDetailDrawerShowChange(show: boolean) {
  if (!show) closeDetailDrawer();
}

function onDetailDeleted() {
  closeDetailDrawer();
  void load();
}

function onDetailUpdated(_row: Requirement) {
  void load();
}

function onBugDetailUpdated() {
  void load();
}

function openUnscheduled(member: MemberScheduleRow) {
  unscheduledMember.value = member;
  unscheduledVisible.value = true;
}

function onUnscheduledOpen(item: MemberScheduleItem) {
  unscheduledVisible.value = false;
  openScheduleItem(item);
}

function toggleScheduleGroup(memberId: string, requirementId: string) {
  const key = scheduleGroupKey(memberId, requirementId);
  const next = new Set(expandedGroupKeys.value);
  if (next.has(key)) next.delete(key);
  else next.add(key);
  expandedGroupKeys.value = next;
}

watch([rangeStart, rangeEnd], () => {
  expandedGroupKeys.value = new Set();
});

watch([() => ctx.projectId, rangeStart, rangeEnd], load, { immediate: true });
</script>

<style scoped>
.member-schedule__card :deep(.n-card-header) {
  padding: 12px 16px 14px;
  border-bottom: 1px solid var(--schedule-border, #e5e6eb);
}
.member-schedule__card :deep(.n-card-header__main) {
  width: 100%;
}
.member-schedule__card :deep(.n-card__content) {
  padding: 12px 16px 16px;
}
.schedule-board {
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 240px);
  overflow: hidden;
  border-radius: 10px;
  border: 1px solid var(--schedule-border, #e5e6eb);
  background: var(--schedule-row-bg, #fff);
}
.schedule-board__head {
  display: flex;
  flex-shrink: 0;
  align-items: stretch;
  width: 100%;
  z-index: 20;
  background: var(--schedule-header-bg, #f5f6f8);
}
.schedule-board__head-corner {
  flex-shrink: 0;
  background: var(--schedule-header-bg, #f5f6f8);
  border-right: 1px solid var(--schedule-border, #e5e6eb);
}
.schedule-board__body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
}
.schedule-body {
  display: flex;
  align-items: stretch;
  width: 100%;
  min-height: min-content;
}
.schedule-empty,
.schedule-hidden-all {
  padding: 48px 0;
}
</style>
