<template>
  <n-card title="系统用户管理">
    <template #header-extra>
      <n-button type="primary" @click="openCreate">新建用户</n-button>
    </template>
    <n-data-table :columns="columns" :data="users" :loading="loading" />
    <n-modal
      v-model:show="showModal"
      preset="dialog"
      :title="editingId ? '编辑用户' : '新建用户'"
      :positive-text="editingId ? '保存' : '创建'"
      @positive-click="onSubmit"
    >
      <n-form :model="form" label-placement="left" label-width="100">
        <n-form-item v-if="!editingId" label="邮箱"><n-input v-model:value="form.email" /></n-form-item>
        <n-form-item label="姓名"><n-input v-model:value="form.name" /></n-form-item>
        <n-form-item :label="editingId ? '新密码' : '密码'">
          <n-input
            v-model:value="form.password"
            type="password"
            :placeholder="editingId ? '留空则不修改，至少 6 位' : '至少 6 位'"
          />
        </n-form-item>
        <n-form-item label="启用"><n-switch v-model:value="form.is_active" /></n-form-item>
        <n-form-item label="系统管理员"><n-switch v-model:value="form.is_system_admin" /></n-form-item>
      </n-form>
    </n-modal>
  </n-card>
</template>

<script setup lang="ts">
import { h, onMounted, ref } from 'vue';
import {
  NButton,
  NCard,
  NDataTable,
  NForm,
  NFormItem,
  NInput,
  NModal,
  NSwitch,
  NTag,
  useMessage,
  type DataTableColumns,
} from 'naive-ui';
import { createUser, listUsers, updateUser } from '@/api/users';
import type { User } from '@/types';
import { apiErrorMessage } from '@/utils/apiError';

const message = useMessage();
const users = ref<User[]>([]);
const loading = ref(false);
const showModal = ref(false);
const editingId = ref<string | null>(null);
const form = ref({
  email: '',
  name: '',
  password: '',
  is_active: true,
  is_system_admin: false,
});

const columns: DataTableColumns<User> = [
  { title: '邮箱', key: 'email' },
  { title: '姓名', key: 'name' },
  {
    title: '状态',
    key: 'is_active',
    render: (row) => h(NTag, { type: row.is_active ? 'success' : 'error' }, () => (row.is_active ? '启用' : '禁用')),
  },
  {
    title: '系统管理员',
    key: 'is_system_admin',
    render: (row) => (row.is_system_admin ? '是' : '否'),
  },
  {
    title: '操作',
    key: 'actions',
    render: (row) =>
      h(NButton, { size: 'small', quaternary: true, type: 'primary', onClick: () => openEdit(row) }, () => '编辑'),
  },
];

function openCreate() {
  editingId.value = null;
  form.value = { email: '', name: '', password: '', is_active: true, is_system_admin: false };
  showModal.value = true;
}

function openEdit(row: User) {
  editingId.value = row.id;
  form.value = {
    email: row.email,
    name: row.name,
    password: '',
    is_active: row.is_active,
    is_system_admin: row.is_system_admin,
  };
  showModal.value = true;
}

async function load() {
  loading.value = true;
  try {
    const { data } = await listUsers();
    users.value = data;
  } finally {
    loading.value = false;
  }
}

async function onSubmit() {
  const email = form.value.email.trim();
  const name = form.value.name.trim();
  const password = form.value.password;

  if (!editingId.value) {
    if (!email) {
      message.warning('请填写邮箱');
      return false;
    }
    if (!name) {
      message.warning('请填写姓名');
      return false;
    }
    if (password.length < 6) {
      message.warning('密码至少 6 位');
      return false;
    }
  } else if (password && password.length < 6) {
    message.warning('新密码至少 6 位');
    return false;
  }

  try {
    if (editingId.value) {
      const payload: Record<string, unknown> = {
        name,
        is_active: form.value.is_active,
        is_system_admin: form.value.is_system_admin,
      };
      if (password) payload.password = password;
      await updateUser(editingId.value, payload);
      message.success('已保存');
    } else {
      await createUser({
        email,
        name,
        password,
        is_active: form.value.is_active,
        is_system_admin: form.value.is_system_admin,
      });
      message.success('创建成功');
    }
    showModal.value = false;
    await load();
  } catch (e: unknown) {
    message.error(apiErrorMessage(e, editingId.value ? '保存失败' : '创建失败'));
    return false;
  }
  return true;
}

onMounted(load);
</script>
