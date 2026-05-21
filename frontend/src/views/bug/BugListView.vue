<template>
  <n-card title="缺陷管理">
    <template #header-extra>
      <n-space>
        <n-button v-if="canCreate" @click="showImportModal = true">导入</n-button>
        <n-button v-if="canCreate" type="primary" @click="openCreate">新建缺陷</n-button>
      </n-space>
    </template>

    <BugImportModal v-model:show="showImportModal" @imported="loadBugs" />

    <SchemaFieldFilters
      :model="filters"
      :catalog="filterCatalog"
      :project-id="ctx.projectId"
      :visible-keys="visibleKeys"
      :status-options="statusOptions"
      :member-options="memberOptions"
      :requirement-options="requirementOptions"
      :plan-options="planOptions"
      @apply="applyFilters"
      @reset="resetFilters"
      @update:visible-keys="onVisibleKeysChange"
    />

    <n-data-table
      :columns="columns"
      :data="bugs"
      :loading="loading"
      :row-key="(row: BugItem) => row.id"
      :row-props="rowProps"
      style="margin-top: 12px"
    />

    <div class="bug-list-pagination">
      <n-pagination
        v-model:page="page"
        v-model:page-size="pageSize"
        :item-count="total"
        :page-sizes="[10, 20, 50, 100]"
        show-size-picker
        show-quick-jumper
      />
    </div>

    <n-drawer
      v-model:show="drawerVisible"
      :width="'50%'"
      placement="right"
      :trap-focus="false"
      @update:show="onDrawerShowChange"
    >
      <n-drawer-content :closable="false" body-content-style="padding: 0">
        <BugDetailPanel
          v-if="activeBugId"
          :bug-id="activeBugId"
          :has-prev="activeIndex > 0"
          :has-next="activeIndex >= 0 && activeIndex < bugs.length - 1"
          @prev="goPrev"
          @next="goNext"
          @close="closeDrawer"
          @deleted="onBugDeleted"
          @updated="onBugUpdated"
        />
      </n-drawer-content>
    </n-drawer>

    <n-modal
      v-model:show="showModal"
      preset="dialog"
      title="新建缺陷"
      positive-text="创建"
      style="width: 560px"
      @positive-click="onCreate"
    >
      <n-form label-placement="top">
        <n-form-item label="缺陷标题" required>
          <n-input v-model:value="form.title" placeholder="请输入缺陷标题" />
        </n-form-item>
        <n-form-item label="状态">
          <n-select v-model:value="form.status_key" :options="statusOptions" style="width: 100%" />
        </n-form-item>
        <n-form-item label="提出人">
          <n-select
            v-model:value="form.reporter_id"
            :options="memberOptions"
            filterable
            style="width: 100%"
          />
        </n-form-item>
        <n-form-item label="跟进人">
          <n-select
            v-model:value="form.follower_ids"
            :options="memberOptions"
            multiple
            filterable
            clearable
            style="width: 100%"
          />
        </n-form-item>
        <n-form-item label="描述">
          <PasteImageTextarea v-model="form.description" :project-id="ctx.projectId" />
        </n-form-item>
        <n-form-item label="关联需求">
          <n-select
            v-model:value="form.requirement_ids"
            :options="requirementOptions"
            multiple
            filterable
            clearable
            style="width: 100%"
          />
        </n-form-item>
        <n-form-item label="关联测试计划">
          <n-select
            v-model:value="form.plan_ids"
            :options="planOptions"
            multiple
            filterable
            clearable
            style="width: 100%"
          />
        </n-form-item>
        <n-form-item label="规划迭代">
          <VersionSelect v-model="form.plan_version_id" :project-id="ctx.projectId" />
        </n-form-item>
        <n-form-item label="发现版本">
          <VersionSelect v-model="form.found_version_id" :project-id="ctx.projectId" />
        </n-form-item>
        <DynamicFieldForm
          v-if="templateUiFields.length"
          v-model="createCustomFields"
          :fields="templateUiFields"
          :project-id="ctx.projectId"
        />
      </n-form>
    </n-modal>
  </n-card>
