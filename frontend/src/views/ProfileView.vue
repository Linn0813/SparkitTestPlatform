<template>
  <n-card title="个人设置">
    <n-descriptions bordered :column="1" style="margin-bottom: 24px">
      <n-descriptions-item label="姓名">{{ auth.user?.name }}</n-descriptions-item>
      <n-descriptions-item label="邮箱">{{ auth.user?.email }}</n-descriptions-item>
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
import { useAuthStore } from '@/stores/auth';

const auth = useAuthStore();
const message = useMessage();
const saving = ref(false);
const pwdForm = ref({ old_password: '', new_password: '', confirm: '' });

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
