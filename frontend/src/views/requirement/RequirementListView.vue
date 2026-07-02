<template>
  <n-card title="需求管理">
    <template #header-extra>
      <n-button
        v-if="canCatalog"
        type="primary"
        :disabled="!ctx.projectId"
        @click="openCreateDrawer()"
      >
        新建需求
      </n-button>
    </template>

    <RequirementListFilters
      :model="filters"
      :project-id="ctx.projectId"
      @apply="applyFilters"
      @reset="resetFilters"
    />

    <n-space v-if="filterTags.length" align="center" style="margin-top: 8px; margin-bottom: 8px">
      <n-text depth="3">筛选：</n-text>
      <n-tag v-for="t in filterTags" :key="t.key" closable @close="t.clear">{{ t.label }}</n-tag>
    </n-space>
    <n-data-table
      :columns="columns"
      :data="rows"
      :loading="loading"
      :row-props="rowProps"
      class="requirement-list-table"
      :class="{ 'requirement-list-table--blocked': listInteractionBlocked }"
      style="margin-top: 8px"
    />

    <div class="requirement-list-pagination">
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
      v-model:show="createDrawerVisible"
      :width="REQUIREMENT_DRAWER_WIDTH"
      placement="right"
      :trap-focus="false"
    >
      <n-drawer-content title="新建需求" closable body-content-style="padding: 8px 12px 16px">
        <RequirementCreateForm
          v-if="ctx.projectId && createDrawerVisible"
          ref="createFormRef"
          :project-id="ctx.projectId"
        />
        <template #footer>
          <n-space justify="end">
            <n-button @click="createDrawerVisible = false">取消</n-button>
            <n-button type="primary" :loading="creating" @click="onCreate">创建</n-button>
          </n-space>
        </template>
      </n-drawer-content>
    </n-drawer>

    <n-drawer
      v-model:show="drawerVisible"
      :width="REQUIREMENT_DRAWER_WIDTH"
      placement="right"
      :trap-focus="false"
      @update:show="onDrawerShowChange"
    >
      <n-drawer-content :closable="false" body-content-style="padding: 0">
        <RequirementDetailPanel
          v-if="activeReqId"
          :requirement-id="activeReqId"
          :has-prev="activeIndex > 0"
          :has-next="activeIndex >= 0 && activeIndex < rows.length - 1"
          @prev="goPrev"
          @next="goNext"
          @close="closeDrawer"
          @deleted="onDetailDeleted"
          @updated="onDetailUpdated"
        />
      </n-drawer-content>
    </n-drawer>
  </n-card>
</template>

<script setup lang="ts">
import { computed, h, nextTick, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  NButton,
  NCard,
  NDataTable,
  NDrawer,
  NDrawerContent,
  NPagination,
  NSpace,
  NTag,
  NText,
  NTooltip,
  useDialog,
  useMessage,
  type DataTableColumns,
} from 'naive-ui';
import {
  createRequirement,
  deleteRequirement,
  listRequirements,
} from '@/api/requirements';
import RequirementCreateForm from '@/components/RequirementCreateForm.vue';
import RequirementListFilters from '@/components/RequirementListFilters.vue';
import type { ComponentPublicInstance } from 'vue';
import RequirementDetailPanel from '@/components/RequirementDetailPanel.vue';
import { listVersions } from '@/api/versions';
import {
  clearRequirementFilterField,
  emptyRequirementListFilters,
  type RequirementListFilterState,
} from '@/composables/useRequirementListFilters';
import { requirementPriorityTagType } from '@/constants/requirementPriority';
import { requirementStatusLabel, requirementStatusTagType } from '@/constants/requirementStatus';
import { useProjectMemberOptions } from '@/composables/useProjectMemberOptions';
import { useRequirementProjectConfig } from '@/composables/useRequirementProjectConfig';
import { usePermissions } from '@/composables/usePermissions';
import { useContextStore } from '@/stores/context';
import type { Requirement, ProjectVersion } from '@/types/business';
import { decodeFilterQuery, encodeFilterValues, hasFilterValues } from '@/utils/filterQueryCodec';
import { pickAdjacentItemId } from '@/utils/listNavigation';
import { NUM_TABLE_COLUMN } from '@/utils/entityNum';
import { formatDevHandoffDate, formatEstimatedCompletion, formatRequirementDevelopers } from '@/utils/requirementListDerived';

const ctx = useContextStore();
const { canManageCatalog } = usePermissions();
const canCatalog = computed(() => canManageCatalog(ctx.projectId));
const projectConfig = useRequirementProjectConfig(() => ctx.projectId);
const { labelByUserId: memberLabelByUserId } = useProjectMemberOptions(computed(() => ctx.projectId));

