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
            <n-space v-if="isTesterSide" vertical size="large">
              <TodoSection
                title="未开始计划"
                :count="data?.todo.draft_plans?.length ?? 0"
                :empty="!data?.todo.draft_plans?.length"
                :view-all-to="{ name: 'plans', query: { status: 'draft' } }"
              >
                <n-list-item v-for="p in data?.todo.draft_plans" :key="p.id">
                  <router-link class="todo-link" :to="{ name: 'plan-detail', params: { id: p.id } }">
                    {{ p.name }}
                  </router-link>
                  <n-text depth="3"> · {{ planProgressText(p) }}</n-text>
                </n-list-item>
              </TodoSection>

              <TodoSection
                title="进行中计划"
                :count="data?.todo.active_plans_todo?.length ?? 0"
                :empty="!data?.todo.active_plans_todo?.length"
                :view-all-to="{ name: 'plans', query: { status: 'active' } }"
              >
                <n-list-item v-for="p in data?.todo.active_plans_todo" :key="p.id">
                  <router-link class="todo-link" :to="{ name: 'plan-detail', params: { id: p.id } }">
                    {{ p.name }}
                  </router-link>
                  <n-text depth="3"> · {{ planProgressText(p) }}</n-text>
                </n-list-item>
              </TodoSection>

              <TodoSection
                title="未转测需求"
                :count="data?.todo.not_tested_requirements?.length ?? 0"
                :empty="!data?.todo.not_tested_requirements?.length"
                :view-all-to="{ name: 'requirements', query: { status: 'not_tested' } }"
              >
                <n-list-item v-for="r in data?.todo.not_tested_requirements" :key="r.id">
                  <router-link class="todo-link" :to="{ name: 'requirements' }">
                    {{ requirementTodoLabel(r) }}
                  </router-link>
                </n-list-item>
              </TodoSection>

              <TodoSection
                title="测试中需求"
                :count="data?.todo.testing_requirements?.length ?? 0"
                :empty="!data?.todo.testing_requirements?.length"
                :view-all-to="{ name: 'requirements', query: { status: 'testing' } }"
              >
                <n-list-item v-for="r in data?.todo.testing_requirements" :key="r.id">
                  <router-link class="todo-link" :to="{ name: 'requirements' }">
                    {{ requirementTodoLabel(r) }}
                  </router-link>
                </n-list-item>
              </TodoSection>

              <TodoSection
                title="已修复缺陷"
                :count="data?.todo.fixed_bugs?.length ?? 0"
                :empty="!data?.todo.fixed_bugs?.length"
                :view-all-to="{ name: 'bugs', query: { status_key: 'fixed' } }"
              >
                <n-list-item v-for="b in data?.todo.fixed_bugs" :key="b.id">
                  <n-space align="center" :size="8">
                    <router-link class="todo-link" :to="{ name: 'bugs', query: { bugId: b.id } }">
                      {{ formatNumWithTitle(b.num, b.title) }}
                    </router-link>
                    <n-tag size="small" :bordered="false">{{ bugStatusLabel(b.status_key) }}</n-tag>
                  </n-space>
                </n-list-item>
              </TodoSection>
            </n-space>

            <n-space v-else vertical size="large">
              <TodoSection
                title="我跟进的缺陷"
                :count="data?.todo.follower_todo_bugs?.length ?? 0"
                :empty="!data?.todo.follower_todo_bugs?.length"
                :view-all-to="bugsFollowerLink"
              >
                <n-list-item v-for="b in data?.todo.follower_todo_bugs" :key="b.id">
                  <n-space align="center" :size="8">
                    <router-link class="todo-link" :to="{ name: 'bugs', query: { bugId: b.id } }">
                      {{ formatNumWithTitle(b.num, b.title) }}
                    </router-link>
                    <n-tag size="small" :bordered="false">{{ bugStatusLabel(b.status_key) }}</n-tag>
                  </n-space>
                </n-list-item>
              </TodoSection>
            </n-space>
          </n-tab-pane>
        </n-tabs>
      </template>
    </n-space>
  </n-spin>
</template>

<script setup lang="ts">
import {
  NAlert,
  NButton,
  NListItem,
  NSpace,
  NSpin,
  NTabPane,
  NTabs,
  NTag,
  NText,
} from 'naive-ui';
import { computed, nextTick, onMounted, ref, watch } from 'vue';
import { type RouteLocationRaw } from 'vue-router';
import { fetchWorkbench } from '@/api/dashboard';
import { listBugStatuses } from '@/api/templates';
import { useAuthStore } from '@/stores/auth';
import { useContextStore } from '@/stores/context';
import type {
  ActivePlanBrief,
  BugStatusDef,
  DashboardWorkbench,
  RequirementTodoBrief,
} from '@/types/business';
import { formatNumWithTitle, formatNum } from '@/utils/entityNum';
import TodoSection from './components/TodoSection.vue';
import WorkbenchStatCards from './components/WorkbenchStatCards.vue';
import WorkbenchBugFocus from './components/WorkbenchBugFocus.vue';
import WorkbenchPlanFocus from './components/WorkbenchPlanFocus.vue';
import WorkbenchVersionFocus from './components/WorkbenchVersionFocus.vue';

type ChartExpose = { resize?: () => void };

const TESTER_ROLES = new Set(['tester', 'project_admin', 'system_admin']);

const ctx = useContextStore();
const auth = useAuthStore();

const data = ref<DashboardWorkbench | null>(null);
const loading = ref(false);
const activeTab = ref<'overview' | 'todo'>('overview');
const bugStatuses = ref<BugStatusDef[]>([]);
const selectedVersionId = ref<string | null>(null);
const versionFocusRef = ref<ChartExpose | null>(null);
const bugFocusRef = ref<ChartExpose | null>(null);
const planFocusRef = ref<ChartExpose | null>(null);

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

const isTesterSide = computed(() => {
  const role = data.value?.project_role;
  return role ? TESTER_ROLES.has(role) : false;
});

const bugStatusMap = computed(() => {
  const m = new Map<string, string>();
  for (const s of bugStatuses.value) m.set(s.key, s.label);
  return m;
});

function bugStatusLabel(key: string) {
  return bugStatusMap.value.get(key) ?? key;
}

const bugsFollowerLink = computed<RouteLocationRaw>(() => ({
  name: 'bugs',
  query: auth.user?.id ? { follower_id: auth.user.id } : {},
}));

function requirementTodoLabel(r: RequirementTodoBrief) {
  const ver = r.version ? ` · ${r.version.name}` : '';
  return `${formatNum(r.num)} ${r.title}${ver}`;
}

function planProgressText(p: ActivePlanBrief) {
  const executed = p.case_total - p.not_run;
  const rate = executed && p.pass_rate != null ? `，通过率 ${p.pass_rate}%` : '';
  return `用例 ${p.case_total}，未执行 ${p.not_run}${rate}`;
}

async function load() {
  if (!ctx.projectId) return;
  loading.value = true;
  try {
    const projectId = ctx.projectId;
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
  }
});

watch(
  () => ctx.projectId,
  () => {
    selectedVersionId.value = null;
    load();
  }
);

onMounted(load);
</script>

<style scoped>
.workbench-header {
  margin-bottom: 4px;
}
.todo-link {
  color: var(--n-primary-color);
  text-decoration: none;
}
.todo-link:hover {
  text-decoration: underline;
}
</style>
