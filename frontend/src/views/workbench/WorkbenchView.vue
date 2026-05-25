<template>
  <n-spin :show="loading">
    <n-space vertical size="large">
      <n-alert v-if="!ctx.projectId" type="warning">请先在顶栏选择项目</n-alert>
      <template v-else>
        <div class="workbench-header">
          <n-space align="center" justify="space-between" style="width: 100%">
            <n-text strong style="font-size: 16px">{{ projectName }}</n-text>
            <n-button quaternary size="small" :loading="loading" @click="load">刷新</n-button>
          </n-space>
        </div>

        <n-tabs v-model:value="activeTab" type="line" animated>
          <n-tab-pane name="overview" tab="概览">
            <n-space vertical size="large">
              <WorkbenchStatCards :summary="data?.summary" />
              <WorkbenchVersionFocus
                ref="versionFocusRef"
                :focus="data?.overview.version_focus"
                :selected-version-id="selectedVersionId"
                @update:selected-version-id="onVersionSelect"
              />
              <WorkbenchBugFocus ref="bugFocusRef" :focus="data?.overview.bug_focus" />
              <WorkbenchPlanFocus ref="planFocusRef" :focus="data?.overview.plan_focus" />
            </n-space>
          </n-tab-pane>

          <n-tab-pane name="todo" tab="我的待办">
            <n-alert v-if="!hasAnyTodo" type="info">暂无待办</n-alert>
            <n-grid v-else class="tester-todo-grid" :cols="todoGridCols" :x-gap="16" :y-gap="16">
              <n-gi v-if="showPlanTodo" class="tester-todo-grid__pair-cell">
                <TodoSection
                  stretch
                  title="计划"
                  :count="planTodoCount"
                  :empty="!planTodoCount"
                  :view-all-to="{ name: 'plans' }"
                >
                  <div v-for="p in data?.todo.draft_plans" :key="`draft-${p.id}`" class="todo-item">
                    <WorkbenchTodoRow
                      :to="{ name: 'plan-detail', params: { id: p.id } }"
                      :label="p.name"
                      :meta="planProgressText(p)"
                      :tag="planStatusLabel('draft')"
                      :tag-type="planStatusTagType('draft')"
                    />
                  </div>
                  <div v-for="p in data?.todo.active_plans_todo" :key="`active-${p.id}`" class="todo-item">
                    <WorkbenchTodoRow
                      :to="{ name: 'plan-detail', params: { id: p.id } }"
                      :label="p.name"
                      :meta="planProgressText(p)"
                      :tag="planStatusLabel('active')"
                      :tag-type="planStatusTagType('active')"
                    />
                  </div>
                </TodoSection>
              </n-gi>

              <n-gi v-if="showReqTodo" class="tester-todo-grid__pair-cell">
                <TodoSection
                  stretch
                  title="需求"
                  :count="requirementTodoCount"
                  :empty="!requirementTodoCount"
                  :view-all-to="{ name: 'requirements' }"
                >
                  <div
                    v-for="r in data?.todo.not_tested_requirements"
                    :key="`not-tested-${r.id}`"
                    class="todo-item"
                  >
                    <WorkbenchTodoRow
                      :to="{ name: 'requirements' }"
                      :label="requirementTodoLabel(r)"
                      :columns="requirementTodoColumns(r)"
                    />
                  </div>
                  <div v-for="r in data?.todo.testing_requirements" :key="`testing-${r.id}`" class="todo-item">
                    <WorkbenchTodoRow
                      :to="{ name: 'requirements' }"
                      :label="requirementTodoLabel(r)"
                      :columns="requirementTodoColumns(r)"
                    />
                  </div>
                </TodoSection>
              </n-gi>

              <n-gi v-if="showFixedBugTodo" :span="todoGridCols">
                <TodoSection
                  title="已修复缺陷"
                  :count="data?.todo.fixed_bugs?.length ?? 0"
                  :empty="!data?.todo.fixed_bugs?.length"
                  :view-all-to="{ name: 'bugs', query: { status_key: 'fixed' } }"
                >
                  <div v-for="b in data?.todo.fixed_bugs" :key="b.id" class="todo-item">
                    <WorkbenchTodoRow
                      mode="action"
                      :label="b.title"
                      :columns="bugFollowerTodoColumns(b)"
                      :tag="bugStatusLabel(b.status_key)"
                      :tag-type="bugStatusTagTypeForKey(b.status_key)"
                      @click="openTodoBug(b.id, data?.todo.fixed_bugs ?? [], 'fixed')"
                    />
                  </div>
                </TodoSection>
              </n-gi>

              <n-gi v-if="showFollowerBugTodo" :span="todoGridCols">
                <TodoSection
                  title="我跟进的缺陷"
                  :count="data?.todo.follower_todo_bugs?.length ?? 0"
                  :empty="!data?.todo.follower_todo_bugs?.length"
                  :view-all-to="bugsFollowerLink"
                >
                  <div v-for="b in data?.todo.follower_todo_bugs" :key="b.id" class="todo-item">
                    <WorkbenchTodoRow
                      mode="action"
                      :label="b.title"
                      :columns="bugFollowerTodoColumns(b)"
                      :tag="bugStatusLabel(b.status_key)"
                      :tag-type="bugStatusTagTypeForKey(b.status_key)"
                      @click="openTodoBug(b.id, data?.todo.follower_todo_bugs ?? [], 'follower')"
                    />
                  </div>
                </TodoSection>
              </n-gi>
            </n-grid>
          </n-tab-pane>

          <n-tab-pane name="schedule" tab="缺陷排期">
            <WorkbenchBugSchedule
              ref="scheduleRef"
              :project-id="ctx.projectId"
              :bug-status-label="bugStatusLabel"
              :bug-status-tag-type="bugStatusTagTypeForKey"
            />
          </n-tab-pane>
        </n-tabs>
      </template>
    </n-space>

    <n-drawer
      v-model:show="bugDrawerVisible"
      :width="'50%'"
      placement="right"
      :trap-focus="false"
      @update:show="onBugDrawerShowChange"
    >
      <n-drawer-content :closable="false" body-content-style="padding: 0">
        <BugDetailPanel
          v-if="activeBugId"
          :bug-id="activeBugId"
          :has-prev="activeBugIndex > 0"
          :has-next="activeBugIndex >= 0 && activeBugIndex < activeBugList.length - 1"
          @prev="goPrevBug"
          @next="goNextBug"
          @close="closeBugDrawer"
          @deleted="onWorkbenchBugDeleted"
          @updated="onWorkbenchBugUpdated"
        />
      </n-drawer-content>
    </n-drawer>
  </n-spin>