/** 需求新建 / 查看 / 编辑 共用抽屉宽度 */
const REQUIREMENT_DRAWER_WIDTH = 'min(1080px, 90vw)';

const route = useRoute();
const router = useRouter();
const message = useMessage();
const dialog = useDialog();
const rows = ref<Requirement[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);
const loading = ref(false);
const createDrawerVisible = ref(false);
const creating = ref(false);
const drawerVisible = ref(false);
/** 详情/新建抽屉打开时禁用列表点击，避免与抽屉内「保存」等同位置的操作列误触 */
const listInteractionBlocked = computed(
  () => drawerVisible.value || createDrawerVisible.value
);
const activeReqId = ref<string | null>(null);
const applyingRoute = ref(false);
const paginationReady = ref(false);
const filters = ref<RequirementListFilterState>(emptyRequirementListFilters());
const versions = ref<ProjectVersion[]>([]);

const createFormRef = ref<ComponentPublicInstance<{
  reset: () => void;
  validate: () => string | null;
  getPayload: () => import('@/components/RequirementCreateForm.vue').RequirementCreatePayload;
  prepare: () => Promise<void>;
}> | null>(null);

const activeIndex = computed(() =>
  activeReqId.value ? rows.value.findIndex((r) => r.id === activeReqId.value) : -1
);

const versionNameById = computed(() => new Map(versions.value.map((v) => [v.id, v.name])));

const filterTags = computed(() => {
  const tags: { key: string; label: string; clear: () => void }[] = [];
  const f = filters.value;

  if (f.q.trim()) {
    tags.push({
      key: 'q',
      label: `标题：${f.q.trim()}`,
      clear: () => clearFilterField('q'),
    });
  }
  if (hasFilterValues(f.status_keys)) {
    const labels = f.status_keys.map((k) => requirementStatusLabel(k)).join('、');
    tags.push({
      key: 'status_keys',
      label: `状态：${labels}`,
      clear: () => clearFilterField('status_keys'),
    });
  }
  if (hasFilterValues(f.priorities)) {
    const labels = f.priorities.map((k) => projectConfig.priorityLabel(k)).join('、');
    tags.push({
      key: 'priorities',
      label: `优先级：${labels}`,
      clear: () => clearFilterField('priorities'),
    });
  }
  if (hasFilterValues(f.req_types)) {
    const labels = f.req_types.map((k) => projectConfig.typeLabel(k)).join('、');
    tags.push({
      key: 'req_types',
      label: `类型：${labels}`,
      clear: () => clearFilterField('req_types'),
    });
  }
  if (f.version_id) {
    const name = versionNameById.value.get(f.version_id) ?? '已选版本';
    tags.push({
      key: 'version_id',
      label: `版本：${name}`,
      clear: () => clearFilterField('version_id'),
    });
  }
  if (hasFilterValues(f.developer_ids)) {
    const labels = f.developer_ids.map((id) => memberLabelByUserId.value.get(id) ?? id).join('、');
    tags.push({
      key: 'developer_ids',
      label: `开发人员：${labels}`,
      clear: () => clearFilterField('developer_ids'),
    });
  }
  if (f.dev_handoff_from || f.dev_handoff_to) {
    const from = f.dev_handoff_from ?? '…';
    const to = f.dev_handoff_to ?? '…';
    tags.push({
      key: 'dev_handoff',
      label: `转测时间：${from} ~ ${to}`,
      clear: () => {
        filters.value = {
          ...filters.value,
          dev_handoff_from: null,
          dev_handoff_to: null,
        };
        page.value = 1;
        syncQueryToRoute();
        void load();
      },
    });
  }
  return tags;
});

function clearFilterField(key: keyof RequirementListFilterState) {
  filters.value = clearRequirementFilterField(filters.value, key);
  page.value = 1;
  syncQueryToRoute();
  void load();
}

function buildListParams() {
  const f = filters.value;
  const params: {
    q?: string;
    version_id?: string;
    status?: string;
    priority?: string;
    req_type?: string;
    developer_id?: string;
    dev_handoff_from?: string;
    dev_handoff_to?: string;
    page?: number;
    page_size?: number;
  } = {
    page: page.value,
    page_size: pageSize.value,
  };
  if (f.q.trim()) params.q = f.q.trim();
  if (f.version_id) params.version_id = f.version_id;
  const status = encodeFilterValues(f.status_keys);
  if (status) params.status = status;
  const priority = encodeFilterValues(f.priorities);
  if (priority) params.priority = priority;
  const reqType = encodeFilterValues(f.req_types);
  if (reqType) params.req_type = reqType;
  const developerId = encodeFilterValues(f.developer_ids);
  if (developerId) params.developer_id = developerId;
  if (f.dev_handoff_from) params.dev_handoff_from = f.dev_handoff_from;
  if (f.dev_handoff_to) params.dev_handoff_to = f.dev_handoff_to;
  return params;
}

