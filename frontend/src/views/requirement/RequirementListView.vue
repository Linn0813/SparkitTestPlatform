<template>
  <n-card title="需求管理">
    <template #header-extra>
      <n-button
        v-if="canCatalog"
        type="primary"
        :disabled="!ctx.projectId"
        @click="openCreateModal()"
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
      v-model:show="showModal"
      preset="dialog"
      :title="editing ? '编辑需求' : '新建需求'"
      positive-text="保存"
      @positive-click="onSave"
    >
      <n-form label-placement="top">
        <n-form-item label="标题" required>
          <n-input v-model:value="form.title" placeholder="需求标题" />
        </n-form-item>
        <n-grid :cols="2" :x-gap="12">
          <n-gi>
            <n-form-item label="优先级">
              <n-select v-model:value="form.priority" :options="prioritySelectOptions" />
            </n-form-item>
          </n-gi>
          <n-gi>
            <n-form-item label="需求类型">
              <n-select v-model:value="form.req_type" :options="typeSelectOptions" />
            </n-form-item>
          </n-gi>
        </n-grid>
        <n-form-item label="PRD / 外部链接">
          <n-input v-model:value="form.external_url" placeholder="可选，粘贴禅道/Jira/PRD 链接" />
        </n-form-item>
        <n-form-item label="关联版本">
          <VersionSelect v-model="form.version_id" :project-id="ctx.projectId" />
        </n-form-item>
        <n-grid :cols="2" :x-gap="12">
          <n-gi v-for="role in createRoleFields" :key="role.key">
            <n-form-item :label="role.label">
              <n-select
                v-model:value="form[role.idField]"
                :options="memberOptions"
                clearable
                filterable
                placeholder="选择负责人"
              />
            </n-form-item>
          </n-gi>
        </n-grid>
      </n-form>
    </n-modal>

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
import RequirementDetailPanel from '@/components/RequirementDetailPanel.vue';
import VersionSelect from '@/components/VersionSelect.vue';
import { LEGACY_ROLE_ID_FIELDS } from '@/constants/requirementNodes';
import { requirementStatusLabel, requirementStatusTagType } from '@/constants/requirementStatus';
import { useProjectMemberOptions } from '@/composables/useProjectMemberOptions';
import { useRequirementProjectConfig } from '@/composables/useRequirementProjectConfig';
import { usePermissions } from '@/composables/usePermissions';
import { useContextStore } from '@/stores/context';
import type { Requirement, RequirementPriority, RequirementStatus, RequirementType } from '@/types/business';
import { NUM_TABLE_COLUMN } from '@/utils/entityNum';

const ctx = useContextStore();
const { canManageCatalog } = usePermissions();
const canCatalog = computed(() => canManageCatalog(ctx.projectId));
const { options: memberOptions } = useProjectMemberOptions(computed(() => ctx.projectId));
const projectConfig = useRequirementProjectConfig(() => ctx.projectId);

const prioritySelectOptions = computed(() =>
  projectConfig.priorityOptions.value.map((o) => ({ label: o.label, value: o.option_key }))
);
const typeSelectOptions = computed(() =>
  projectConfig.typeOptions.value.map((o) => ({ label: o.label, value: o.option_key }))
);
const createRoleFields = computed(() =>
  projectConfig.roles.value
    .filter((r) => LEGACY_ROLE_ID_FIELDS[r.role_key])
    .map((r) => ({
      key: r.role_key,
      label: r.label,
      idField: LEGACY_ROLE_ID_FIELDS[r.role_key] as keyof typeof form.value,
    }))
);
const route = useRoute();
const router = useRouter();
const message = useMessage();
const dialog = useDialog();
const rows = ref<Requirement[]>([]);
const loading = ref(false);
const showModal = ref(false);
const editing = ref<Requirement | null>(null);
const drawerVisible = ref(false);
const activeReqId = ref<string | null>(null);