</template>

<script setup lang="ts">
import { computed, h, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  NButton,
  NCard,
  NSpace,
  NDataTable,
  NDrawer,
  NDrawerContent,
  NForm,
  NFormItem,
  NInput,
  NModal,
  NSelect,
  NPagination,
  useMessage,
  type DataTableColumns,
} from 'naive-ui';
import { createBug, listBugs, type ListBugsParams } from '@/api/bugs';
import { listPlans } from '@/api/plans';
import { listRequirements } from '@/api/requirements';
import { listBugStatuses } from '@/api/templates';
import BugDetailPanel from '@/components/BugDetailPanel.vue';
import BugImportModal from '@/components/BugImportModal.vue';
import SchemaFieldFilters from '@/components/SchemaFieldFilters.vue';
import DynamicFieldForm from '@/components/DynamicFieldForm.vue';
import PasteImageTextarea from '@/components/PasteImageTextarea.vue';
import VersionSelect from '@/components/VersionSelect.vue';
import {
  emptyBugListFilters,
  syncCustomFilterKeys,
  type BugListFilterState,
} from '@/composables/useBugListFilters';
import { useBugListFilterVisibility } from '@/composables/useBugListFilterVisibility';
import { useProjectFieldSchema } from '@/composables/useProjectFieldSchema';
import { emptyCustomFields, validateCustomFields } from '@/constants/fieldTypes';
import { useProjectMemberOptions } from '@/composables/useProjectMemberOptions';
import { usePermissions } from '@/composables/usePermissions';
import { useContextStore } from '@/stores/context';
import { useAuthStore } from '@/stores/auth';
import type { BugItem, BugStatusDef, Requirement, TestPlan } from '@/types/business';
import { NUM_TABLE_COLUMN } from '@/utils/entityNum';

const route = useRoute();
const router = useRouter();
const ctx = useContextStore();
const auth = useAuthStore();
const message = useMessage();
const { canManageBugs } = usePermissions();
const canCreate = computed(() => canManageBugs(ctx.projectId));
const { options: memberOptions } = useProjectMemberOptions(computed(() => ctx.projectId));

const bugs = ref<BugItem[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);
const statuses = ref<BugStatusDef[]>([]);
const requirements = ref<Requirement[]>([]);
const plans = ref<TestPlan[]>([]);
const loading = ref(false);
const showModal = ref(false);
const showImportModal = ref(false);
const drawerVisible = ref(false);
const activeBugId = ref<string | null>(null);
const applyingRoute = ref(false);
const paginationReady = ref(false);

const filters = ref<BugListFilterState>(emptyBugListFilters());
const projectIdRef = computed(() => ctx.projectId);
const fieldSchema = useProjectFieldSchema('bug', projectIdRef);
const templateUiFields = computed(() => fieldSchema.templateFieldsForUi.value);

const { visibleKeys, setVisibleKeys, sanitizeVisibleKeys, catalog: filterCatalog } =
  useBugListFilterVisibility(projectIdRef, fieldSchema.templateFields, filters);

function memberLabel(userId: string) {
  return memberOptions.value.find((o) => o.value === userId)?.label ?? userId;
}

function onVisibleKeysChange(keys: string[]) {
  setVisibleKeys(keys);
}

function expandVisibleFromActiveFilters() {
  const f = filters.value;
  const extra: string[] = [];
  if (f.status_key) extra.push('status');
  if (f.reporter_id) extra.push('reporter');
  if (f.follower_id) extra.push('follower');
  if (f.plan_version_id) extra.push('plan_version');
  if (f.found_version_id) extra.push('found_version');
  if (f.requirement_id) extra.push('requirement');
  if (f.plan_id) extra.push('plan');
  if (f.q?.trim()) extra.push('q');
  for (const [fieldId, val] of Object.entries(f.custom)) {
    if (val) extra.push(`cf:${fieldId}`);
  }
  if (!extra.length) return;
  setVisibleKeys([...new Set([...visibleKeys.value, ...extra])]);
}

