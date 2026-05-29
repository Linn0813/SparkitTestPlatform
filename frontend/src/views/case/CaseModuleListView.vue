<template>
  <n-card title="模块管理">
    <template #header-extra>
      <n-button
        v-if="canCatalog"
        type="primary"
        :disabled="!ctx.projectId"
        @click="openModal()"
      >
        新建模块
      </n-button>
    </template>
    <n-alert v-if="!ctx.projectId" type="info" style="margin-bottom: 12px">请先选择项目</n-alert>
    <n-data-table
      v-else
      :columns="columns"
      :data="tableData"
      :loading="loading"
      :row-key="(row: ModuleTableRow) => row.id"
      :expanded-row-keys="expandedRowKeys"
      @update:expanded-row-keys="expandedRowKeys = $event"
      style="margin-top: 12px"
    />
    <n-modal
      v-model:show="showModal"
      preset="dialog"
      :title="editing ? '编辑模块' : '新建模块'"
      positive-text="保存"
      @positive-click="onSave"
    >
      <n-form label-placement="top">
        <n-form-item label="模块名称" required>
          <n-input v-model:value="form.name" placeholder="请输入模块名称" />
        </n-form-item>
        <n-form-item label="上级模块">
          <n-select
            v-model:value="form.parent_id"
            :options="parentOptions"
            clearable
            placeholder="无（作为根模块）"
            style="width: 100%"
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
  NForm,
  NFormItem,
  NInput,
  NModal,
  NSelect,
  NSpace,
  useDialog,
  useMessage,
  type DataTableColumns,
} from 'naive-ui';
import { createModule, deleteModule, listModules, updateModule } from '@/api/cases';
import { usePermissions } from '@/composables/usePermissions';
import { useContextStore } from '@/stores/context';
import type { CaseModule } from '@/types/business';
import {
  buildModuleTableTree,
  collectDescendantIds,
  collectModuleTableExpandKeys,
  modulePathLabel,
  moduleSelectOptions,
  parentModuleLabel,
  type ModuleTableRow,
} from '@/utils/moduleTree';

const ctx = useContextStore();
const { canManageCatalog } = usePermissions();
const canCatalog = computed(() => canManageCatalog(ctx.projectId));
const router = useRouter();
const message = useMessage();
const dialog = useDialog();

const modules = ref<CaseModule[]>([]);
const expandedRowKeys = ref<Array<string | number>>([]);
const loading = ref(false);
const showModal = ref(false);
const editing = ref<CaseModule | null>(null);
const form = ref({
  name: '',
  parent_id: null as string | null,
});

const tableData = computed(() => buildModuleTableTree(modules.value));

const parentOptions = computed(() => {
  const opts = moduleSelectOptions(modules.value);
  if (!editing.value) return opts;
  const invalid = collectDescendantIds(modules.value, editing.value.id);
  invalid.add(editing.value.id);
  return opts.filter((o) => !invalid.has(o.value));
});

const columns = computed<DataTableColumns<ModuleTableRow>>(() => [
  { title: '模块名称', key: 'name', minWidth: 160, tree: true },
  {
    title: '上级模块',
    key: 'parent_id',
    width: 140,
    ellipsis: { tooltip: true },
    render: (row) => parentModuleLabel(modules.value, row.parent_id),
  },
  {
    title: '路径',
    key: 'path',
    minWidth: 200,
    ellipsis: { tooltip: true },
    render: (row) => modulePathLabel(modules.value, row.id),
  },
  {
    title: '操作',
    key: 'a',
    width: 260,
    render: (row) => {
      const actions = [
        h(
          NButton,
          { size: 'small', quaternary: true, onClick: () => goCases(row.id) },
          () => '查看用例'
        ),
      ];
      if (canCatalog.value) {
        actions.unshift(
          h(NButton, { size: 'small', quaternary: true, onClick: () => openModal(row) }, () => '编辑'),
          h(
            NButton,
            { size: 'small', quaternary: true, onClick: () => openModal(undefined, row.id) },
            () => '子模块'
          ),
          h(
            NButton,
            { size: 'small', quaternary: true, type: 'error', onClick: () => onRemove(row) },
            () => '删除'
          )
        );
      }
      return h(NSpace, { size: 4, wrap: false }, () => actions);
    },
  },
]);

function apiErrorDetail(e: unknown): string | undefined {
  if (e && typeof e === 'object' && 'response' in e) {
    return (e as { response?: { data?: { detail?: string } } }).response?.data?.detail;
  }
  return undefined;
}

async function load() {
  if (!ctx.projectId) {
    modules.value = [];
    expandedRowKeys.value = [];
    return;
  }
  loading.value = true;
  try {
    const { data } = await listModules();
    modules.value = data;
    expandedRowKeys.value = collectModuleTableExpandKeys(buildModuleTableTree(data));
  } finally {
    loading.value = false;
  }
}

function openModal(row?: CaseModule, parentId?: string | null) {
  editing.value = row ?? null;
  form.value = {
    name: row?.name ?? '',
    parent_id: row?.parent_id ?? parentId ?? null,
  };
  showModal.value = true;
}

async function onSave() {
  const name = form.value.name.trim();
  if (!name) {
    message.warning('请填写模块名称');
    return false;
  }
  try {
    if (editing.value) {
      await updateModule(editing.value.id, {
        name,
        parent_id: form.value.parent_id,
      });
      message.success('已保存');
    } else {
      await createModule({
        name,
        parent_id: form.value.parent_id,
      });
      message.success('已创建');
    }
    showModal.value = false;
    await load();
    return true;
  } catch (e: unknown) {
    const detail = apiErrorDetail(e);
    message.error(typeof detail === 'string' ? detail : '保存失败');
    return false;
  }
}

function hasChildModules(moduleId: string): boolean {
  return modules.value.some((m) => m.parent_id === moduleId);
}

function moduleDeleteErrorMessage(detail: string | undefined): string {
  if (!detail) return '删除失败';
  const map: Record<string, string> = {
    'Module has child modules': '请先删除子模块',
    'Module has cases': '请先删除或移出模块内的用例',
  };
  return map[detail] ?? detail;
}

function onRemove(row: CaseModule) {
  if (hasChildModules(row.id)) {
    message.warning('请先删除该模块下的子模块');
    return;
  }
  dialog.warning({
    title: '删除模块',
    content: `确定删除模块「${row.name}」？若模块内仍有测试用例将无法删除。`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await deleteModule(row.id);
        message.success('已删除');
        await load();
      } catch (e: unknown) {
        const detail = apiErrorDetail(e);
        message.error(moduleDeleteErrorMessage(typeof detail === 'string' ? detail : undefined));
      }
    },
  });
}

function goCases(moduleId: string) {
  router.push({ name: 'cases', query: { moduleId } });
}

onMounted(load);
watch(() => ctx.projectId, load);
</script>
