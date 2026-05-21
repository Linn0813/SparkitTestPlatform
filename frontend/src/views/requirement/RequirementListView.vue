<template>
  <n-card title="需求管理">
    <template #header-extra>
      <n-button
        v-if="canCatalog"
        type="primary"
        :disabled="!ctx.projectId"
        @click="openModal()"
      >
        新建需求
      </n-button>
    </template>
    <n-space v-if="filterTags.length" align="center" style="margin-top: 8px; margin-bottom: 8px">
      <n-text depth="3">筛选：</n-text>
      <n-tag v-for="t in filterTags" :key="t.key" closable @close="t.clear">{{ t.label }}</n-tag>
    </n-space>
    <n-data-table :columns="columns" :data="rows" :loading="loading" style="margin-top: 8px" />
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
        <n-form-item label="PRD / 外部链接">
          <n-input v-model:value="form.external_url" placeholder="可选，粘贴禅道/Jira/PRD 链接" />
        </n-form-item>
        <n-form-item label="关联版本">
          <VersionSelect v-model="form.version_id" :project-id="ctx.projectId" />
        </n-form-item>
        <n-form-item label="状态">
          <n-select
            v-model:value="form.status"
            :options="[...REQUIREMENT_STATUS_OPTIONS]"
          />
        </n-form-item>
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
  NDataTable,
  NForm,
  NFormItem,
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
import VersionSelect from '@/components/VersionSelect.vue';
import { REQUIREMENT_STATUS_OPTIONS, requirementStatusLabel } from '@/constants/requirementStatus';
import { usePermissions } from '@/composables/usePermissions';
import { useContextStore } from '@/stores/context';
import type { Requirement } from '@/types/business';
import { NUM_TABLE_COLUMN } from '@/utils/entityNum';

const ctx = useContextStore();
const { canManageCatalog } = usePermissions();
const canCatalog = computed(() => canManageCatalog(ctx.projectId));
const route = useRoute();
const router = useRouter();
const message = useMessage();
const dialog = useDialog();
const rows = ref<Requirement[]>([]);
const loading = ref(false);
const showModal = ref(false);
const editing = ref<Requirement | null>(null);
const form = ref({
  title: '',
  external_url: '' as string,
  version_id: null as string | null,
  status: 'not_tested' as string,
});

const filterTags = computed(() => {
  const tags: { key: string; label: string; clear: () => void }[] = [];
  const vid = route.query.version_id;
  if (typeof vid === 'string' && vid) {
    tags.push({
      key: 'version',
      label: `版本已筛选`,
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
    render: (r) => requirementStatusLabel(r.status),
  },
  {
    title: 'PRD 链接',
    key: 'external_url',
    width: 200,
    render: (r) => {
      if (!r.external_url) return '—';
      const url = r.external_url;
      const label = url.length > 32 ? `${url.slice(0, 32)}…` : url;
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
        h(NButton, { size: 'small', quaternary: true, onClick: () => goCases(row.id) }, () => '查看用例'),
      ];
      if (canCatalog.value) {
        actions.push(
          h(NButton, { size: 'small', quaternary: true, onClick: () => openModal(row) }, () => '编辑'),
          h(
            NButton,
            { size: 'small', quaternary: true, type: 'error',
            onClick: () => onRemove(row) },
            () => '删除'
          )
        );
      }
      return h(NSpace, { size: 4 }, () => actions);
    },
  },
]);

function goCases(requirementId: string) {
  router.push({ name: 'cases', query: { requirement_id: requirementId } });
}

async function load() {
  if (!ctx.projectId) {
    rows.value = [];
    return;
  }
  loading.value = true;
  try {
    const params: { version_id?: string; status?: import('@/types/business').RequirementStatus } = {};
    if (typeof route.query.version_id === 'string' && route.query.version_id) {
      params.version_id = route.query.version_id;
    }
    if (typeof route.query.status === 'string' && route.query.status) {
      params.status = route.query.status as import('@/types/business').RequirementStatus;
    }
    const { data } = await listRequirements(params);
    rows.value = data;
  } finally {
    loading.value = false;
  }
}

function openModal(row?: Requirement) {
  editing.value = row ?? null;
  form.value = {
    title: row?.title ?? '',
    external_url: row?.external_url ?? '',
    version_id: row?.version_id ?? null,
    status: row?.status ?? 'not_tested',
  };
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
    status: form.value.status as import('@/types/business').RequirementStatus,
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