</template>

<script setup lang="ts">
import {
  NAlert,
  NButton,
  NDrawer,
  NDrawerContent,
  NGi,
  NGrid,
  NSpace,
  NSpin,
  NTabPane,
  NTabs,
  NText,
} from 'naive-ui';
import { computed, nextTick, onBeforeUnmount, onMounted, provide, ref, watch } from 'vue';
import { type RouteLocationRaw } from 'vue-router';
import { fetchWorkbench } from '@/api/dashboard';
import { listBugStatuses } from '@/api/templates';
import BugDetailPanel from '@/components/BugDetailPanel.vue';
import {
  WORKBENCH_BUG_DRAWER_KEY,
  type WorkbenchBugListSource,
} from '@/composables/useWorkbenchBugDrawer';
import { useAuthStore } from '@/stores/auth';
import { useContextStore } from '@/stores/context';
import type {
  ActivePlanBrief,
  BugItem,
  BugStatusDef,
  DashboardWorkbench,
  RequirementTodoBrief,
} from '@/types/business';
import { bugStatusTagType } from '@/constants/bugStatus';
import { planStatusLabel, planStatusTagType } from '@/constants/planStatus';
import {
  requirementStatusLabel,
  requirementStatusTagType,
} from '@/constants/requirementStatus';
import { bugFollowerTodoColumns } from '@/utils/bugListLabels';
import type { BugListColumn } from '@/utils/bugListLabels';
import { requirementTodoDisplayLabel } from '@/utils/requirementLabel';
import { formatVersionDisplay } from '@/utils/versionLabel';
import { pickAdjacentItemId } from '@/utils/listNavigation';
import TodoSection from './components/TodoSection.vue';
import WorkbenchBugSchedule from './components/WorkbenchBugSchedule.vue';
import WorkbenchStatCards from './components/WorkbenchStatCards.vue';
import WorkbenchBugFocus from './components/WorkbenchBugFocus.vue';
import WorkbenchPlanFocus from './components/WorkbenchPlanFocus.vue';
import WorkbenchTodoRow from './components/WorkbenchTodoRow.vue';
import WorkbenchVersionFocus from './components/WorkbenchVersionFocus.vue';

