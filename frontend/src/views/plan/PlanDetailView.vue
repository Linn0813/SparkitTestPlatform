<template>
  <n-card v-if="plan">
    <template #header>
      <n-space align="center" :size="12">
        <n-button quaternary size="small" @click="goBack">返回列表</n-button>
        <n-text strong style="font-size: 16px">{{ plan.name }}</n-text>
        <n-text depth="3" style="font-size: 13px">
          用例 {{ stats?.total ?? planCases.length }} · 相关缺陷 {{ planBugs.length }}
        </n-text>
      </n-space>
    </template>
    <template #header-extra>
      <n-space align="center">
        <n-select
          v-model:value="planStatus"
          :options="PLAN_STATUS_OPTIONS"
          :disabled="!canManagePlan"
          style="width: 140px"
          size="small"
          @update:value="onStatusChange"
        />
      </n-space>
    </template>

    <n-alert v-if="isArchived" type="info" style="margin-bottom: 12px">
      计划已归档，仅可查看，不可关联用例或修改执行结果。
    </n-alert>

    <n-grid v-if="stats" :cols="6" :x-gap="12" style="margin-bottom: 16px">
      <n-gi>
        <n-statistic label="未执行" :value="stats.not_run" />
      </n-gi>
      <n-gi>
        <n-statistic label="通过" :value="stats.pass_count" />
      </n-gi>
      <n-gi>
        <n-statistic label="失败" :value="stats.fail_count" />
      </n-gi>
      <n-gi>
        <n-statistic label="阻塞" :value="stats.block_count" />
      </n-gi>
      <n-gi>
        <n-statistic label="跳过" :value="stats.skip_count" />
      </n-gi>
      <n-gi>
        <n-statistic
          label="通过率"
          :value="stats.total - stats.not_run > 0 ? `${stats.pass_rate}%` : '—'"
        />
      </n-gi>
    </n-grid>

    <n-tabs v-model:value="activeTab" type="line">
      <n-tab-pane name="cases" tab="计划用例">
        <n-card size="small" :bordered="false" content-style="padding: 0">
          <template #header-extra>
            <n-space align="center">
              <n-select
                v-model:value="filterResult"
                :options="resultFilterOptions"
                clearable
                placeholder="按结果筛选"
                size="small"
                style="width: 140px"
              />
              <n-button :disabled="isArchived" @click="openAddCases">关联用例</n-button>
            </n-space>
          </template>
          <n-data-table
            :columns="columns"
            :data="displayedPlanCases"
            :loading="loading"
            :row-key="(row: PlanCase) => row.id"
            :row-props="planCaseRowProps"
            style="margin-top: 8px"
          />
        </n-card>
      </n-tab-pane>
      <n-tab-pane name="bugs" tab="相关缺陷">
        <n-empty
          v-if="!loadingBugs && !planBugs.length"
          description="暂无关联缺陷，请在缺陷管理中关联本测试计划"
          style="margin: 24px 0"
        />
        <n-data-table
          v-else
          :columns="bugColumns"
          :data="planBugs"
          :loading="loadingBugs"
          :scroll-x="600"
          :row-key="(row: BugItem) => row.id"
          :row-props="bugRowProps"
          style="margin-top: 8px"
        />
      </n-tab-pane>
    </n-tabs>

    <n-modal
      v-model:show="showAddCases"
      preset="dialog"
      title="关联用例"
      positive-text="添加"
      style="width: 800px"
      @positive-click="onAddCases"
    >
      <n-form label-placement="top">
        <n-grid :cols="2" :x-gap="12">
          <n-gi>
            <n-form-item label="按模块筛选">
              <n-tree-select
                v-model:value="filterModuleId"
                :options="treeData"
                key-field="key"
                label-field="label"
                clearable
                filterable
                placeholder="全部模块"
                style="width: 100%"
                @update:value="onPickerFilterChange"
              />
            </n-form-item>
          </n-gi>
          <n-gi>
            <n-form-item label="关联需求">
              <n-select
                v-model:value="filterRequirementId"
                :options="requirementOptions"
                clearable
                filterable
                placeholder="全部需求"
                style="width: 100%"
                @update:value="onPickerFilterChange"
              />
            </n-form-item>
          </n-gi>
          <n-gi>
            <n-form-item label="优先级">
              <n-select
                v-model:value="filterPriority"
                :options="priorityOptions"
                clearable
                placeholder="全部"
                style="width: 100%"
                @update:value="onPickerFilterChange"
              />
            </n-form-item>
          </n-gi>
          <n-gi>
            <n-form-item label="标题">
              <n-input
                v-model:value="filterQ"
                placeholder="关键字匹配标题"
                clearable
                @update:value="onFilterQInput"
              />
            </n-form-item>
          </n-gi>
        </n-grid>
        <n-form-item label="选择用例">
          <n-space vertical style="width: 100%">
            <n-space justify="space-between" align="center" wrap>
              <n-text depth="3">
                共 {{ selectableCases.length }} 条可关联
                <template v-if="selectedCaseIds.length">，已选 {{ selectedCaseIds.length }} 条</template>
              </n-text>
              <n-space :size="8">
                <n-button
                  size="small"
                  quaternary
                  :disabled="!selectableCases.length"
                  @click="selectAllCases"
                >
                  全选
                </n-button>
                <n-button size="small" quaternary :disabled="!selectedCaseIds.length" @click="clearCaseSelection">
                  清空
                </n-button>
              </n-space>
            </n-space>
            <n-data-table
              size="small"
              :columns="pickerColumns"
              :data="selectableCases"
              :loading="pickerLoading"
              :row-key="(row: TestCase) => row.id"
              :checked-row-keys="selectedCaseIds"
              :max-height="320"
              :scroll-x="640"
              @update:checked-row-keys="onCheckedCaseKeysChange"
            />
          </n-space>
        </n-form-item>
      </n-form>
    </n-modal>

    <n-drawer
      v-model:show="caseDrawerVisible"
      :width="'50%'"
      placement="right"
      :trap-focus="false"
      @update:show="onCaseDrawerShowChange"
    >
      <n-drawer-content :closable="false" body-content-style="padding: 0">
        <CaseDetailPanel
          v-if="activeCaseId"
          :case-id="activeCaseId"
          :plan-execution="planExecutionContext"
          :has-prev="activeCaseIndex > 0"
          :has-next="activeCaseIndex >= 0 && activeCaseIndex < navigablePlanCases.length - 1"
          @prev="goPrevCase"
          @next="goNextCase"
          @close="closeCaseDrawer"
          @updated="onCaseUpdated"
          @execution-updated="load"
        />
      </n-drawer-content>
    </n-drawer>

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
          :has-next="activeBugIndex >= 0 && activeBugIndex < planBugs.length - 1"
          @prev="goPrevBug"
          @next="goNextBug"
          @close="closeBugDrawer"
          @deleted="onBugDeleted"
          @updated="onBugUpdated"
        />
      </n-drawer-content>
    </n-drawer>
  </n-card>