function syncQueryToRoute() {
  const q: Record<string, string> = {};
  const f = filters.value;
  if (f.q.trim()) q.q = f.q.trim();
  if (f.version_id) q.version_id = f.version_id;
  const status = encodeFilterValues(f.status_keys);
  if (status) q.status = status;
  const priority = encodeFilterValues(f.priorities);
  if (priority) q.priority = priority;
  const reqType = encodeFilterValues(f.req_types);
  if (reqType) q.req_type = reqType;
  const developerId = encodeFilterValues(f.developer_ids);
  if (developerId) q.developer_id = developerId;
  if (f.dev_handoff_from) q.dev_handoff_from = f.dev_handoff_from;
  if (f.dev_handoff_to) q.dev_handoff_to = f.dev_handoff_to;
  if (activeReqId.value) q.id = activeReqId.value;
  if (page.value > 1) q.page = String(page.value);
  if (pageSize.value !== 20) q.page_size = String(pageSize.value);
  router.replace({ name: 'requirements', query: q });
}

function applyRouteQuery() {
  applyingRoute.value = true;
  const q = route.query;
  filters.value = {
    q: typeof q.q === 'string' ? q.q : '',
    status_keys: decodeFilterQuery(q.status),
    priorities: decodeFilterQuery(q.priority),
    req_types: decodeFilterQuery(q.req_type),
    version_id: typeof q.version_id === 'string' && q.version_id ? q.version_id : null,
    developer_ids: decodeFilterQuery(q.developer_id),
    dev_handoff_from: typeof q.dev_handoff_from === 'string' && q.dev_handoff_from ? q.dev_handoff_from : null,
    dev_handoff_to: typeof q.dev_handoff_to === 'string' && q.dev_handoff_to ? q.dev_handoff_to : null,
  };
  const pageQ = typeof q.page === 'string' ? parseInt(q.page, 10) : NaN;
  page.value = Number.isFinite(pageQ) && pageQ > 0 ? pageQ : 1;
  const pageSizeQ = typeof q.page_size === 'string' ? parseInt(q.page_size, 10) : NaN;
  pageSize.value = Number.isFinite(pageSizeQ) && pageSizeQ > 0 ? pageSizeQ : 20;
  const qid = typeof q.id === 'string' && q.id ? q.id : null;
  if (qid) {
    activeReqId.value = qid;
    drawerVisible.value = true;
  } else if (!drawerVisible.value) {
    activeReqId.value = null;
  }
  applyingRoute.value = false;
}

function applyFilters() {
  const hadPage = page.value;
  page.value = 1;
  applyingRoute.value = true;
  syncQueryToRoute();
  applyingRoute.value = false;
  if (hadPage === 1) void load();
}

function resetFilters() {
  filters.value = emptyRequirementListFilters();
  applyFilters();
}

const columns = computed<DataTableColumns<Requirement>>(() => [
  NUM_TABLE_COLUMN,
  {
    title: '标题',
    key: 'title',
    ellipsis: { tooltip: true },
    render: (row) =>
      h(
        NTooltip,
        { trigger: 'hover' },
        {
          trigger: () =>
            h(
              'a',
              {
                class: 'prd-link',
                style: { cursor: 'pointer' },
                onClick: (e: Event) => {
                  e.stopPropagation();
                  openDetail(row.id);
                },
              },
              row.title
            ),
          default: () => row.title,
        }
      ),
  },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render: (row) =>
      h(NTag, { size: 'small', type: requirementStatusTagType(row.status) }, () =>
        requirementStatusLabel(row.status)
      ),
  },
  {
    title: '优先级',
    key: 'priority',
    width: 80,
    render: (row) =>
      h(
        NTag,
        { size: 'small', round: true, bordered: false, type: requirementPriorityTagType(row.priority) },
        () => projectConfig.priorityLabel(row.priority)
      ),
  },
  {
    title: '类型',
    key: 'req_type',
    width: 100,
    render: (row) => projectConfig.typeLabel(row.req_type),
  },
  {
    title: '版本',
    key: 'version',
    width: 120,
    render: (row) => row.version?.name ?? '—',
  },
  {
    title: '开发人员',
    key: 'developers',
    width: 140,
    ellipsis: { tooltip: true },
    render: (row) => formatRequirementDevelopers(row),
  },
  {
    title: '转测时间',
    key: 'dev_handoff_date',
    width: 110,
    render: (row) => formatDevHandoffDate(row),
  },
  {
    title: '预计完成',
    key: 'estimated_completion',
    width: 110,
    render: (row) => formatEstimatedCompletion(row),
  },
  ...(canCatalog.value
    ? [
        {
          title: '操作',
          key: 'actions',
          width: 72,
          render: (row: Requirement) =>
            h(
              NButton,
              {
                size: 'small',
                quaternary: true,
                type: 'error',
                onClick: (e: Event) => {
                  e.stopPropagation();
                  onRemove(row);
                },
              },
              () => '删除'
            ),
        },
      ]
    : []),
]);

