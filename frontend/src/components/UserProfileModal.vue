<template>
  <n-modal
    v-model:show="visible"
    preset="dialog"
    title="我的资料"
    positive-text="保存"
    @update:show="(v) => emit('update:show', v)"
    @positive-click="onSave"
  >
    <n-form label-placement="top">
      <n-form-item label="姓名">
        <n-input :value="auth.user?.name" disabled />
      </n-form-item>
      <n-form-item label="企微绑定手机号（用于群 @ 提醒）">
        <n-input v-model:value="form.wecom_mobile" placeholder="与企微账号一致的手机号" clearable />
      </n-form-item>
      <n-form-item label="企微 userid（可选，有则优先 @）">
        <n-input v-model:value="form.wecom_userid" placeholder="企业微信成员账号" clearable />
      </n-form-item>
      <n-alert type="info" :bordered="false">
        群机器人无法通过显示姓名 @ 人，需填写手机号或 userid。未填写时仍会出现在消息正文，但不会收到 @ 提醒。
      </n-alert>
    </n-form>
  </n-modal>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { NAlert, NForm, NFormItem, NInput, NModal, useMessage } from 'naive-ui';
import { updateMyProfile } from '@/api/users';
import { useAuthStore } from '@/stores/auth';

const props = defineProps<{ show: boolean }>();
const emit = defineEmits<{ 'update:show': [value: boolean] }>();

const auth = useAuthStore();
const message = useMessage();
const visible = ref(props.show);
const form = ref({ wecom_mobile: '', wecom_userid: '' });

watch(
  () => props.show,
  (v) => {
    visible.value = v;
    if (v) {
      form.value = {
        wecom_mobile: auth.user?.wecom_mobile ?? '',
        wecom_userid: auth.user?.wecom_userid ?? '',
      };
    }
  }
);

watch(visible, (v) => emit('update:show', v));

async function onSave() {
  try {
    const { data } = await updateMyProfile({
      wecom_mobile: form.value.wecom_mobile.trim() || null,
      wecom_userid: form.value.wecom_userid.trim() || null,
    });
    if (auth.user) {
      auth.user = { ...auth.user, ...data };
    }
    if (auth.me) {
      auth.me = { ...auth.me, user: data };
    }
    message.success('已保存');
    visible.value = false;
    return true;
  } catch (e: unknown) {
    const detail =
      e && typeof e === 'object' && 'response' in e
        ? (e as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : undefined;
    message.error(typeof detail === 'string' ? detail : '保存失败');
    return false;
  }
}
</script>