const form = ref({
  title: '',
  external_url: '' as string,
  version_id: null as string | null,
  priority: 'p1' as RequirementPriority,
  req_type: 'feature' as RequirementType,
  frontend_rd_id: null as string | null,
  backend_rd_id: null as string | null,
  pm_id: null as string | null,
  tech_owner_id: null as string | null,
  qa_id: null as string | null,
  designer_id: null as string | null,
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
  { ...NUM_TABLE_COLUMN },
  {
    title: '标题',
    key: 'title',
    width: 180,
    minWidth: 120,
    ellipsis: { tooltip: true },
  },
  {
    title: '优先级',
    key: 'priority',
    width: 70,
    render: (r) => projectConfig.priorityLabel(r.priority),
  },
  {
    title: '类型',
    key: 'req_type',
    width: 90,
    render: (r) => projectConfig.typeLabel(r.req_type),
  },
  {
    title: '关联版本',
    key: 'version',
    width: 120,
    ellipsis: { tooltip: true },
    render: (r) => (r.version ? r.version.name : '—'),
  },
  {
    title: '状态',
    key: 'status',
    width: 90,
    render: (r) =>
      h(
        NTag,
        { size: 'small', type: requirementStatusTagType(r.status), bordered: false },
        () => requirementStatusLabel(r.status)
      ),
  },
  {
    title: 'PRD 链接',
    key: 'external_url',
    width: 160,
    render: (r) => {
      if (!r.external_url) return '—';
      const url = r.external_url;
      const label = url.length > 28 ? `${url.slice(0, 28)}…` : url;
      return h(
        NTooltip,
        {
          placement: 'top-start',
          contentStyle: { maxWidth: '400px', wordBreak: 'break-all' },
        },
        {
          trigger: () =>
            h(
              'a',
              {
                href: url,
                target: '_blank',
                rel: 'noopener',
                class: 'prd-link',
                onClick: (e: MouseEvent) => e.stopPropagation(),
              },
              label
            ),
          default: () => url,
        }
      );
    },
  },
  {
    title: '操作',
    key: 'a',
    width: 200,
    render: (row) => {
      const actions = [
        h(NButton, { size: 'small', quaternary: true, onClick: (e: Event) => { e.stopPropagation(); goCases(row.id); } }, () => '查看用例'),
      ];
      if (canCatalog.value) {
        actions.push(
          h(NButton, { size: 'small', quaternary: true, onClick: (e: Event) => { e.stopPropagation(); openCreateModal(row); } }, () => '编辑'),
          h(
            NButton,
            {
              size: 'small',
              quaternary: true,
              type: 'error',
              onClick: (e: Event) => { e.stopPropagation(); onRemove(row); },
            },
            () => '删除'
          )
        );
      }
      return h(NSpace, { size: 4 }, () => actions);
    },
  },
]);

function rowProps(row: Requirement) {
  return {
    style: 'cursor: pointer',
    onClick: () => openDrawer(row.id),
  };
}

function goCases(requirementId: string) {
  router.push({ name: 'cases', query: { requirement_id: requirementId } });
}

function openDrawer(id: string) {
  activeReqId.value = id;
  drawerVisible.value = true;
  router.replace({ name: 'requirements', query: { ...route.query, id } });
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
  const idx = activeIndex.value;
  if (idx > 0) openDrawer(rows.value[idx - 1].id);
}

function goNext() {
  const idx = activeIndex.value;
  if (idx >= 0 && idx < rows.value.length - 1) openDrawer(rows.value[idx + 1].id);
}

async function onDetailDeleted() {
  closeDrawer();
  await load();
}

async function onDetailUpdated(updated: Requirement) {
  const idx = rows.value.findIndex((r) => r.id === updated.id);
  if (idx >= 0) rows.value[idx] = updated;
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

function resetForm() {
  form.value = {
    title: '',
    external_url: '',
    version_id: null,
    priority: 'p1',
    req_type: 'feature',
    frontend_rd_id: null,
    backend_rd_id: null,
    pm_id: null,
    tech_owner_id: null,
    qa_id: null,
    designer_id: null,
  };
}

function openCreateModal(row?: Requirement) {
  editing.value = row ?? null;
  if (row) {
    form.value = {
      title: row.title,
      external_url: row.external_url ?? '',
      version_id: row.version_id,
      priority: row.priority,
      req_type: row.req_type,
      frontend_rd_id: row.frontend_rd_id,
      backend_rd_id: row.backend_rd_id,
      pm_id: row.pm_id,
      tech_owner_id: row.tech_owner_id,
      qa_id: row.qa_id,
      designer_id: row.designer_id,
    };
  } else {
    resetForm();
  }
  showModal.value = true;
}

async function onSave() {
  if (!form.value.title.trim()) {
    message.warning('请填写标题');
    return false;
  }
  const payload = {
    title: form.value.title.trim(),
    external_url: form.value.external_url.trim() || null,
    version_id: form.value.version_id,
    priority: form.value.priority,
    req_type: form.value.req_type,
    frontend_rd_id: form.value.frontend_rd_id,
    backend_rd_id: form.value.backend_rd_id,
    pm_id: form.value.pm_id,
    tech_owner_id: form.value.tech_owner_id,
    qa_id: form.value.qa_id,
    designer_id: form.value.designer_id,
  };
  if (editing.value) {
    await updateRequirement(editing.value.id, payload);
    message.success('已保存');
  } else {
    await createRequirement(payload);
    message.success('已创建');
  }
  showModal.value = false;
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
