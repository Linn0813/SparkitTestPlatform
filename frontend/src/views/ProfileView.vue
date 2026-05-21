<template>
  <n-card title="个人设置">
    <n-form label-placement="left" label-width="100" style="max-width: 480px; margin-bottom: 24px">
      <n-form-item label="姓名">
        <n-input v-model:value="profileForm.name" placeholder="在评论、提出人中显示" />
      </n-form-item>
      <n-form-item label="邮箱">
        <n-input :value="auth.user?.email" disabled />
      </n-form-item>
      <n-form-item>
        <n-button type="primary" :loading="profileSaving" @click="onSaveProfile">保存姓名</n-button>
      </n-form-item>
    </n-form>
    <n-descriptions bordered :column="1" style="margin-bottom: 24px">
      <n-descriptions-item label="系统管理员">
        {{ auth.user?.is_system_admin ? '是' : '否' }}
      </n-descriptions-item>
    </n-descriptions>
    <n-divider />
    <n-form label-placement="left" label-width="100" style="max-width: 480px">
      <n-form-item label="当前密码">
        <n-input v-model:value="pwdForm.old_password" type="password" />
      </n-form-item>
      <n-form-item label="新密码">
        <n-input v-model:value="pwdForm.new_password" type="password" />
      </n-form-item>
      <n-form-item label="确认新密码">
        <n-input v-model:value="pwdForm.confirm" type="password" />
      </n-form-item>
      <n-form-item>
        <n-button type="primary" :loading="saving" @click="onChangePassword">修改密码</n-button>
      </n-form-item>
    </n-form>
  </n-card>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import {
  NButton,
  NCard,
  NDescriptions,
  NDescriptionsItem,
  NDivider,
  NForm,
  NFormItem,
  NInput,
  useMessage,
} from 'naive-ui';
import { changePassword } from '@/api/auth';
import { updateMyProfile } from '@/api/users';
import { useAuthStore } from '@/stores/auth';
import { watch } from 'vue';

const auth = useAuthStore();
const message = useMessage();
const saving = ref(false);
const profileSaving = ref(false);
const profileForm = ref({ name: '' });
const pwdForm = ref({ old_password: '', new_password: '', confirm: '' });

watch(
  () => auth.user?.name,
  (name) => {
    profileForm.value.name = name ?? '';
  },
  { immediate: true }
);

async function onSaveProfile() {
  const name = profileForm.value.name.trim();
  if (!name) {
    message.warning('请填写姓名');
    return;
  }
  profileSaving.value = true;
  try {
    await updateMyProfile({ name });
    await auth.loadMe();
    message.success('姓名已更新');
  } catch {
    message.error('保存失败');
  } finally {
    profileSaving.value = false;
  }
}

async function onChangePassword() {
  if (!pwdForm.value.old_password || !pwdForm.value.new_password) {
    message.warning('请填写密码');
    return;
  }
  if (pwdForm.value.new_password !== pwdForm.value.confirm) {
    message.warning('两次新密码不一致');
    return;
  }
  saving.value = true;
  try {
    await changePassword(pwdForm.value.old_password, pwdForm.value.new_password);
    message.success('密码已修改');
    pwdForm.value = { old_password: '', new_password: '', confirm: '' };
  } catch {
    message.error('修改失败，请检查当前密码');
  } finally {
    saving.value = false;
  }
}
</script>