const form = ref({
  title: '',
  status_key: null as string | null,
  description: '',
  reporter_id: null as string | null,
  follower_ids: [] as string[],
  requirement_ids: [] as string[],
  plan_ids: [] as string[],
  plan_version_id: null as string | null,
  found_version_id: null as string | null,
});

const createCustomFields = ref<Record<string, unknown>>({});

const statusLabelMap = computed(() => {
  const m = new Map<string, string>();
  for (const s of statuses.value) m.set(s.key, s.label);
  return m;
});

const statusOptions = computed(() =>
  statuses.value.map((s) => ({ label: s.label, value: s.key }))
);

const requirementOptions = computed(() =>
  requirements.value.map((r) => ({ label: r.title, value: r.id }))
);

const planOptions = computed(() => plans.value.map((p) => ({ label: p.name, value: p.id })));

const activeIndex = computed(() =>
  activeBugId.value ? bugs.value.findIndex((b) => b.id === activeBugId.value) : -1
);

function formatDate(iso: string) {
  try {
    return new Date(iso).toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return iso;
  }
}

function followersSummary(row: BugItem): string {
  const names = row.followers?.map((f) => f.name).filter(Boolean);
  if (names?.length) return names.join('、');
  if (row.follower_ids?.length) return `${row.follower_ids.length} 人`;
  return '—';
}

const columns = computed<DataTableColumns<BugItem>>(() => {
  const customCols = fieldSchema.buildListColumns<BugItem>({ memberLabel });

  return [
  { ...NUM_TABLE_COLUMN, width: 56 },
  {
    title: '标题',
    key: 'title',
    minWidth: 180,
    ellipsis: { tooltip: true },
    render: (row) =>
      h(
        NButton,
        { text: true, type: 'primary', onClick: (e: Event) => { e.stopPropagation(); openBug(row.id); } },
        () => row.title
      ),
  },
  {
    title: '状态',
    key: 'status_key',
    width: 96,
    render: (row) => statusLabelMap.value.get(row.status_key) ?? row.status_key,
  },
  ...customCols,
  {
    title: '提出人',
    key: 'reporter',
    width: 100,
    ellipsis: { tooltip: true },
    render: (row) => row.reporter?.name ?? '—',
  },
  {
    title: '跟进人',
    key: 'followers',
    width: 120,
    ellipsis: { tooltip: true },
    render: (row) => followersSummary(row),
  },
  {
    title: '规划迭代',
    key: 'plan_version',
    width: 100,
    ellipsis: { tooltip: true },
    render: (row) => row.plan_version?.name ?? '—',
  },
  {
    title: '发现版本',
    key: 'found_version',
    width: 100,
    ellipsis: { tooltip: true },
    render: (row) => row.found_version?.name ?? '—',
  },
  {
    title: '更新时间',
    key: 'updated_at',
    width: 120,
    render: (row) => formatDate(row.updated_at),
  },
];
});

function rowProps(row: BugItem) {
  return {
    style: 'cursor: pointer',
    onClick: () => openBug(row.id),
  };
}

function buildListParams(): ListBugsParams {
  const p: ListBugsParams = {
    page: page.value,
    page_size: pageSize.value,
  };
  const f = filters.value;
  if (f.status_key) p.status_key = f.status_key;
  if (f.reporter_id) p.reporter_id = f.reporter_id;
  if (f.follower_id) p.follower_id = f.follower_id;
  if (f.plan_version_id) p.plan_version_id = f.plan_version_id;
  if (f.found_version_id) p.found_version_id = f.found_version_id;
  if (f.requirement_id) p.requirement_id = f.requirement_id;
  if (f.plan_id) p.plan_id = f.plan_id;
  if (f.q?.trim()) p.q = f.q.trim();
  const custom: Record<string, string> = {};
  for (const [fieldId, val] of Object.entries(f.custom)) {
    if (val) custom[fieldId] = val;
  }
  if (Object.keys(custom).length) p.custom_filters = JSON.stringify(custom);
  return p;
}