</template>

<script setup lang="ts">
import { computed, h, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  NAlert,
  NButton,
  NCard,
  NDataTable,
  NDrawer,
  NDrawerContent,
  NEmpty,
  NForm,
  NFormItem,
  NGi,
  NGrid,
  NInput,
  NModal,
  NSelect,
  NSpace,
  NStatistic,
  NTabPane,
  NTabs,
  NText,
  NTreeSelect,
  useDialog,
  useMessage,
  type DataTableColumns,
  type DataTableRowKey,
} from 'naive-ui';
import { listCases, type ListCasesParams } from '@/api/cases';
import {
  addPlanCases,
  getPlan,
  getPlanStats,
  listPlanCases,
  removePlanCase,
  updatePlan,
  updatePlanResult,
} from '@/api/plans';
import { listBugs } from '@/api/bugs';
import { listRequirements } from '@/api/requirements';
import { listBugStatuses } from '@/api/templates';
import BugDetailPanel from '@/components/BugDetailPanel.vue';
import CaseDetailPanel from '@/components/CaseDetailPanel.vue';
import { useCaseModules } from '@/composables/useCaseModules';
import { usePermissions } from '@/composables/usePermissions';
import {
  PLAN_RESULT_OPTIONS,
  PLAN_STATUS_OPTIONS,
  isPlanArchived,
  planStatusLabel,
} from '@/constants/planStatus';
import type { BugItem, BugStatusDef, PlanCase, PlanStats, Requirement, TestCase, TestPlan } from '@/types/business';
import { NUM_TABLE_COLUMN } from '@/utils/entityNum';

const route = useRoute();
const router = useRouter();
const message = useMessage();
const dialog = useDialog();
const { canManagePlans } = usePermissions();
const planId = route.params.id as string;

