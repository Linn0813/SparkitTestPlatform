<template>
  <n-card title="测试用例">
    <template #header-extra>
      <n-space>
        <n-button
          v-if="canCases && checkedRowKeys.length"
          type="error"
          :loading="batchDeleting"
          @click="onBatchDelete"
        >
          删除选中（{{ checkedRowKeys.length }}）
        </n-button>
        <n-button v-if="canCases" @click="showImportModal = true">导入</n-button>
        <n-button v-if="canCases" type="primary" @click="openCreateDrawer">新建用例</n-button>
      </n-space>
    </template>

    <SchemaFieldFilters
      scene="functional_case"
      :model="filters"
      :catalog="filterCatalog"
      :project-id="ctx.projectId"
      :visible-keys="visibleKeys"
      :requirement-options="requirementOptions"
      :module-tree-options="treeData"
      @apply="applyFilters"
      @reset="resetFilters"
      @module-change="applyFilters"
      @update:visible-keys="onVisibleKeysChange"
    />

    <n-data-table
      class="case-list-table"
      :columns="columns"
      :data="cases"
      :loading="loading"
      :scroll-x="1960"
      :row-key="(row: TestCase) => row.id"
      :row-props="rowProps"
      :checked-row-keys="checkedRowKeys"
      @update:checked-row-keys="onCheckedRowKeysChange"
      style="margin-top: 12px"
    />

    <div class="case-list-pagination">
      <n-pagination
        v-model:page="page"
        v-model:page-size="pageSize"
        :item-count="total"
        :page-sizes="[10, 20, 50, 100]"
        show-size-picker
        show-quick-jumper
      />
    </div>
  </n-card>

  <CaseImportModal v-model:show="showImportModal" @imported="onCasesImported" />

  <n-drawer
    v-model:show="detailDrawerVisible"
    :width="'50%'"
    placement="right"
    :trap-focus="false"
    @update:show="onDetailDrawerShowChange"
  >
    <n-drawer-content :closable="false" body-content-style="padding: 0">
      <CaseDetailPanel
        v-if="activeCaseId"
        :case-id="activeCaseId"
        :has-prev="activeIndex > 0"
        :has-next="activeIndex >= 0 && activeIndex < cases.length - 1"
        @prev="goPrev"
        @next="goNext"
        @close="closeDetailDrawer"
        @deleted="onCaseDeleted"
        @updated="onCaseUpdated"
      />
    </n-drawer-content>
  </n-drawer>

  <n-drawer v-model:show="createDrawerVisible" :width="600" placement="right">
    <n-drawer-content title="新建用例">
      <n-form label-placement="top">
        <n-form-item label="用例标题" required>
          <n-input v-model:value="caseForm.title" placeholder="请输入用例标题" />
        </n-form-item>
        <n-form-item label="模块" required>
          <n-select
            v-model:value="caseForm.module_id"
            :options="moduleOptions"
            placeholder="选择模块"
            filterable
            style="width: 100%"
          />
        </n-form-item>
        <n-form-item label="优先级">
          <n-select v-model:value="caseForm.priority" :options="priorityOptions" style="width: 100%" />
        </n-form-item>
        <n-form-item label="前置条件">
          <PasteImageTextarea
            v-model="caseForm.precondition"
            :project-id="ctx.projectId"
            placeholder="可选"
          />
        </n-form-item>
        <n-form-item label="步骤">
          <n-input v-model:value="caseForm.step_text" type="textarea" :rows="4" placeholder="请输入步骤" />
        </n-form-item>
        <n-form-item label="预期结果">
          <n-input
            v-model:value="caseForm.expected_result"
            type="textarea"
            :rows="4"
            placeholder="请输入预期结果"
          />
        </n-form-item>
        <n-form-item label="关联需求">
          <n-select
            v-model:value="caseForm.requirement_ids"
            :options="requirementOptions"
            multiple
            filterable
            clearable
            placeholder="可选，多选"
            style="width: 100%"
          />
        </n-form-item>
        <DynamicFieldForm
          v-if="templateUiFields.length"
          v-model="caseForm.custom_fields"
          :fields="templateUiFields"
        />
      </n-form>
      <template #footer>
        <n-button type="primary" @click="saveNewCase">保存</n-button>
      </template>
    </n-drawer-content>
  </n-drawer>
</template>