function syncQueryToRoute() {
  const q: Record<string, string> = {};
  const f = filters.value;
  if (f.status_key) q.status_key = f.status_key;
  if (f.reporter_id) q.reporter_id = f.reporter_id;
  if (f.follower_id) q.follower_id = f.follower_id;
  if (f.plan_version_id) q.plan_version_id = f.plan_version_id;
  if (f.found_version_id) q.found_version_id = f.found_version_id;
  if (f.requirement_id) q.requirement_id = f.requirement_id;
  if (f.plan_id) q.plan_id = f.plan_id;
  if (f.q?.trim()) q.q = f.q.trim();
  for (const [fieldId, val] of Object.entries(f.custom)) {
    if (val) q[`cf_${fieldId}`] = val;
  }
  if (activeBugId.value) q.bugId = activeBugId.value;
  if (page.value > 1) q.page = String(page.value);
  if (pageSize.value !== 20) q.page_size = String(pageSize.value);
  router.replace({ name: 'bugs', query: q });
}

function applyRouteQuery() {
  applyingRoute.value = true;
  const q = route.query;
  const custom: Record<string, string | null> = {};
  for (const f of fieldSchema.templateFields.value) {
    const key = `cf_${f.id}`;
    custom[f.id] = typeof q[key] === 'string' ? q[key] : null;
  }
  filters.value = syncCustomFilterKeys(
    {
      status_key: typeof q.status_key === 'string' ? q.status_key : null,
      reporter_id: typeof q.reporter_id === 'string' ? q.reporter_id : null,
      follower_id: typeof q.follower_id === 'string' ? q.follower_id : null,
      plan_version_id: typeof q.plan_version_id === 'string' ? q.plan_version_id : null,
      found_version_id: typeof q.found_version_id === 'string' ? q.found_version_id : null,
      requirement_id: typeof q.requirement_id === 'string' ? q.requirement_id : null,
      plan_id: typeof q.plan_id === 'string' ? q.plan_id : null,
      q: typeof q.q === 'string' ? q.q : '',
      custom,
    },
    fieldSchema.templateFields.value
  );
  const pageQ = typeof q.page === 'string' ? parseInt(q.page, 10) : NaN;
  page.value = Number.isFinite(pageQ) && pageQ > 0 ? pageQ : 1;
  const pageSizeQ = typeof q.page_size === 'string' ? parseInt(q.page_size, 10) : NaN;
  pageSize.value = Number.isFinite(pageSizeQ) && pageSizeQ > 0 ? pageSizeQ : 20;

  const bugId = typeof q.bugId === 'string' && q.bugId ? q.bugId : null;
  if (bugId) {
    activeBugId.value = bugId;
    drawerVisible.value = true;
  }
  applyingRoute.value = false;
}

function openBug(id: string) {
  activeBugId.value = id;
  drawerVisible.value = true;
  syncQueryToRoute();
}

function closeDrawer() {
  drawerVisible.value = false;
  activeBugId.value = null;
  const q = { ...route.query };
  delete q.bugId;
  router.replace({ name: 'bugs', query: q });
}

function onDrawerShowChange(show: boolean) {
  if (!show) closeDrawer();
}

function goPrev() {
  const idx = activeIndex.value;
  if (idx > 0) openBug(bugs.value[idx - 1].id);
}

function goNext() {
  const idx = activeIndex.value;
  if (idx >= 0 && idx < bugs.value.length - 1) openBug(bugs.value[idx + 1].id);
}

async function onBugDeleted() {
  closeDrawer();
  await load();
}

async function onBugUpdated() {
  await load();
}

function applyFilters() {
  const hadPage = page.value;
  page.value = 1;
  syncQueryToRoute();
  if (hadPage === 1) load();
}

