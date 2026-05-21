<template>
  <n-card title="项目成员">
    <template #header-extra>
      <n-button
        v-if="canManageProjectMembers(selectedProjectId)"
        type="primary"
        :disabled="!selectedProjectId"
        @click="showAdd = true"
      >
        添加成员
      </n-button>
    </template>
    <n-form inline label-placement="left" style="margin-bottom: 12px">
      <n-form-item label="项目">
        <n-select
          v-model:value="selectedProjectId"
          :options="projectOptions"
          placeholder="选择项目"
          style="width: 240px"
          @update:value="load"
        />
      </n-form-item>
    </n-form>
    <n-alert v-if="!selectedProjectId" type="info">请选择项目</n-alert>
    <n-data-table v-else :columns="columns" :data="members" :loading="loading" />
    <n-modal v-model:show="showAdd" preset="dialog" title="添加成员" positive-text="添加" @positive-click="onAdd">
      <n-form label-placement="left" label-width="80">
        <n-form-item label="用户">
          <n-select v-model:value="addForm.user_id" :options="userOptions" filterable placeholder="选择用户" />
        </n-form-item>
        <n-form-item label="角色">
          <n-select v-model:value="addForm.role" :options="roleOptions" />
          <n-text depth="3" style="font-size: 12px; margin-top: 4px; display: block">
            管理员可管理项目与成员；测试可编辑用例/计划/缺陷；项目成员适用于开发、产品等协作角色（查看为主）。
          </n-text>
        </n-form-item>
      </n-form>
    </n-modal>
  </n-card>
</template>

<script setup lang="ts">
import { computed, h, onMounted, ref } from 'vue';
import {
  NAlert,
  NButton,
  NCard,
  NDataTable,
  NForm,
  NFormItem,
  NModal,
  NSelect,
  NTag,
  NText,
  useDialog,
  useMessage,
  type DataTableColumns,
} from 'naive-ui';
import { addProjectMember, listProjectMembers, removeProjectMember } from '@/api/projects';
import { listUsers } from '@/api/users';
import { usePermissions } from '@/composables/usePermissions';
import { useSettingScope } from '@/composables/useSettingScope';
import { useAuthStore } from '@/stores/auth';
import { useContextStore } from '@/stores/context';
import { PROJECT_ROLE_OPTIONS, projectRoleLabel } from '@/constants/projectRole';
import type { ProjectMember, User } from '@/types';

const auth = useAuthStore();
const ctx = useContextStore();
const { canManageProjectMembers } = usePermissions();
const message = useMessage();
const dialog = useDialog();

const selectedProjectId = ref<string | null>(null);
const { restoreProject } = useSettingScope(selectedProjectId);
const members = ref<ProjectMember[]>([]);
const allUsers = ref<User[]>([]);
const loading = ref(false);
const showAdd = ref(false);
const addForm = ref({ user_id: null as string | null, role: 'member' as const });

const projectOptions = computed(() =>
  (auth.me?.projects ?? []).map((p) => ({ label: p.name, value: p.id }))
);

const roleOptions = PROJECT_ROLE_OPTIONS;

const userOptions = computed(() =>
  allUsers.value.map((u) => ({ label: `${u.name} (${u.email})`, value: u.id }))
);

const columns = computed<DataTableColumns<ProjectMember>>(() => {
  const base: DataTableColumns<ProjectMember> = [
    { title: '邮箱', key: 'user', render: (r) => r.user?.email ?? r.user_id },
    { title: '姓名', key: 'name', render: (r) => r.user?.name ?? '-' },
    { title: '角色', key: 'role', render: (r) => h(NTag, null, () => projectRoleLabel(r.role)) },
  ];
  if (canManageProjectMembers(selectedProjectId.value)) {
    base.push({
      title: '操作',
      key: 'actions',
      render: (r) =>
        h(NButton, { size: 'small', type: 'error', quaternary: true, onClick: () => onRemove(r) }, () => '移除'),
    });
  }
  return base;
});

async function load() {
  if (!selectedProjectId.value) {
    members.value = [];
    return;
  }
  loading.value = true;
  try {
    const { data } = await listProjectMembers(selectedProjectId.value);
    members.value = data;
  } catch {
    members.value = [];
    message.error('加载成员失败，请确认是否选择了正确的项目且有权限');
  } finally {
    loading.value = false;
  }
}

async function loadUsers() {
  try {
    const { data } = await listUsers();
    allUsers.value = data;
  } catch {
    allUsers.value = [];
  }
}

async function onAdd() {
  if (!selectedProjectId.value || !addForm.value.user_id) {
    message.warning('请选择项目和用户');
    return false;
  }
  try {
    await addProjectMember(selectedProjectId.value, {
      user_id: addForm.value.user_id,
      role: addForm.value.role,
    });
    message.success('已添加');
    showAdd.value = false;
    addForm.value = { user_id: null, role: 'member' };
    await load();
  } catch {
    message.error('添加失败');
    return false;
  }
  return true;
}

function onRemove(row: ProjectMember) {
  if (!selectedProjectId.value) return;
  dialog.warning({
    title: '确认移除',
    content: `移除成员 ${row.user?.email ?? row.user_id}？`,
    positiveText: '移除',
    negativeText: '取消',
    onPositiveClick: async () => {
      await removeProjectMember(selectedProjectId.value!, row.id);
      message.success('已移除');
      await load();
    },
  });
}

async function init() {
  const validProjectIds = projectOptions.value.map((o) => o.value as string);
  restoreProject(validProjectIds, ctx.projectId ?? validProjectIds[0] ?? null);
  await load();
}

onMounted(() => {
  loadUsers();
  init();
});
</script>