const plan = ref<TestPlan | null>(null);
const planStatus = ref('draft');
const planCases = ref<PlanCase[]>([]);
const stats = ref<PlanStats | null>(null);
const pickerCases = ref<TestCase[]>([]);
const requirements = ref<Requirement[]>([]);
const loading = ref(false);
const pickerLoading = ref(false);
const showAddCases = ref(false);
const selectedCaseIds = ref<string[]>([]);
const filterModuleId = ref<string | null>(null);
const filterPriority = ref<string | null>(null);
const filterQ = ref('');
const filterRequirementId = ref<string | null>(null);
const filterResult = ref<string | null>(null);
const activeCaseId = ref<string | null>(null);
const activePlanCase = ref<PlanCase | null>(null);
const caseDrawerVisible = ref(false);
const activeTab = ref('cases');
const planBugs = ref<BugItem[]>([]);
const bugStatuses = ref<BugStatusDef[]>([]);
const loadingBugs = ref(false);
const activeBugId = ref<string | null>(null);
const bugDrawerVisible = ref(false);

let filterQTimer: ReturnType<typeof setTimeout> | null = null;

const { treeData, loadModules } = useCaseModules();

const isArchived = computed(() => isPlanArchived(plan.value?.status));
const canManagePlan = computed(() => canManagePlans(plan.value?.project_id));

const priorityOptions = ['P0', 'P1', 'P2', 'P3'].map((v) => ({ label: v, value: v }));
const requirementOptions = computed(() =>
  requirements.value.map((r) => ({ label: r.title, value: r.id }))
);

const resultFilterOptions = PLAN_RESULT_OPTIONS;

const existingCaseIds = computed(() => new Set(planCases.value.map((pc) => pc.case_id)));

const selectableCases = computed(() =>
  pickerCases.value.filter((c) => !existingCaseIds.value.has(c.id))
);

const displayedPlanCases = computed(() => {
  if (!filterResult.value) return planCases.value;
  return planCases.value.filter((pc) => (pc.result?.result ?? 'not_run') === filterResult.value);
});

const navigablePlanCases = computed(() =>
  displayedPlanCases.value.filter((pc) => !!pc.case_id)
);

const activeCaseIndex = computed(() => {
  if (!activePlanCase.value) return -1;
  return navigablePlanCases.value.findIndex((pc) => pc.id === activePlanCase.value!.id);
});

const planExecutionContext = computed(() => {
  if (!activePlanCase.value || !plan.value) return null;
  return {
    planId: planId,
    planCaseId: activePlanCase.value.id,
    result: activePlanCase.value.result?.result ?? 'not_run',
    comment: activePlanCase.value.result?.comment ?? null,
    readOnly: isArchived.value || !canManagePlan.value,
  };
});

const bugStatusLabelMap = computed(() => {
  const m = new Map<string, string>();
  for (const s of bugStatuses.value) m.set(s.key, s.label);
  return m;
});

const activeBugIndex = computed(() =>
  activeBugId.value ? planBugs.value.findIndex((b) => b.id === activeBugId.value) : -1
);

function followersSummary(row: BugItem): string {
  const names = row.followers?.map((f) => f.name).filter(Boolean);
  if (names?.length) return names.join('、');
  if (row.follower_ids?.length) return `${row.follower_ids.length} 人`;
  return '—';
}

const bugColumns = computed<DataTableColumns<BugItem>>(() => [
  { ...NUM_TABLE_COLUMN, width: 56 },
  {
    title: '标题',
    key: 'title',
    width: 220,
    minWidth: 120,
    maxWidth: 280,
    ellipsis: { tooltip: true },
    render: (row) =>
      h(
        NButton,
        {
          text: true,
          type: 'primary',
          onClick: (e: Event) => {
            e.stopPropagation();
            openBug(row.id);
          },
        },
        () => row.title
      ),
  },
  {
    title: '状态',
    key: 'status_key',
    width: 96,
    render: (row) => bugStatusLabelMap.value.get(row.status_key) ?? row.status_key,
  },
  {
    title: '跟进人',
    key: 'followers',
    width: 120,
    ellipsis: { tooltip: true },
    render: (row) => followersSummary(row),
  },
]);

const pickerColumns: DataTableColumns<TestCase> = [
  { type: 'selection' },
  { title: '优先级', key: 'priority', width: 72 },
  { title: '标题', key: 'title', minWidth: 200, ellipsis: { tooltip: true } },
  {
    title: '模块',
    key: 'module_path',
    width: 140,
    ellipsis: { tooltip: true },
    render: (row) => row.module_path ?? '—',
  },
];

function goBack() {
  router.push({ name: 'plans' });
}