type ChartExpose = { resize?: () => void };
type ScheduleExpose = {
  load?: () => Promise<void>;
  dailyBugs?: BugItem[];
  unplannedBugs?: BugItem[];
};

const ctx = useContextStore();
const auth = useAuthStore();

const data = ref<DashboardWorkbench | null>(null);
const loading = ref(false);
const activeTab = ref<'overview' | 'todo' | 'schedule'>('overview');
const bugStatuses = ref<BugStatusDef[]>([]);
const selectedVersionId = ref<string | null>(null);
const versionFocusRef = ref<ChartExpose | null>(null);
const bugFocusRef = ref<ChartExpose | null>(null);
const planFocusRef = ref<ChartExpose | null>(null);
const scheduleRef = ref<ScheduleExpose | null>(null);

const projectRoles = computed(() => data.value?.project_roles ?? []);

const showPlanTodo = computed(
  () => projectRoles.value.includes('system_admin') || projectRoles.value.includes('tester')
);
const showReqTodo = computed(
  () =>
    projectRoles.value.includes('system_admin') ||
    projectRoles.value.includes('tester') ||
    projectRoles.value.includes('product')
);
const showFixedBugTodo = computed(
  () => projectRoles.value.includes('system_admin') || projectRoles.value.includes('tester')
);
const showFollowerBugTodo = computed(
  () => projectRoles.value.includes('system_admin') || projectRoles.value.includes('developer')
);

const hasAnyTodo = computed(
  () =>
    showPlanTodo.value ||
    showReqTodo.value ||
    showFixedBugTodo.value ||
    showFollowerBugTodo.value
);

const todoGridCols = computed(() => {
  const topCount = (showPlanTodo.value ? 1 : 0) + (showReqTodo.value ? 1 : 0);
  return topCount > 1 ? 2 : 1;
});

const bugDrawerVisible = ref(false);
const activeBugId = ref<string | null>(null);
const activeBugList = ref<BugItem[]>([]);
const activeBugListSource = ref<WorkbenchBugListSource | null>(null);

const activeBugIndex = computed(() =>
  activeBugId.value ? activeBugList.value.findIndex((b) => b.id === activeBugId.value) : -1
);

function openBugDrawer(id: string, list: BugItem[], source: WorkbenchBugListSource) {
  activeBugListSource.value = source;
  activeBugList.value = list;
  activeBugId.value = id;
  bugDrawerVisible.value = true;
}

function openTodoBug(id: string, list: BugItem[], source: WorkbenchBugListSource) {
  openBugDrawer(id, list, source);
}

provide(WORKBENCH_BUG_DRAWER_KEY, { open: openBugDrawer });

function closeBugDrawer() {
  bugDrawerVisible.value = false;
  activeBugId.value = null;
  activeBugListSource.value = null;
  activeBugList.value = [];
}

function onBugDrawerShowChange(show: boolean) {
  if (!show) closeBugDrawer();
}

function goPrevBug() {
  const idx = activeBugIndex.value;
  if (idx > 0) activeBugId.value = activeBugList.value[idx - 1].id;
}

function goNextBug() {
  const idx = activeBugIndex.value;
  if (idx >= 0 && idx < activeBugList.value.length - 1) {
    activeBugId.value = activeBugList.value[idx + 1].id;
  }
}

function getBugListBySource(source: WorkbenchBugListSource): BugItem[] {
  switch (source) {
    case 'daily':
      return scheduleRef.value?.dailyBugs ?? [];
    case 'unplanned':
      return scheduleRef.value?.unplannedBugs ?? [];
    case 'fixed':
      return data.value?.todo.fixed_bugs ?? [];
    case 'follower':
      return data.value?.todo.follower_todo_bugs ?? [];
  }
}

async function syncActiveBugListAfterRefresh() {
  const source = activeBugListSource.value;
  if (!bugDrawerVisible.value || !source) return;
  const prevIndex = activeBugIndex.value;
  const list = getBugListBySource(source);
  activeBugList.value = list;
  if (!list.length) {
    closeBugDrawer();
    return;
  }
  if (activeBugId.value && list.some((b) => b.id === activeBugId.value)) return;
  const nextId = pickAdjacentItemId(list, prevIndex);
  if (nextId) activeBugId.value = nextId;
  else closeBugDrawer();
}

async function onWorkbenchBugUpdated() {
  await refreshCurrentTabData();
  await syncActiveBugListAfterRefresh();
}

