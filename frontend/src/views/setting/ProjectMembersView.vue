<template>
  <n-card
    :bordered="!embedded"
    :title="embedded ? undefined : '项目成员'"
    :header-style="embedded ? 'padding: 0 0 12px' : undefined"
    :content-style="embedded ? 'padding: 0' : undefined"
  >
    <template #header-extra>
      <n-button
        v-if="canManageProjectMembers(ctx.projectId)"
        type="primary"
        :disabled="!ctx.projectId"
        @click="showAdd = true"
      >
        添加成员
      </n-button>
    </template>
    <n-alert v-if="!ctx.projectId" type="info" style="margin-bottom: 12px">请先在顶栏选择项目</n-alert>
    <n-data-table v-else :columns="columns" :data="members" :loading="loading" />
    <n-modal v-model:show="showAdd" preset="dialog" title="添加成员" positive-text="添加" @positive-click="onAdd">
      <n-form label-placement="left" label-width="80">
        <n-form-item label="用户">
          <n-select v-model:value="addForm.user_id" :options="userOptions" filterable placeholder="选择用户" />
        </n-form-item>
        <n-form-item label="管理员">
          <n-switch v-model:value="addForm.is_project_admin" />
        </n-form-item>
        <n-form-item label="职能">
          <n-select
            v-model:value="addForm.specialtyRole"
            :options="specialtyRoleOptions"
            clearable
            placeholder="无（普通项目成员）"
          />
          <n-text depth="3" style="font-size: 12px; margin-top: 4px; display: block">
            非管理员即为项目成员；可额外指定测试/产品/开发以授予对应业务权限。管理员负责项目配置。
          </n-text>
        </n-form-item>
      </n-form>
    </n-modal>
    <n-modal
      v-model:show="showEdit"
      preset="dialog"
      title="编辑成员"
      positive-text="保存"
      @positive-click="onEditSave"
    >
      <n-form label-placement="left" label-width="80">
        <n-form-item label="邮箱">
          <n-input :value="editForm.email" disabled />
          <n-text depth="3" style="font-size: 12px; margin-top: 4px; display: block">
            邮箱为登录账号，不可在此修改
          </n-text>
        </n-form-item>
        <n-form-item label="姓名">
          <n-input v-model:value="editForm.name" :disabled="!isSystemAdmin" placeholder="姓名" />
        </n-form-item>
        <n-form-item label="管理员">
          <n-switch v-model:value="editForm.is_project_admin" />
        </n-form-item>
        <n-form-item label="职能">
          <n-select
            v-model:value="editForm.specialtyRole"
            :options="specialtyRoleOptions"
            clearable
            placeholder="无（普通项目成员）"
          />
        </n-form-item>
      </n-form>
    </n-modal>
  </n-card>
</template>

<script setup lang="ts">
import { computed, h, onMounted, ref, watch } from 'vue';
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
  NSwitch,
  NTag,
  NText,
  useDialog,
  useMessage,
  type DataTableColumns,
} from 'naive-ui';
import {
  addProjectMember,
  listProjectMembers,
  removeProjectMember,
  updateProjectMember,
} from '@/api/projects';
import { listUsers, updateUser } from '@/api/users';
import { usePermissions } from '@/composables/usePermissions';
import { useAuthStore } from '@/stores/auth';
import { useContextStore } from '@/stores/context';
import {
  SPECIALTY_ROLE_OPTIONS,
  memberRoleDisplay,
  memberRoleFromSpecialty,
  specialtyRoleFromMember,
} from '@/constants/projectRole';
import type { SpecialtyBusinessRoleValue } from '@/constants/projectRole';
import type { ProjectMember, User } from '@/types';
import { apiErrorMessage } from '@/utils/apiError';

withDefaults(defineProps<{ embedded?: boolean }>(), { embedded: false });

const auth = useAuthStore();
const ctx = useContextStore();
const { canManageProjectMembers, isSystemAdmin } = usePermissions();
const message = useMessage();
const dialog = useDialog();

const members = ref<ProjectMember[]>([]);
const allUsers = ref<User[]>([]);
const loading = ref(false);
const showAdd = ref(false);
const showEdit = ref(false);
const addForm = ref({
  user_id: null as string | null,
  specialtyRole: null as SpecialtyBusinessRoleValue | null,
  is_project_admin: false,
});
const editingMember = ref<ProjectMember | null>(null);
const editForm = ref({
  email: '',
  name: '',
  specialtyRole: null as SpecialtyBusinessRoleValue | null,
  is_project_admin: false,
});

