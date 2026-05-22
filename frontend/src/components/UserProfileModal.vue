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
      <n-form-item label="企微绑定手机号">
        <n-input
          v-model:value="form.wecom_mobile"
          placeholder="与企微账号一致的手机号，用于群消息 @ 提醒"
          clearable
        />
      </n-form-item>
      <n-alert type="info" :bordered="false">
        填写与企微一致的手机号后，缺陷通知会 @ 你并推送提醒。未填写时仍会发群消息，但不会 @ 到你。
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
const form = ref({ wecom_mobile: '' });

watch(
  () => props.show,
  (v) => {
    visible.value = v;
    if (v) {
      form.value = {
        wecom_mobile: auth.user?.wecom_mobile ?? '',
      };
    }
  }
);

watch(visible, (v) => emit('update:show', v));

async function onSave() {
  try {
    const { data } = await updateMyProfile({
      wecom_mobile: form.value.wecom_mobile.trim() || null,
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
