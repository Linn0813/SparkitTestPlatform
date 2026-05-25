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
    <n-space v-if="filterTags.length" align="center" style="margin-top: 8px; margin-bottom: 8px">
      <n-text depth="3">筛选：</n-text>
      <n-tag v-for="t in filterTags" :key="t.key" closable @close="t.clear">{{ t.label }}</n-tag>
    </n-space>
    <n-data-table
      :columns="columns"
      :data="rows"
      :loading="loading"
      :row-props="rowProps"
      style="margin-top: 8px"
    />

    <n-modal
      v-model:show="showEditModal"
      preset="dialog"
      title="编辑需求"
      positive-text="保存"
      class="requirement-form-modal"
      @positive-click="onSaveEdit"
    >
      <n-form label-placement="top">
        <n-form-item label="标题" required>
          <n-input v-model:value="editForm.title" placeholder="需求标题" />
        </n-form-item>
        <n-grid :cols="2" :x-gap="12">
          <n-gi>
            <n-form-item label="优先级">
              <n-select v-model:value="editForm.priority" :options="prioritySelectOptions" />
            </n-form-item>
          </n-gi>
          <n-gi>
            <n-form-item label="需求类型">
              <n-select v-model:value="editForm.req_type" :options="typeSelectOptions" />
            </n-form-item>
          </n-gi>
        </n-grid>
        <n-form-item label="PRD 链接">
          <n-input v-model:value="editForm.external_url" placeholder="可选" />
        </n-form-item>
        <n-form-item label="关联版本">
          <VersionSelect v-model="editForm.version_id" :project-id="ctx.projectId" />
        </n-form-item>
      </n-form>
    </n-modal>

    <n-drawer
      v-model:show="createDrawerVisible"
      :width="'min(720px, 92vw)'"
      placement="right"
      :trap-focus="false"
    >
      <n-drawer-content title="新建需求" closable body-content-style="padding: 12px 16px">
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
      :width="'min(1200px, 85vw)'"
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
  NForm,
  NFormItem,
  NGi,
  NGrid,
  NInput,
  NModal,
  NSelect,
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
  updateRequirement,
} from '@/api/requirements';
import RequirementCreateForm from '@/components/RequirementCreateForm.vue';
import type { ComponentPublicInstance } from 'vue';
import RequirementDetailPanel from '@/components/RequirementDetailPanel.vue';
import VersionSelect from '@/components/VersionSelect.vue';
import { requirementStatusLabel, requirementStatusTagType } from '@/constants/requirementStatus';
import { useRequirementProjectConfig } from '@/composables/useRequirementProjectConfig';
import { usePermissions } from '@/composables/usePermissions';
import { useContextStore } from '@/stores/context';
import type { Requirement, RequirementPriority, RequirementStatus, RequirementType } from '@/types/business';
import { NUM_TABLE_COLUMN } from '@/utils/entityNum';

const ctx = useContextStore();
const { canManageCatalog } = usePermissions();
const canCatalog = computed(() => canManageCatalog(ctx.projectId));
const projectConfig = useRequirementProjectConfig(() => ctx.projectId);

const prioritySelectOptions = computed(() =>
  projectConfig.priorityOptions.value.map((o) => ({ label: o.label, value: o.option_key }))
);
const typeSelectOptions = computed(() =>
  projectConfig.typeOptions.value.map((o) => ({ label: o.label, value: o.option_key }))
);
const route = useRoute();
const router = useRouter();
const message = useMessage();
const dialog = useDialog();
const rows = ref<Requirement[]>([]);
const loading = ref(false);
const showEditModal = ref(false);
const createDrawerVisible = ref(false);
const creating = ref(false);
const editing = ref<Requirement | null>(null);
const drawerVisible = ref(false);
const activeReqId = ref<string | null>(null);

const createFormRef = ref<ComponentPublicInstance<{
  reset: () => void;
  validate: () => string | null;
  getPayload: () => import('@/components/RequirementCreateForm.vue').RequirementCreatePayload;
  prepare: () => Promise<void>;
}> | null>(null);

const editForm = ref({
  title: '',
  external_url: '' as string,
  version_id: null as string | null,
  priority: 'p1' as RequirementPriority,
  req_type: 'feature' as RequirementType,
});

const activeIndex = computed(() =>
  activeReqId.value ? rows.value.findIndex((r) => r.id === activeReqId.value) : -1
);

const filterTags = computed(() => {
  const tags: { key: string; label: string; clear: () => void }[] = [];
  const vid = route.query.version_id;
  if (typeof vid === 'string' && vid) {
    tags.push({
      key: 'version',
      label: '版本已筛选',
      clear: () => {
        const q = { ...route.query };
        delete q.version_id;
        router.replace({ name: 'requirements', query: q });
      },
    });
  }
  const st = route.query.status;
  if (typeof st === 'string' && st) {
    tags.push({
      key: 'status',
      label: `状态 ${requirementStatusLabel(st)}`,
      clear: () => {
        const q = { ...route.query };
        delete q.status;
        router.replace({ name: 'requirements', query: q });
      },
    });
  }
  return tags;
});

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
    render: (row) => projectConfig.priorityLabel(row.priority),
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
  ...(canCatalog.value
    ? [
        {
          title: '操作',
          key: 'actions',
          width: 140,
          render: (row: Requirement) =>
            h('div', { style: { display: 'flex', gap: '4px' } }, [
              h(
                NButton,
                {
                  size: 'small',
                  quaternary: true,
                  onClick: (e: Event) => {
                    e.stopPropagation();
                    openEditModal(row);
                  },
                },
                () => '编辑'
              ),
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
            ]),
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
  const q = { ...route.query, id };
  router.replace({ name: 'requirements', query: q });
}

function closeDrawer() {
  drawerVisible.value = false;
  activeReqId.value = null;
  const q = { ...route.query };
  delete q.id;
  router.replace({ name: 'requirements', query: q });
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
    return;
  }
  loading.value = true;
  try {
    await projectConfig.reload();
    const params: {
      version_id?: string;
      status?: RequirementStatus;
    } = {};
    if (typeof route.query.version_id === 'string' && route.query.version_id) {
      params.version_id = route.query.version_id;
    }
    if (typeof route.query.status === 'string' && route.query.status) {
      params.status = route.query.status as RequirementStatus;
    }
    const { data } = await listRequirements(params);
    rows.value = data;
    const qid = route.query.id;
    if (typeof qid === 'string' && qid && data.some((r) => r.id === qid)) {
      activeReqId.value = qid;
      drawerVisible.value = true;
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

function openEditModal(row: Requirement) {
  editing.value = row;
  editForm.value = {
    title: row.title,
    external_url: row.external_url ?? '',
    version_id: row.version_id,
    priority: row.priority,
    req_type: row.req_type,
  };
  showEditModal.value = true;
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

async function onSaveEdit() {
  if (!editForm.value.title.trim()) {
    message.warning('请填写标题');
    return false;
  }
  if (!editing.value) return false;
  await updateRequirement(editing.value.id, {
    title: editForm.value.title.trim(),
    external_url: editForm.value.external_url.trim() || null,
    version_id: editForm.value.version_id,
    priority: editForm.value.priority,
    req_type: editForm.value.req_type,
  });
  message.success('已保存');
  showEditModal.value = false;
  await load();
  return true;
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

onMounted(load);
watch(() => ctx.projectId, load);
watch(() => route.query, load);
</script>

<style scoped>
:global(.requirement-form-modal) {
  width: min(640px, 92vw);
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