function openPlanCase(row: PlanCase) {
  if (!row.case_id) return;
  activePlanCase.value = row;
  activeCaseId.value = row.case_id;
  caseDrawerVisible.value = true;
  syncCaseIdToRoute();
}

function planCaseRowProps(row: PlanCase) {
  return {
    style: 'cursor: pointer',
    onClick: () => openPlanCase(row),
  };
}

function syncCaseIdToRoute() {
  const q = { ...route.query };
  if (activeCaseId.value) q.caseId = activeCaseId.value;
  else delete q.caseId;
  router.replace({ name: 'plan-detail', params: { id: planId }, query: q });
}

function applyRouteCaseId() {
  const raw = route.query.caseId;
  const caseId = typeof raw === 'string' && raw ? raw : null;
  if (!caseId) return;
  const row = planCases.value.find((pc) => pc.case_id === caseId);
  if (row) {
    activePlanCase.value = row;
    activeCaseId.value = caseId;
    caseDrawerVisible.value = true;
  }
}

function closeCaseDrawer() {
  caseDrawerVisible.value = false;
  activeCaseId.value = null;
  activePlanCase.value = null;
  syncCaseIdToRoute();
}

function onCaseDrawerShowChange(show: boolean) {
  if (!show) closeCaseDrawer();
}

function goPrevCase() {
  const idx = activeCaseIndex.value;
  if (idx > 0) openPlanCase(navigablePlanCases.value[idx - 1]);
}

function goNextCase() {
  const idx = activeCaseIndex.value;
  if (idx >= 0 && idx < navigablePlanCases.value.length - 1) {
    openPlanCase(navigablePlanCases.value[idx + 1]);
  }
}

async function onCaseUpdated() {
  await load();
}

function bugRowProps(row: BugItem) {
  return {
    style: 'cursor: pointer',
    onClick: () => openBug(row.id),
  };
}

function openBug(id: string) {
  activeBugId.value = id;
  bugDrawerVisible.value = true;
}

function closeBugDrawer() {
  bugDrawerVisible.value = false;
  activeBugId.value = null;
}

function onBugDrawerShowChange(show: boolean) {
  if (!show) closeBugDrawer();
}

function goPrevBug() {
  const idx = activeBugIndex.value;
  if (idx > 0) openBug(planBugs.value[idx - 1].id);
}

function goNextBug() {
  const idx = activeBugIndex.value;
  if (idx >= 0 && idx < planBugs.value.length - 1) openBug(planBugs.value[idx + 1].id);
}

async function onBugDeleted() {
  closeBugDrawer();
  await loadBugs();
}

async function onBugUpdated() {
  await loadBugs();
}

async function loadBugs() {
  loadingBugs.value = true;
  try {
    const { data } = await listBugs({ plan_id: planId });
    planBugs.value = data;
    if (activeBugId.value && !data.some((b) => b.id === activeBugId.value)) {
      closeBugDrawer();
    }
  } finally {
    loadingBugs.value = false;
  }
}

async function loadBugStatuses() {
  const pid = plan.value?.project_id;
  if (!pid) {
    bugStatuses.value = [];
    return;
  }
  const { data } = await listBugStatuses(pid);
  bugStatuses.value = data;
}

function onCheckedCaseKeysChange(keys: DataTableRowKey[]) {
  selectedCaseIds.value = keys.map((k) => String(k));
}

function selectAllCases() {
  selectedCaseIds.value = selectableCases.value.map((c) => c.id);
}

function clearCaseSelection() {
  selectedCaseIds.value = [];
}

function pruneCaseSelection() {
  const allowed = new Set(selectableCases.value.map((c) => c.id));
  selectedCaseIds.value = selectedCaseIds.value.filter((id) => allowed.has(id));
}