const specialtyRoleOptions = SPECIALTY_ROLE_OPTIONS;

const userOptions = computed(() =>
  allUsers.value.map((u) => ({ label: `${u.name} (${u.email})`, value: u.id }))
);

const canManage = computed(() => canManageProjectMembers(ctx.projectId));

const columns = computed<DataTableColumns<ProjectMember>>(() => {
  const base: DataTableColumns<ProjectMember> = [
    { title: '邮箱', key: 'user', render: (r) => r.user?.email ?? r.user_id },
    { title: '姓名', key: 'name', render: (r) => r.user?.name ?? '-' },
    {
      title: '管理员',
      key: 'is_project_admin',
      width: 90,
      render: (r) =>
        h(
          NTag,
          { size: 'small', type: r.is_project_admin ? 'success' : 'default' },
          () => (r.is_project_admin ? '是' : '否')
        ),
    },
    {
      title: '角色',
      key: 'role',
      render: (r) => {
        const label = memberRoleDisplay(r);
        if (label === '—') return h(NText, { depth: 3 }, () => label);
        return h(NTag, { size: 'small' }, () => label);
      },
    },
  ];
  if (canManage.value) {
    base.push({
      title: '操作',
      key: 'actions',
      render: (r) =>
        h(NSpace, { size: 4 }, () => [
          h(NButton, { size: 'small', quaternary: true, type: 'primary', onClick: () => openEdit(r) }, () => '编辑'),
          h(NButton, { size: 'small', type: 'error', quaternary: true, onClick: () => onRemove(r) }, () => '移除'),
        ]),
    });
  }
  return base;
});

async function refreshAuthIfSelf(member: ProjectMember) {
  if (member.user_id === auth.user?.id) {
    await auth.loadMe();
  }
}

function openEdit(row: ProjectMember) {
  editingMember.value = row;
  editForm.value = {
    email: row.user?.email ?? '',
    name: row.user?.name ?? '',
    specialtyRole: specialtyRoleFromMember(row.role),
    is_project_admin: row.is_project_admin,
  };
  showEdit.value = true;
}

async function onEditSave() {
  const row = editingMember.value;
  if (!ctx.projectId || !row) return false;

  const newRole = memberRoleFromSpecialty(editForm.value.specialtyRole);
  const nameChanged = isSystemAdmin.value && editForm.value.name.trim() !== (row.user?.name ?? '');
  const roleChanged = newRole !== row.role;
  const adminChanged = editForm.value.is_project_admin !== row.is_project_admin;

  if (!nameChanged && !roleChanged && !adminChanged) {
    showEdit.value = false;
    return true;
  }

  try {
    if (nameChanged) {
      await updateUser(row.user_id, { name: editForm.value.name.trim() });
    }
    if (roleChanged || adminChanged) {
      await updateProjectMember(ctx.projectId, row.id, {
        role: newRole,
        is_project_admin: editForm.value.is_project_admin,
      });
      await refreshAuthIfSelf(row);
    }
    message.success('已保存');
    showEdit.value = false;
    editingMember.value = null;
    await load();
  } catch (e) {
    message.error(apiErrorMessage(e, '保存失败'));
    return false;
  }
  return true;
}

async function load() {
  if (!ctx.projectId) {
    members.value = [];
    return;
  }
  loading.value = true;
  try {
    const { data } = await listProjectMembers(ctx.projectId);
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
  if (!ctx.projectId || !addForm.value.user_id) {
    message.warning('请先在顶栏选择项目并选择用户');
    return false;
  }
  try {
    await addProjectMember(ctx.projectId, {
      user_id: addForm.value.user_id,
      role: memberRoleFromSpecialty(addForm.value.specialtyRole),
      is_project_admin: addForm.value.is_project_admin,
    });
    message.success('已添加');
    showAdd.value = false;
    addForm.value = { user_id: null, specialtyRole: null, is_project_admin: false };
    await load();
  } catch {
    message.error('添加失败');
    return false;
  }
  return true;
}

function onRemove(row: ProjectMember) {
  const projectId = ctx.projectId;
  if (!projectId) return;
  dialog.warning({
    title: '确认移除',
    content: `移除成员 ${row.user?.email ?? row.user_id}？`,
    positiveText: '移除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await removeProjectMember(projectId, row.id);
        message.success('已移除');
        await load();
      } catch (e) {
        message.error(apiErrorMessage(e, '移除失败'));
      }
    },
  });
}

watch(() => ctx.projectId, () => {
  void load();
});

onMounted(() => {
  loadUsers();
  void load();
});
</script>
