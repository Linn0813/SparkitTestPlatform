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
    <n-data-table
      v-else
      :columns="columns"
      :data="rows"
      :loading="loading"
      :row-props="rowProps"
    />
    <n-modal
      v-model:show="showModal"
      preset="dialog"
      :title="editing ? '编辑版本' : '新建版本'"
      positive-text="保存"
      @positive-click="onSave"
    >
      <n-form label-placement="top">
        <n-form-item label="版本类型" required>
          <n-select v-model:value="form.version_type" :options="versionTypeOptions" />
          <n-text
            v-if="editing && editing.version_type !== form.version_type"
            depth="3"
            style="display: block; font-size: 12px; margin-top: 4px"
          >
            修改类型将重置该版本工作流进度
          </n-text>
        </n-form-item>
        <n-form-item label="版本名称" required>
          <n-input v-model:value="form.name" placeholder="如 v1.2.0、Sprint-2025-W20" />
        </n-form-item>
        <n-form-item label="构建号">
          <n-input
            v-model:value="form.build_number"
            placeholder="选填，如 1234 或 1.2.0.456"
            :maxlength="64"
          />
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

    <n-drawer
      v-model:show="drawerVisible"
      :width="VERSION_DRAWER_WIDTH"
      placement="right"
      :trap-focus="false"
      @update:show="onDrawerShowChange"
    >
      <n-drawer-content :closable="false" body-content-style="padding: 0">
        <VersionDetailPanel
          v-if="activeVersionId"
          :version-id="activeVersionId"
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
  NAlert,
  NButton,
  NCard,
  NDataTable,
  NDatePicker,
  NDrawer,
  NDrawerContent,
  NForm,
  NFormItem,
  NInput,
  NModal,
  NSelect,
  NSpace,
  NTag,
  useDialog,
  useMessage,
  type DataTableColumns,
} from 'naive-ui';
import { createVersion, deleteVersion, listVersions, updateVersion } from '@/api/versions';
import VersionDetailPanel from '@/components/VersionDetailPanel.vue';
import { VERSION_TYPE_OPTIONS, versionTypeLabel } from '@/constants/versionTypes';
import { usePermissions } from '@/composables/usePermissions';
import { useContextStore } from '@/stores/context';
import type { ProjectVersion, VersionType } from '@/types/business';
import { NUM_TABLE_COLUMN } from '@/utils/entityNum';
import { versionStatusLabel, versionStatusTagType } from '@/constants/versionStatus';
import { formatDateOnly } from '@/utils/formatDateOnly';

const VERSION_DRAWER_WIDTH = 'min(1080px, 90vw)';

const route = useRoute();
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
const form = ref({
  name: '',
  build_number: '' as string,
  released_at: null as string | null,
  version_type: 'app_release' as VersionType,
});
const drawerVisible = ref(false);
const activeVersionId = ref<string | null>(null);
const applyingRoute = ref(false);

const versionTypeOptions = VERSION_TYPE_OPTIONS;

const activeIndex = computed(() =>
  activeVersionId.value ? rows.value.findIndex((r) => r.id === activeVersionId.value) : -1
);

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
          onClick: (e: Event) => {
            e.stopPropagation();
            openDetail(row.id);
          },
        },
        () => row.name
      ),
  },
  {
    title: '类型',
    key: 'version_type',
    width: 100,
    render: (row) => versionTypeLabel(row.version_type),
  },
  {
    title: '构建号',
    key: 'build_number',
    width: 120,
    ellipsis: { tooltip: true },
    render: (row) => row.build_number || '—',
  },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render: (row) =>
      h(
        NTag,
        { size: 'small', type: versionStatusTagType(row.status), bordered: false },
        () => versionStatusLabel(row.status)
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
            onClick: (e: Event) => {
              e.stopPropagation();
              router.push({ name: 'requirements', query: { version_id: row.id } });
            },
          },
          () => '查看版本需求'
        ),
        h(
          NButton,
          {
            size: 'small',
            quaternary: true,
            onClick: (e: Event) => {
              e.stopPropagation();
              router.push({ name: 'bugs', query: { plan_version_id: row.id } });
            },
          },
          () => '查看版本缺陷'
        ),
      ];
      if (canCatalog.value) {
        buttons.push(
          h(
            NButton,
            {
              size: 'small',
              quaternary: true,
              onClick: (e: Event) => {
                e.stopPropagation();
                openModal(row);
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
          )
        );
      }
      return h(NSpace, { size: 4, wrap: true }, () => buttons);
    },
  },
]);

