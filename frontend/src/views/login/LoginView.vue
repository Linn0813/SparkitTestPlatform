<template>
  <div class="login-page">
    <n-card title="SparkitTestPlatform" style="width: 400px">
      <n-form ref="formRef" :model="form" :rules="rules" @submit.prevent="onSubmit">
        <n-form-item path="email" label="邮箱">
          <n-input v-model:value="form.email" placeholder="admin@example.com" />
        </n-form-item>
        <n-form-item path="password" label="密码">
          <n-input v-model:value="form.password" type="password" show-password-on="click" />
        </n-form-item>
        <n-button type="primary" block :loading="loading" attr-type="submit">登录</n-button>
        <n-text depth="3" style="display: block; margin-top: 12px; font-size: 12px">
          
        </n-text>
      </n-form>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import {
  useMessage,
  NButton,
  NCard,
  NForm,
  NFormItem,
  NInput,
  NText,
  type FormInst,
  type FormRules,
} from 'naive-ui';
import { useAuthStore } from '@/stores/auth';
import { apiErrorMessage } from '@/utils/apiError';

const router = useRouter();
const route = useRoute();
const message = useMessage();
const auth = useAuthStore();

const formRef = ref<FormInst | null>(null);
const loading = ref(false);
const form = ref({ email: '', password: '' });
const rules: FormRules = {
  email: [
    { required: true, message: '请输入邮箱' },
    { type: 'email', message: '邮箱格式不正确', trigger: ['input', 'blur'] },
  ],
  password: [
    { required: true, message: '请输入密码' },
    { min: 6, message: '密码至少 6 位', trigger: ['input', 'blur'] },
  ],
};

async function onSubmit() {
  await formRef.value?.validate();
  loading.value = true;
  try {
    await auth.login(form.value.email, form.value.password);
    const redirect = (route.query.redirect as string) || '/';
    await router.replace(redirect);
  } catch (e: unknown) {
    message.error(apiErrorMessage(e, '登录失败'));
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
</style>