<script setup lang="ts">
import { computed, h, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  NButton,
  NCard,
  NDataTable,
  NDrawer,
  NDrawerContent,
  NForm,
  NFormItem,
  NInput,
  NPagination,
  NSelect,
  NSpace,
  NTooltip,
  useDialog,
  useMessage,
  type DataTableColumns,
} from 'naive-ui';
import { createCase, deleteCase, listCases, type ListCasesParams } from '@/api/cases';
import { listRequirementOptions, type RequirementSelectOption } from '@/api/requirements';
import CaseDetailPanel from '@/components/CaseDetailPanel.vue';
import CaseImportModal from '@/components/CaseImportModal.vue';
import DynamicFieldForm from '@/components/DynamicFieldForm.vue';
import PasteImageTextarea from '@/components/PasteImageTextarea.vue';
import SchemaFieldFilters from '@/components/SchemaFieldFilters.vue';
import { useCaseModules } from '@/composables/useCaseModules';
import {
  emptyCaseListFilters,
  syncCustomFilterKeys,
  type CaseListFilterState,
} from '@/composables/useCaseListFilters';
import { useCaseListFilterVisibility } from '@/composables/useCaseListFilterVisibility';
import { useProjectFieldSchema } from '@/composables/useProjectFieldSchema';
import { emptyCustomFields, validateCustomFields } from '@/constants/fieldTypes';
import { usePermissions } from '@/composables/usePermissions';
import { FILTER_EMPTY_VALUE } from '@/schemas/entityFieldSchema';
import { useContextStore } from '@/stores/context';
import type { TestCase } from '@/types/business';
import { modulePathLabel } from '@/utils/moduleTree';
import { decodeFilterQuery, encodeFilterValues, hasFilterValues } from '@/utils/filterQueryCodec';
import { pickAdjacentItemId } from '@/utils/listNavigation';
import { requirementOptionLabel } from '@/utils/requirementLabel';

const ctx = useContextStore();
const { canManageCases } = usePermissions();
const canCases = computed(() => canManageCases(ctx.projectId));
const route = useRoute();
const router = useRouter();
const message = useMessage();
const dialog = useDialog();

const { modules, moduleOptions, treeData, loadModules } = useCaseModules();

const cases = ref<TestCase[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);
const requirements = ref<RequirementSelectOption[]>([]);
const loading = ref(false);
const applyingRoute = ref(false);
const paginationReady = ref(false);
const detailDrawerVisible = ref(false);
const createDrawerVisible = ref(false);
const activeCaseId = ref<string | null>(null);
const showImportModal = ref(false);
const checkedRowKeys = ref<string[]>([]);
const batchDeleting = ref(false);

const projectIdRef = computed(() => ctx.projectId);
const fieldSchema = useProjectFieldSchema('functional_case', projectIdRef);
const templateUiFields = computed(() => fieldSchema.templateFieldsForUi.value);

const filters = ref<CaseListFilterState>(emptyCaseListFilters());
const { visibleKeys, catalog: filterCatalog, setVisibleKeys, sanitizeVisibleKeys } =
  useCaseListFilterVisibility(projectIdRef, fieldSchema.templateFields, filters);

const caseForm = ref({
  title: '',
  module_id: '' as string,
  priority: 'P2',
  precondition: '',
  step_text: '',
  expected_result: '',
  requirement_ids: [] as string[],
  custom_fields: {} as Record<string, unknown>,
});

const priorityOptions = ['P0', 'P1', 'P2', 'P3'].map((v) => ({ label: v, value: v }));

const requirementOptions = computed(() =>
  requirements.value.map((r) => ({
    label: requirementOptionLabel(r, { showNum: false }),
    value: r.id,
  }))
);

const activeIndex = computed(() => {
  if (!activeCaseId.value) return -1;
  return cases.value.findIndex((c) => c.id === activeCaseId.value);
});

function moduleLabel(row: TestCase): string {
  return row.module_path || modulePathLabel(modules.value, row.module_id) || '—';
}

function tableLineText(text: string | null | undefined): string {
  if (!text?.trim()) return '—';
  return text.replace(/\s+/g, ' ').trim();
}

function textCell(text: string | null | undefined) {
  const display = tableLineText(text);
  if (display === '—') return display;
  return h(
    NTooltip,
    { placement: 'top-start', style: { maxWidth: '480px' } },
    {
      trigger: () => h('span', { class: 'cell-ellipsis' }, display),
      default: () => text?.trim() ? text : display,
    }
  );
}

function formatDate(iso: string) {
  try {
    return new Date(iso).toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return iso;
  }
}

function openCaseDetail(id: string) {
  activeCaseId.value = id;
  detailDrawerVisible.value = true;
  syncQueryToRoute();
}

function rowProps(row: TestCase) {
  return {
    style: 'cursor: pointer',
    onClick: () => openCaseDetail(row.id),
  };
}