function rowProps(row: Requirement) {
  return {
    style: { cursor: 'pointer' },
    onClick: () => openDetail(row.id),
  };
}

function openDetail(id: string) {
  activeReqId.value = id;
  drawerVisible.value = true;
  applyingRoute.value = true;
  syncQueryToRoute();
  applyingRoute.value = false;
}

function closeDrawer() {
  drawerVisible.value = false;
  activeReqId.value = null;
  applyingRoute.value = true;
  syncQueryToRoute();
  applyingRoute.value = false;
}

function onDrawerShowChange(show: boolean) {
  if (!show) closeDrawer();
}

function goPrev() {
  if (activeIndex.value > 0) openDetail(rows.value[activeIndex.value - 1].id);
}

function goNext() {
  if (activeIndex.value >= 0 && activeIndex.value < rows.value.length - 1) {
    openDetail(rows.value[activeIndex.value + 1].id);
  }
}

function onDetailDeleted() {
  closeDrawer();
  void load();
}

function onDetailUpdated(row: Requirement) {
  const idx = rows.value.findIndex((r) => r.id === row.id);
  if (idx >= 0) rows.value[idx] = row;
}

async function load() {
  if (!ctx.projectId) {
    rows.value = [];
    total.value = 0;
    versions.value = [];
    return;
  }
  const prevIndex = activeReqId.value
    ? rows.value.findIndex((r) => r.id === activeReqId.value)
    : -1;
  loading.value = true;
  try {
    await projectConfig.reload();
    const [{ data }, versionRes] = await Promise.all([
      listRequirements(buildListParams()),
      listVersions(),
    ]);
    total.value = data.total;
    const maxPage = Math.max(1, Math.ceil(data.total / data.page_size) || 1);
    if (page.value > maxPage) {
      page.value = maxPage;
      return;
    }
    rows.value = data.items;
    if (data.page_size !== pageSize.value) pageSize.value = data.page_size;
    versions.value = versionRes.data;
    if (
      activeReqId.value &&
      !data.items.some((r) => r.id === activeReqId.value) &&
      prevIndex >= 0
    ) {
      const nextId = pickAdjacentItemId(data.items, prevIndex);
      if (nextId) openDetail(nextId);
      else closeDrawer();
    }
  } finally {
    loading.value = false;
  }
}

function openCreateDrawer() {
  createDrawerVisible.value = true;
  void nextTick(async () => {
    await createFormRef.value?.prepare();
    createFormRef.value?.reset();
  });
}

async function onCreate() {
  const form = createFormRef.value;
  if (!form) return;
  const err = form.validate();
  if (err) {
    message.warning(err);
    return;
  }
  creating.value = true;
  try {
    await createRequirement(form.getPayload());
    message.success('已创建');
    createDrawerVisible.value = false;
    await load();
  } catch (e: unknown) {
    const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
    message.error(typeof detail === 'string' ? detail : '创建失败');
  } finally {
    creating.value = false;
  }
}

function onRemove(row: Requirement) {
  dialog.warning({
    title: '删除需求',
    content: `确定删除「${row.title}」？`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      await deleteRequirement(row.id);
      message.success('已删除');
      await load();
    },
  });
}

onMounted(() => {
  applyRouteQuery();
  paginationReady.value = true;
  void load();
});

watch(
  () => ctx.projectId,
  () => {
    filters.value = emptyRequirementListFilters();
    page.value = 1;
    activeReqId.value = null;
    drawerVisible.value = false;
    router.replace({ name: 'requirements', query: {} });
    void load();
  }
);

watch(
  () => route.query,
  () => {
    if (applyingRoute.value) return;
    applyRouteQuery();
    void load();
  }
);

watch(pageSize, () => {
  if (!paginationReady.value || applyingRoute.value) return;
  if (page.value !== 1) {
    page.value = 1;
    return;
  }
  syncQueryToRoute();
  void load();
});

watch(page, () => {
  if (!paginationReady.value || applyingRoute.value) return;
  syncQueryToRoute();
  void load();
});
</script>

<style scoped>
.requirement-list-table--blocked {
  pointer-events: none;
  user-select: none;
}

.requirement-list-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}

:deep(.prd-link) {
  display: inline-block;
  max-width: 100%;
  color: var(--n-primary-color, #18a058);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: bottom;
}
</style>
