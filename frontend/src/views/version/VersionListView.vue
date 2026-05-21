<template>
  <n-card title="版本管理">
    <template #header-extra>
      <n-button
        v-if="canCatalog"
        type="primary"
        :disabled="!ctx.projectId"
        @click="openModal()"
      >
        新建版本
      </n-button>
    </template>
    <n-alert v-if="!ctx.projectId" type="info" style="margin-bottom: 12px">请先选择项目</n-alert>
    <n-data-table v-else :columns="columns" :data="rows" :loading="loading" />
    <n-modal
      v-model:show="showModal"
      preset="dialog"
      :title="editing ? '编辑版本' : '新建版本'"
      positive-text="保存"
      @positive-click="onSave"
    >
      <n-form label-placement="top">
        <n-form-item label="版本名称" required>
          <n-input v-model:value="form.name" placeholder="如 v1.2.0、Sprint-2025-W20" />
        </n-form-item>
        <n-form-item label="上线时间">
          <n-date-picker
            v-model:formatted-value="form.released_at"
            value-format="yyyy-MM-dd"
            type="date"
            clearable
            style="width: 100%"
            placeholder="选择上线日期"
          />
        </n-form-item>
      </n-form>
    </n-modal>
  </n-card>
</template>

<script setup lang="ts">
import { computed, h, onMounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import {
  NAlert,
  NButton,
  NCard,
  NDataTable,
  NDatePicker,
  NForm,
  NFormItem,
  NInput,
  NModal,
  NSpace,
  useDialog,
  useMessage,
  type DataTableColumns,
} from 'naive-ui';
import { createVersion, deleteVersion, listVersions, updateVersion } from '@/api/versions';
import { usePermissions } from '@/composables/usePermissions';
import { useContextStore } from '@/stores/context';
import type { ProjectVersion } from '@/types/business';
import { NUM_TABLE_COLUMN } from '@/utils/entityNum';
import { formatDateOnly } from '@/utils/formatDateOnly';

const router = useRouter();
const ctx = useContextStore();
const { canManageCatalog } = usePermissions();
const canCatalog = computed(() => canManageCatalog(ctx.projectId));
const message = useMessage();
const dialog = useDialog();
const rows = ref<ProjectVersion[]>([]);
const loading = ref(false);
const showModal = ref(false);
const editing = ref<ProjectVersion | null>(null);
const form = ref({ name: '', released_at: null as string | null });

const columns = computed<DataTableColumns<ProjectVersion>>(() => [
  { ...NUM_TABLE_COLUMN },
  {
    title: '名称',
    key: 'name',
    width: 200,
    maxWidth: 240,
    ellipsis: { tooltip: true },
    render: (row) =>
      h(
        NButton,
        {
          text: true,
          type: 'primary',
          onClick: () => router.push({ name: 'version-detail', params: { id: row.id } }),
        },
        () => row.name
      ),
  },
  {
    title: '上线时间',
    key: 'released_at',
    width: 120,
    render: (row) => formatDateOnly(row.released_at),
  },
  {
    title: '操作',
    key: 'a',
    width: 320,
    render: (row) => {
      const buttons = [
        h(
          NButton,
          {
            size: 'small',
            quaternary: true,
            onClick: () =>
              router.push({ name: 'requirements', query: { version_id: row.id } }),
          },
          () => '查看版本需求'
        ),
        h(
          NButton,
          {
            size: 'small',
            quaternary: true,
            onClick: () => router.push({ name: 'bugs', query: { plan_version_id: row.id } }),
          },
          () => '查看版本缺陷'
        ),
      ];
      if (canCatalog.value) {
        buttons.push(
          h(NButton, { size: 'small', quaternary: true, onClick: () => openModal(row) }, () => '编辑'),
          h(
            NButton,
            { size: 'small', quaternary: true, type: 'error', onClick: () => onRemove(row) },
            () => '删除'
          )
        );
      }
      return h(NSpace, { size: 4, wrap: true }, () => buttons);
    },
  },
]);

async function load() {
  if (!ctx.projectId) {
    rows.value = [];
    return;
  }
  loading.value = true;
  try {
    const { data } = await listVersions();
    rows.value = data;
  } finally {
    loading.value = false;
  }
}

function openModal(row?: ProjectVersion) {
  editing.value = row ?? null;
  form.value = {
    name: row?.name ?? '',
    released_at: row?.released_at?.slice(0, 10) ?? null,
  };
  showModal.value = true;
}

async function onSave() {
  if (!form.value.name.trim()) {
    message.warning('请填写版本名称');
    return false;
  }
  const payload = {
    name: form.value.name.trim(),
    released_at: form.value.released_at || null,
  };
  try {
    if (editing.value) {
      await updateVersion(editing.value.id, payload);
      message.success('已保存');
    } else {
      await createVersion(payload);
      message.success('已创建');
    }
    showModal.value = false;
    await load();
    return true;
  } catch (e: unknown) {
    const detail =
      (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? '保存失败';
    message.error(typeof detail === 'string' ? detail : '保存失败');
    return false;
  }
}

function onRemove(row: ProjectVersion) {
  dialog.warning({
    title: '删除版本',
    content: `确定删除「${row.name}」？若仍被缺陷或需求引用将无法删除。`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await deleteVersion(row.id);
        message.success('已删除');
        await load();
      } catch (e: unknown) {
        const detail =
          (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
          '删除失败';
        message.error(typeof detail === 'string' ? detail : '删除失败');
      }
    },
  });
}

onMounted(load);
watch(() => ctx.projectId, load);
</script>