const columns = computed<DataTableColumns<TestCase>>(() => {
  const cols: DataTableColumns<TestCase> = [];
  if (canCases.value) {
    cols.push({ type: 'selection' });
  }
  cols.push(
  {
    title: '模块',
    key: 'module_path',
    width: 160,
    ellipsis: { tooltip: true },
    render: (row) => h('span', { class: 'cell-ellipsis' }, moduleLabel(row)),
  },
  {
    title: '标题',
    key: 'title',
    width: 280,
    ellipsis: { tooltip: true },
    render: (row) =>
      h(
        'span',
        {
          class: 'case-title-link',
          onClick: (e: MouseEvent) => {
            e.stopPropagation();
            openCaseDetail(row.id);
          },
        },
        row.title
      ),
  },
  { title: '优先级', key: 'priority', width: 72 },
  ...fieldSchema.buildListColumns<TestCase>(),
  {
    title: '前置条件',
    key: 'precondition',
    width: 280,
    ellipsis: { tooltip: true },
    render: (row) => textCell(row.precondition),
  },
  {
    title: '步骤',
    key: 'step_text',
    width: 280,
    ellipsis: { tooltip: true },
    render: (row) => textCell(row.step_text),
  },
  {
    title: '预期结果',
    key: 'expected_result',
    width: 280,
    ellipsis: { tooltip: true },
    render: (row) => textCell(row.expected_result),
  },
  {
    title: '更新时间',
    key: 'updated_at',
    width: 150,
    render: (row) => formatDate(row.updated_at),
  },
  {
    title: '操作',
    key: 'a',
    width: canCases.value ? 140 : 80,
    fixed: 'right',
    render: (row) => {
      const buttons = [
        h(
          NButton,
          {
            size: 'small',
            quaternary: true,
            onClick: (e: MouseEvent) => {
              e.stopPropagation();
              openCaseDetail(row.id);
            },
          },
          () => '查看'
        ),
      ];
      if (canCases.value) {
        buttons.push(
          h(
            NButton,
            {
              size: 'small',
              quaternary: true,
              type: 'error',
              onClick: (e: MouseEvent) => {
                e.stopPropagation();
                onRemove(row);
              },
            },
            () => '删除'
          )
        );
      }
      return h(NSpace, { size: 4, wrap: false, class: 'case-row-actions' }, () => buttons);
    },
  },
  );
  return cols;
});

function onCheckedRowKeysChange(keys: Array<string | number>) {
  checkedRowKeys.value = keys.map(String);
}

function removeCasesLocally(ids: string[]) {
  if (!ids.length) return;
  const idSet = new Set(ids);
  const removed = cases.value.filter((c) => idSet.has(c.id)).length;
  cases.value = cases.value.filter((c) => !idSet.has(c.id));
  total.value = Math.max(0, total.value - removed);
}

function onRemove(row: TestCase) {
  dialog.warning({
    title: '删除用例',
    content: `确定删除「${row.title}」？此操作不可恢复。`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await deleteCase(row.id);
        removeCasesLocally([row.id]);
        checkedRowKeys.value = checkedRowKeys.value.filter((id) => id !== row.id);
        if (activeCaseId.value === row.id) closeDetailDrawer();
        message.success('已删除');
        await loadCases();
        return true;
      } catch (e: unknown) {
        const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
        message.error(typeof detail === 'string' ? detail : '删除失败');
        return false;
      }
    },
  });
}

function onBatchDelete() {
  const ids = [...checkedRowKeys.value];
  if (!ids.length) return;
  dialog.warning({
    title: '批量删除用例',
    content: `确定删除选中的 ${ids.length} 条用例？此操作不可恢复。`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      batchDeleting.value = true;
      try {
        const results = await Promise.allSettled(ids.map((id) => deleteCase(id)));
        const succeededIds = ids.filter((_, i) => results[i].status === 'fulfilled');
        const failed = ids.length - succeededIds.length;
        removeCasesLocally(succeededIds);
        checkedRowKeys.value = [];
        if (activeCaseId.value && succeededIds.includes(activeCaseId.value)) closeDetailDrawer();
        await loadCases();
        if (failed === 0) {
          message.success(`已删除 ${succeededIds.length} 条用例`);
        } else if (succeededIds.length > 0) {
          message.warning(`已删除 ${succeededIds.length} 条，${failed} 条删除失败`);
        } else {
          message.error('删除失败');
        }
        return failed === 0;
      } finally {
        batchDeleting.value = false;
      }
    },
  });
}

