<template>
  <n-card
    :bordered="!embedded"
    :title="embedded ? undefined : '项目管理'"
    :header-style="embedded ? 'padding: 0 0 12px' : undefined"
    :content-style="embedded ? 'padding: 0' : undefined"
  >
    <template #header-extra>
      <n-button v-if="canCreateProject()" type="primary" @click="showCreate = true">新建项目</n-button>
    </template>
    <n-text v-if="!canCreateProject()" depth="3" style="display: block; margin-bottom: 12px">
      仅系统管理员可新建项目
    </n-text>
    <n-data-table :columns="columns" :data="projects" :loading="loading" />

    <n-modal v-model:show="showCreate" preset="dialog" title="新建项目" positive-text="创建" @positive-click="onCreate">
      <n-form label-width="80">
        <n-form-item label="名称"><n-input v-model:value="form.name" /></n-form-item>
      </n-form>
    </n-modal>

    <n-modal v-model:show="showEdit" preset="dialog" title="编辑项目" positive-text="保存" @positive-click="onSave">
      <n-form label-width="80">
        <n-form-item label="名称"><n-input v-model:value="editForm.name" /></n-form-item>
        <n-form-item label="启用"><n-switch v-model:value="editForm.is_enabled" /></n-form-item>
      </n-form>
    </n-modal>
  </n-card>
</template>

<script setup lang="ts">
import { computed, h, onMounted, ref } from 'vue';
import {
  NButton,
  NCard,
  NDataTable,
  NForm,
  NFormItem,
  NInput,
  NModal,
  NPopconfirm,
  NSpace,
  NSwitch,
  NTag,
  NText,
  useMessage,
  type DataTableColumns,
} from 'naive-ui';
import { createProject, deleteProject, listProjects, updateProject } from '@/api/projects';
import { usePermissions } from '@/composables/usePermissions';
import { useAuthStore } from '@/stores/auth';
import { useContextStore } from '@/stores/context';
import type { Project } from '@/types';

withDefaults(defineProps<{ embedded?: boolean }>(), { embedded: false });

const auth = useAuthStore();
const ctx = useContextStore();
const { canCreateProject, canDeleteProject, canEditProject } = usePermissions();
const message = useMessage();

const projects = ref<Project[]>([]);
const loading = ref(false);
const showCreate = ref(false);
const showEdit = ref(false);
const form = ref({ name: '' });
const editForm = ref({ id: '', name: '', is_enabled: true });

const columns = computed<DataTableColumns<Project>>(() => [
  { title: '名称', key: 'name' },
  {
    title: '状态',
    key: 'is_enabled',
    width: 90,
    render: (row) => h(NTag, { type: row.is_enabled ? 'success' : 'error', size: 'small' }, () => (row.is_enabled ? '启用' : '禁用')),
  },
  {
    title: '操作',
    key: 'actions',
    width: 220,
    render: (row) => {
      const actions: ReturnType<typeof h>[] = [];
      if (canEditProject(row.id)) {
        actions.push(
          h(NButton, { size: 'small', quaternary: true, onClick: () => openEdit(row) }, () => '编辑')
        );
      }
      actions.push(
        h(
          NButton,
          {
            size: 'small',
            quaternary: true,
            type: 'primary',
            onClick: async () => {
              await ctx.switchProject(row.id);
              await auth.loadMe();
              message.success('已切换当前项目');
            },
          },
          () => '设为当前'
        )
      );
      if (canDeleteProject()) {
        actions.push(
          h(
            NPopconfirm,
            {
              onPositiveClick: () => onDelete(row),
            },
            {
              trigger: () =>
                h(NButton, { size: 'small', quaternary: true, type: 'error' }, () => '删除'),
              default: () =>
                `确定删除项目「${row.name}」？不可恢复，将删除需求、用例、缺陷、计划等全部数据。`,
            }
          )
        );
      }
      return h(NSpace, null, () => actions);
    },
  },
]);

async function load() {
  loading.value = true;
  try {
    const { data } = await listProjects();
    projects.value = data;
  } finally {
    loading.value = false;
  }
}

async function onCreate() {
  if (!form.value.name.trim()) {
    message.warning('请填写项目名称');
    return false;
  }
  const { data } = await createProject({ name: form.value.name.trim() });
  message.success('项目已创建');
  showCreate.value = false;
  form.value = { name: '' };
  await auth.loadMe();
  await load();
  await ctx.switchProject(data.id);
  return true;
}

function openEdit(row: Project) {
  editForm.value = { id: row.id, name: row.name, is_enabled: row.is_enabled };
  showEdit.value = true;
}

async function onSave() {
  await updateProject(editForm.value.id, {
    name: editForm.value.name,
    is_enabled: editForm.value.is_enabled,
  });
  message.success('已保存');
  showEdit.value = false;
  await auth.loadMe();
  await load();
  return true;
}

async function onDelete(row: Project) {
  const deletedId = row.id;
  try {
    await deleteProject(deletedId);
    message.success('项目已删除');
    await auth.loadMe();
    if (ctx.projectId === deletedId) {
      const nextId = auth.me?.projects[0]?.id ?? null;
      if (nextId) {
        await ctx.switchProject(nextId);
      } else {
        ctx.reset();
      }
    }
    await load();
  } catch {
    message.error('删除失败，请稍后重试');
  }
}

onMounted(load);
</script>