function rowProps(row: ProjectVersion) {
  return {
    style: 'cursor: pointer',
    onClick: () => openDetail(row.id),
  };
}

function syncRouteQuery() {
  applyingRoute.value = true;
  const q: Record<string, string> = { ...route.query } as Record<string, string>;
  if (activeVersionId.value) q.versionId = activeVersionId.value;
  else delete q.versionId;
  router.replace({ name: 'versions', query: q }).finally(() => {
    applyingRoute.value = false;
  });
}

function applyRouteQuery() {
  const qid = route.query.versionId;
  if (typeof qid === 'string' && qid) {
    activeVersionId.value = qid;
    drawerVisible.value = true;
  } else if (!drawerVisible.value) {
    activeVersionId.value = null;
  }
}

function openDetail(id: string) {
  activeVersionId.value = id;
  drawerVisible.value = true;
  syncRouteQuery();
}

function closeDrawer() {
  drawerVisible.value = false;
  activeVersionId.value = null;
  syncRouteQuery();
}

function onDrawerShowChange(show: boolean) {
  if (!show) closeDrawer();
}

function goPrev() {
  const idx = activeIndex.value;
  if (idx > 0) openDetail(rows.value[idx - 1].id);
}

function goNext() {
  const idx = activeIndex.value;
  if (idx >= 0 && idx < rows.value.length - 1) openDetail(rows.value[idx + 1].id);
}

function onDetailDeleted() {
  closeDrawer();
  load();
}

function onDetailUpdated(v: ProjectVersion) {
  const idx = rows.value.findIndex((r) => r.id === v.id);
  if (idx >= 0) rows.value[idx] = v;
}

async function load() {
  if (!ctx.projectId) {
    rows.value = [];
    return;
  }
  loading.value = true;
  try {
    const { data } = await listVersions();
    rows.value = data;
    if (activeVersionId.value && !data.some((r) => r.id === activeVersionId.value)) {
      closeDrawer();
    }
  } finally {
    loading.value = false;
  }
}

function openModal(row?: ProjectVersion) {
  editing.value = row ?? null;
  form.value = {
    name: row?.name ?? '',
    build_number: row?.build_number ?? '',
    released_at: row?.released_at?.slice(0, 10) ?? null,
    version_type: row?.version_type ?? 'app_release',
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
    build_number: form.value.build_number.trim() || null,
    released_at: form.value.released_at || null,
    version_type: form.value.version_type,
  };
  const typeChanged = editing.value && editing.value.version_type !== form.value.version_type;
  if (typeChanged) {
    return new Promise<boolean>((resolve) => {
      dialog.warning({
        title: '修改版本类型',
        content: '修改类型将重置该版本全部工作流进度，是否继续？',
        positiveText: '继续',
        negativeText: '取消',
        onPositiveClick: async () => {
          const ok = await persistVersion(payload);
          resolve(ok);
        },
        onNegativeClick: () => resolve(false),
        onClose: () => resolve(false),
      });
    });
  }
  return persistVersion(payload);
}

async function persistVersion(payload: {
  name: string;
  build_number: string | null;
  released_at: string | null;
  version_type: VersionType;
}) {
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
        if (activeVersionId.value === row.id) closeDrawer();
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

onMounted(() => {
  applyRouteQuery();
  load();
});
watch(() => ctx.projectId, load);
watch(
  () => route.query.versionId,
  () => {
    if (applyingRoute.value) return;
    applyRouteQuery();
  }
);
</script>