function buildListParams(): ListCasesParams {
  const p: ListCasesParams = {
    page: page.value,
    page_size: pageSize.value,
  };
  if (filters.value.module_id) {
    p.module_id = filters.value.module_id;
    p.include_submodules = filters.value.include_submodules;
  }
  const f = filters.value;
  const encodedRequirement = encodeFilterValues(f.requirement_ids);
  if (encodedRequirement) p.requirement_id = encodedRequirement;
  const encodedPriority = encodeFilterValues(f.priorities);
  if (encodedPriority) p.priority = encodedPriority;
  if (f.q?.trim()) p.q = f.q.trim();
  const custom: Record<string, string | string[]> = {};
  for (const [fieldId, val] of Object.entries(f.custom)) {
    if (hasFilterValues(val)) custom[fieldId] = val.length === 1 ? val[0] : val;
  }
  if (Object.keys(custom).length) p.custom_filters = JSON.stringify(custom);
  return p;
}

function syncQueryToRoute() {
  const q: Record<string, string> = {};
  if (filters.value.module_id) {
    q.moduleId = filters.value.module_id;
    if (filters.value.include_submodules) q.includeSubmodules = '1';
  }
  const f = filters.value;
  const qRequirement = encodeFilterValues(f.requirement_ids);
  if (qRequirement) q.requirement_id = qRequirement;
  const qPriority = encodeFilterValues(f.priorities);
  if (qPriority) q.priority = qPriority;
  if (f.q?.trim()) q.q = f.q.trim();
  for (const [fieldId, val] of Object.entries(f.custom)) {
    const encoded = encodeFilterValues(val);
    if (encoded) q[`cf_${fieldId}`] = encoded;
  }
  if (activeCaseId.value) q.caseId = activeCaseId.value;
  if (page.value > 1) q.page = String(page.value);
  if (pageSize.value !== 20) q.page_size = String(pageSize.value);
  router.replace({ name: 'cases', query: q });
}

function applyRouteQuery() {
  applyingRoute.value = true;
  const q = route.query;
  const custom: Record<string, string[]> = {};
  for (const f of fieldSchema.templateFields.value) {
    const key = `cf_${f.id}`;
    custom[f.id] = decodeFilterQuery(q[key]);
  }
  const rawModule = q.moduleId;
  filters.value = syncCustomFilterKeys(
    {
      module_id: typeof rawModule === 'string' && rawModule ? rawModule : null,
      include_submodules: q.includeSubmodules === '1',
      q: typeof q.q === 'string' ? q.q : '',
      priorities: decodeFilterQuery(q.priority),
      requirement_ids: decodeFilterQuery(q.requirement_id),
      custom,
    },
    fieldSchema.templateFields.value
  );
  const pageQ = typeof q.page === 'string' ? parseInt(q.page, 10) : NaN;
  page.value = Number.isFinite(pageQ) && pageQ > 0 ? pageQ : 1;
  const pageSizeQ = typeof q.page_size === 'string' ? parseInt(q.page_size, 10) : NaN;
  pageSize.value = Number.isFinite(pageSizeQ) && pageSizeQ > 0 ? pageSizeQ : 20;

  const caseId = typeof q.caseId === 'string' && q.caseId ? q.caseId : null;
  if (caseId) {
    activeCaseId.value = caseId;
    detailDrawerVisible.value = true;
  }
  applyingRoute.value = false;
}

function applyFilters() {
  const hadPage = page.value;
  checkedRowKeys.value = [];
  page.value = 1;
  syncQueryToRoute();
  if (hadPage === 1) loadCases();
}

function resetFilters() {
  filters.value = emptyCaseListFilters(fieldSchema.templateFields.value);
  applyFilters();
}

function onVisibleKeysChange(keys: string[]) {
  setVisibleKeys(keys);
}

function closeDetailDrawer() {
  detailDrawerVisible.value = false;
  activeCaseId.value = null;
  const q = { ...route.query };
  delete q.caseId;
  router.replace({ name: 'cases', query: q });
}

function onDetailDrawerShowChange(show: boolean) {
  if (!show) closeDetailDrawer();
}

function goPrev() {
  const idx = activeIndex.value;
  if (idx > 0) openCaseDetail(cases.value[idx - 1].id);
}

function goNext() {
  const idx = activeIndex.value;
  if (idx >= 0 && idx < cases.value.length - 1) openCaseDetail(cases.value[idx + 1].id);
}

async function onCaseDeleted() {
  await loadCases();
}

async function onCaseUpdated() {
  await loadCases();
}

async function onCasesImported() {
  await loadModules();
  await loadCases();
}