const columns = computed<DataTableColumns<PlanCase>>(() => [
  { title: '优先级', key: 'priority', width: 72, render: (r) => r.case?.priority ?? '—' },
  {
    title: '用例标题',
    key: 'case',
    width: 220,
    ellipsis: { tooltip: true },
    render: (row) =>
      h(
        'span',
        {
          class: 'case-title-link',
          onClick: (e: MouseEvent) => {
            e.stopPropagation();
            openPlanCase(row);
          },
        },
        row.case?.title ?? row.case_id
      ),
  },
  {
    title: '模块',
    key: 'module_path',
    width: 160,
    ellipsis: { tooltip: true },
    render: (r) => r.case?.module_path ?? '—',
  },
  {
    title: '执行结果',
    key: 'result',
    width: 130,
    render: (row) =>
      h('div', { onClick: (e: Event) => e.stopPropagation() }, [
        h(NSelect, {
          size: 'small',
          value: row.result?.result ?? 'not_run',
          options: PLAN_RESULT_OPTIONS,
          disabled: isArchived.value,
          style: { width: '120px' },
          onUpdateValue: (v: string) => onResult(row.id, v),
        }),
      ]),
  },
  {
    title: '操作',
    key: 'actions',
    width: 120,
    fixed: 'right',
    render: (row) =>
      h(NSpace, { size: 4, onClick: (e: Event) => e.stopPropagation() }, () => [
        h(NButton, { size: 'small', quaternary: true, onClick: () => openPlanCase(row) }, () => '查看'),
        !isArchived.value
          ? h(
              NButton,
              { size: 'small', quaternary: true, type: 'error', onClick: () => onRemovePlanCase(row) },
              () => '移出'
            )
          : null,
      ]),
  },
]);

function buildPickerParams(): ListCasesParams | undefined {
  const p: ListCasesParams = {};
  if (filterModuleId.value) {
    p.module_id = filterModuleId.value;
    p.include_submodules = true;
  }
  if (filterPriority.value) p.priority = filterPriority.value;
  if (filterRequirementId.value) p.requirement_id = filterRequirementId.value;
  if (filterQ.value.trim()) p.q = filterQ.value.trim();
  return Object.keys(p).length ? p : undefined;
}

async function loadCasePickerOptions() {
  pickerLoading.value = true;
  try {
    const { data } = await listCases(buildPickerParams());
    pickerCases.value = data;
    pruneCaseSelection();
  } finally {
    pickerLoading.value = false;
  }
}

function onPickerFilterChange() {
  loadCasePickerOptions();
}

function onFilterQInput() {
  if (filterQTimer) clearTimeout(filterQTimer);
  filterQTimer = setTimeout(() => {
    loadCasePickerOptions();
  }, 300);
}

async function load() {
  loading.value = true;
  try {
    const [p, pc, st] = await Promise.all([
      getPlan(planId),
      listPlanCases(planId),
      getPlanStats(planId),
    ]);
    plan.value = p.data;
    planStatus.value = p.data.status;
    planCases.value = pc.data;
    stats.value = st.data;
    if (activePlanCase.value) {
      const refreshed = pc.data.find((item) => item.id === activePlanCase.value!.id);
      if (refreshed) activePlanCase.value = refreshed;
      else closeCaseDrawer();
    }
    await Promise.all([loadBugs(), loadBugStatuses()]);
  } finally {
    loading.value = false;
  }
}

async function onStatusChange(status: string) {
  if (!plan.value || status === plan.value.status) return;
  try {
    const { data } = await updatePlan(planId, { status });
    plan.value = data;
    message.success(`状态已更新为「${planStatusLabel(status)}」`);
  } catch {
    planStatus.value = plan.value.status;
    message.error('状态更新失败');
  }
}

async function openAddCases() {
  filterModuleId.value = null;
  filterPriority.value = null;
  filterQ.value = '';
  filterRequirementId.value = null;
  selectedCaseIds.value = [];
  showAddCases.value = true;
  const { data } = await listRequirements();
  requirements.value = data;
  await loadCasePickerOptions();
}

async function onAddCases() {
  if (!selectedCaseIds.value.length) {
    message.warning('请选择用例');
    return false;
  }
  await addPlanCases(planId, selectedCaseIds.value);
  showAddCases.value = false;
  selectedCaseIds.value = [];
  message.success('已关联');
  await load();
  return true;
}

async function onResult(planCaseId: string, result: string) {
  await updatePlanResult(planId, { plan_case_id: planCaseId, result });
  message.success('已更新');
  await load();
}

function onRemovePlanCase(row: PlanCase) {
  dialog.warning({
    title: '移出计划',
    content: `确定将用例「${row.case?.title ?? row.case_id}」移出本计划？`,
    positiveText: '移出',
    negativeText: '取消',
    onPositiveClick: async () => {
      await removePlanCase(planId, row.id);
      message.success('已移出');
      if (activeCaseId.value === row.case_id) closeCaseDrawer();
      await load();
    },
  });
}

onMounted(async () => {
  applyRouteCaseId();
  await loadModules();
  await load();
});

watch(() => route.query.caseId, () => {
  applyRouteCaseId();
});
</script>

<style scoped>
.case-title-link {
  color: var(--n-primary-color);
  cursor: pointer;
}

.case-title-link:hover {
  text-decoration: underline;
}
</style>