function resetFilters() {
  filters.value = emptyBugListFilters(fieldSchema.templateFields.value);
  applyFilters();
}

async function loadMeta() {
  if (!ctx.projectId) {
    statuses.value = [];
    requirements.value = [];
    plans.value = [];
    return;
  }
  const [st, , req, pl] = await Promise.all([
    listBugStatuses(ctx.projectId),
    fieldSchema.reload(true),
    listRequirements(),
    listPlans(),
  ]);
  statuses.value = st.data;
  filters.value = syncCustomFilterKeys(filters.value, fieldSchema.templateFields.value);
  sanitizeVisibleKeys();
  requirements.value = req.data;
  plans.value = pl.data;
}

async function load() {
  if (!ctx.projectId) {
    bugs.value = [];
    return;
  }
  loading.value = true;
  try {
    const { data } = await listBugs(buildListParams());
    total.value = data.total;
    const maxPage = Math.max(1, Math.ceil(data.total / data.page_size) || 1);
    if (page.value > maxPage) {
      page.value = maxPage;
      return;
    }
    bugs.value = data.items;
    if (data.page_size !== pageSize.value) pageSize.value = data.page_size;
    if (activeBugId.value && !data.items.some((b) => b.id === activeBugId.value)) {
      closeDrawer();
    }
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  form.value = {
    title: '',
    status_key: statuses.value[0]?.key ?? null,
    reporter_id: auth.user?.id ?? null,
    follower_ids: [],
    description: '',
    requirement_ids: [],
    plan_ids: [],
    plan_version_id: null,
    found_version_id: null,
  };
  createCustomFields.value = emptyCustomFields(fieldSchema.templateFieldsForUi.value);
  showModal.value = true;
}

async function onCreate() {
  if (!form.value.title.trim()) {
    message.warning('请填写标题');
    return false;
  }
  const customErr = validateCustomFields(fieldSchema.templateFieldsForUi.value, createCustomFields.value);
  if (customErr) {
    message.warning(customErr);
    return false;
  }
  const { data } = await createBug({
    title: form.value.title.trim(),
    status_key: form.value.status_key ?? undefined,
    reporter_id: form.value.reporter_id ?? undefined,
    follower_ids: form.value.follower_ids,
    description: form.value.description || undefined,
    requirement_ids: form.value.requirement_ids,
    plan_ids: form.value.plan_ids,
    plan_version_id: form.value.plan_version_id ?? undefined,
    found_version_id: form.value.found_version_id ?? undefined,
    custom_fields: createCustomFields.value,
  });
  message.success('已创建');
  showModal.value = false;
  await load();
  openBug(data.id);
  return true;
}

onMounted(async () => {
  await loadMeta();
  applyRouteQuery();
  expandVisibleFromActiveFilters();
  paginationReady.value = true;
  await load();
});

watch(
  () => route.query.bugId,
  (id) => {
    if (typeof id === 'string' && id) {
      activeBugId.value = id;
      drawerVisible.value = true;
    } else if (!id && drawerVisible.value) {
      drawerVisible.value = false;
      activeBugId.value = null;
    }
  }
);

watch(
  () => [
    route.query.follower_id,
    route.query.reporter_id,
    route.query.status_key,
    route.query.assignee_id,
    route.query.plan_id,
    route.query.requirement_id,
  ],
  async () => {
    applyRouteQuery();
    expandVisibleFromActiveFilters();
    await load();
  }
);

watch(() => ctx.projectId, async () => {
  filters.value = emptyBugListFilters();
  page.value = 1;
  closeDrawer();
  await loadMeta();
  await load();
});

watch(pageSize, () => {
  if (!paginationReady.value || applyingRoute.value) return;
  if (page.value !== 1) {
    page.value = 1;
    return;
  }
  syncQueryToRoute();
  load();
});

watch(page, () => {
  if (!paginationReady.value || applyingRoute.value) return;
  syncQueryToRoute();
  load();
});
</script>

<style scoped>
.bug-list-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}
</style>