async function loadMeta() {
  if (!ctx.projectId) {
    requirements.value = [];
    return;
  }
  const selectedReqIds = filters.value.requirement_ids.filter(
    (id) => id && id !== FILTER_EMPTY_VALUE
  );
  const [, reqRes] = await Promise.all([
    fieldSchema.reload(),
    listRequirementOptions({
      limit: 100,
      ids: selectedReqIds.length ? selectedReqIds.join(',') : undefined,
    }),
  ]);
  requirements.value = reqRes.data;
  filters.value = syncCustomFilterKeys(filters.value, fieldSchema.templateFields.value);
  sanitizeVisibleKeys();
}

async function loadCases() {
  if (!ctx.projectId) {
    cases.value = [];
    total.value = 0;
    return;
  }
  const prevIndex = activeCaseId.value
    ? cases.value.findIndex((c) => c.id === activeCaseId.value)
    : -1;
  loading.value = true;
  try {
    let { data } = await listCases(buildListParams());
    total.value = data.total;
    const maxPage = Math.max(1, Math.ceil(data.total / data.page_size) || 1);
    if (page.value > maxPage) {
      page.value = maxPage;
      ({ data } = await listCases(buildListParams()));
      total.value = data.total;
    }
    cases.value = data.items;
    if (data.page_size !== pageSize.value) pageSize.value = data.page_size;
    if (
      activeCaseId.value &&
      !data.items.some((c) => c.id === activeCaseId.value) &&
      prevIndex >= 0
    ) {
      const nextId = pickAdjacentItemId(data.items, prevIndex);
      if (nextId) openCaseDetail(nextId);
      else closeDetailDrawer();
    }
  } finally {
    loading.value = false;
  }
}

function openCreateDrawer() {
  caseForm.value = {
    title: '',
    module_id: filters.value.module_id ?? '',
    priority: 'P2',
    precondition: '',
    step_text: '',
    expected_result: '',
    requirement_ids: [],
    custom_fields: emptyCustomFields(fieldSchema.templateFieldsForUi.value),
  };
  createDrawerVisible.value = true;
}

async function saveNewCase() {
  if (!caseForm.value.title.trim()) {
    message.warning('请填写用例标题');
    return;
  }
  if (!caseForm.value.module_id) {
    message.warning('请选择模块');
    return;
  }
  const err = validateCustomFields(fieldSchema.templateFieldsForUi.value, caseForm.value.custom_fields);
  if (err) {
    message.warning(err);
    return;
  }
  await createCase({
    title: caseForm.value.title.trim(),
    module_id: caseForm.value.module_id,
    priority: caseForm.value.priority,
    precondition: caseForm.value.precondition || null,
    step_text: caseForm.value.step_text || null,
    expected_result: caseForm.value.expected_result || null,
    requirement_ids: caseForm.value.requirement_ids,
    custom_fields: caseForm.value.custom_fields,
  });
  message.success('已创建');
  createDrawerVisible.value = false;
  await loadCases();
}

onMounted(async () => {
  await loadMeta();
  applyRouteQuery();
  await loadModules();
  paginationReady.value = true;
  await loadCases();
});

watch(
  () => [
    route.query.moduleId,
    route.query.includeSubmodules,
    route.query.requirement_id,
    route.query.priority,
    route.query.q,
    route.query.caseId,
    route.query.page,
    route.query.page_size,
    ...fieldSchema.templateFields.value.map((f) => route.query[`cf_${f.id}`]),
  ],
  async () => {
    applyRouteQuery();
    await loadCases();
  }
);

watch(() => ctx.projectId, async () => {
  filters.value = emptyCaseListFilters(fieldSchema.templateFields.value);
  page.value = 1;
  checkedRowKeys.value = [];
  closeDetailDrawer();
  await loadMeta();
  await loadModules();
  await loadCases();
});

watch(pageSize, () => {
  if (!paginationReady.value || applyingRoute.value) return;
  if (page.value !== 1) {
    page.value = 1;
    return;
  }
  syncQueryToRoute();
  loadCases();
});

watch(page, () => {
  if (!paginationReady.value || applyingRoute.value) return;
  checkedRowKeys.value = [];
  syncQueryToRoute();
  loadCases();
});
</script>

<style scoped>
.case-list-table :deep(.n-data-table-td) {
  overflow: hidden;
}

.case-list-table :deep(.cell-ellipsis),
.case-list-table :deep(.case-title-link) {
  display: block;
  width: 100%;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.case-title-link {
  color: var(--n-primary-color);
  cursor: pointer;
}

.case-title-link:hover {
  text-decoration: underline;
}

.case-list-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}

.case-list-table :deep(.case-row-actions) {
  flex-wrap: nowrap;
  white-space: nowrap;
}
</style>