async function onWorkbenchBugDeleted() {
  await refreshCurrentTabData();
  await syncActiveBugListAfterRefresh();
}

function resizeOverviewCharts() {
  versionFocusRef.value?.resize?.();
  bugFocusRef.value?.resize?.();
  planFocusRef.value?.resize?.();
}

const projectName = computed(() => {
  const pid = ctx.projectId;
  if (!pid) return '工作台';
  return auth.me?.projects.find((p) => p.id === pid)?.name ?? '工作台';
});

const planTodoCount = computed(
  () =>
    (data.value?.todo.draft_plans?.length ?? 0) + (data.value?.todo.active_plans_todo?.length ?? 0)
);

const requirementTodoCount = computed(
  () =>
    (data.value?.todo.not_tested_requirements?.length ?? 0) +
    (data.value?.todo.testing_requirements?.length ?? 0)
);

const bugStatusMap = computed(() => {
  const m = new Map<string, string>();
  for (const s of bugStatuses.value) m.set(s.key, s.label);
  return m;
});

function bugStatusLabel(key: string) {
  return bugStatusMap.value.get(key) ?? key;
}

function bugStatusTagTypeForKey(key: string) {
  return bugStatusTagType(key, bugStatuses.value);
}

const FOLLOWER_TODO_STATUS_KEYS = 'pending_confirm,in_progress,suspended';

const bugsFollowerLink = computed<RouteLocationRaw | undefined>(() => {
  if (!auth.user?.id) return undefined;
  return {
    name: 'bugs',
    query: {
      follower_id: auth.user.id,
      status_key: FOLLOWER_TODO_STATUS_KEYS,
    },
  };
});

function requirementTodoLabel(r: RequirementTodoBrief) {
  return requirementTodoDisplayLabel(r);
}

function requirementTodoColumns(r: RequirementTodoBrief): BugListColumn[] {
  const cols: BugListColumn[] = [
    {
      label: '状态',
      value: requirementStatusLabel(r.status),
      type: requirementStatusTagType(r.status),
    },
  ];
  if (r.version) {
    cols.push({
      label: '版本',
      value: formatVersionDisplay(r.version),
      type: 'info',
    });
  }
  return cols;
}

function planProgressText(p: ActivePlanBrief) {
  const executed = p.case_total - p.not_run;
  const rate = executed && p.pass_rate != null ? `，通过率 ${p.pass_rate}%` : '';
  return `用例 ${p.case_total}，未执行 ${p.not_run}${rate}`;
}

async function loadDashboardData() {
  const projectId = ctx.projectId!;
  const [workbenchRes] = await Promise.all([
    fetchWorkbench(selectedVersionId.value),
    listBugStatuses(projectId).then(({ data: statuses }) => {
      bugStatuses.value = statuses;
    }),
  ]);
  const d = workbenchRes.data;
  data.value = d;
  if (!selectedVersionId.value && d.overview.version_focus.version) {
    selectedVersionId.value = d.overview.version_focus.version.id;
  }
  if (activeTab.value === 'overview') {
    await nextTick();
    resizeOverviewCharts();
  }
}

async function refreshCurrentTabData() {
  if (!ctx.projectId) return;
  if (activeTab.value === 'schedule') {
    await scheduleRef.value?.load?.();
    return;
  }
  await loadDashboardData();
}

async function load() {
  if (!ctx.projectId) return;
  loading.value = true;
  try {
    if (activeTab.value === 'schedule') {
      if (!bugStatuses.value.length) {
        const { data: statuses } = await listBugStatuses(ctx.projectId);
        bugStatuses.value = statuses;
      }
      await scheduleRef.value?.load?.();
      return;
    }
    await loadDashboardData();
  } finally {
    loading.value = false;
  }
}

function onVersionSelect(id: string | null) {
  selectedVersionId.value = id;
  load();
}

watch(activeTab, async (tab) => {
  if (tab === 'overview') {
    await nextTick();
    resizeOverviewCharts();
  } else if (tab === 'schedule') {
    await nextTick();
    await load();
  }
});

watch(
  () => ctx.projectId,
  () => {
    selectedVersionId.value = null;
    closeBugDrawer();
    load();
  }
);

onMounted(load);

onBeforeUnmount(() => {
  closeBugDrawer();
});
</script>

<style scoped>
.workbench-header {
  margin-bottom: 4px;
}
.tester-todo-grid :deep(.tester-todo-grid__pair-cell) {
  display: flex;
}
</style>
