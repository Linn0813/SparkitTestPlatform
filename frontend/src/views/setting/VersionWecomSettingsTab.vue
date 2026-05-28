<template>
  <n-form label-placement="top" style="max-width: 960px">
    <n-divider title-placement="left">版本企微（独立于缺陷通知）</n-divider>
    <n-form-item label="启用">
      <n-switch v-model:value="wecom.version_wecom_enabled" :disabled="readOnly" />
    </n-form-item>
    <n-form-item label="Webhook URL">
      <n-input
        v-model:value="wecom.version_wecom_webhook_url"
        type="textarea"
        :rows="2"
        placeholder="版本发版节点完成通知专用机器人地址"
        :disabled="readOnly"
      />
    </n-form-item>
    <n-form-item label="站点访问地址">
      <n-input
        v-model:value="wecom.app_public_url"
        placeholder="企微消息 {link} 用，勿填 localhost"
        clearable
        :disabled="readOnly"
      />
    </n-form-item>
    <n-space v-if="!readOnly">
      <n-button type="primary" @click="saveIntegration">保存配置</n-button>
      <n-button @click="onTest">发送测试</n-button>
    </n-space>

    <n-divider title-placement="left">节点完成通知规则</n-divider>
    <n-alert type="info" :bordered="false" style="margin-bottom: 12px">
      版本开发、发版验证、GP/AS/官网提审节点完成后发送。占位符：{version} {project} {node}
      {operator} {link}。@ 对象需在下方为每条规则选择项目成员（须绑定企微手机号）。
    </n-alert>
    <n-data-table :columns="ruleColumns" :data="rules" :loading="loadingRules" size="small" />

    <n-modal v-model:show="showRuleModal" preset="dialog" title="编辑通知规则" positive-text="保存" @positive-click="onSaveRule">
      <n-form label-placement="top" v-if="editingRule">
        <n-form-item label="事件">
          <n-text>{{ editingRule.event_label }}</n-text>
        </n-form-item>
        <n-form-item label="启用">
          <n-switch v-model:value="ruleForm.enabled" />
        </n-form-item>
        <n-form-item label="消息模板">
          <n-input v-model:value="ruleForm.message_template" type="textarea" :rows="5" />
        </n-form-item>
        <n-form-item label="@ 用户">
          <n-select
            v-model:value="ruleForm.notify_user_ids"
            :options="memberOptions"
            multiple
            filterable
            placeholder="选择要 @ 的项目成员"
          />
        </n-form-item>
      </n-form>
    </n-modal>
  </n-form>
</template>

<script setup lang="ts">
import { computed, h, onMounted, ref, watch } from 'vue';
import {
  NAlert,
  NButton,
  NDataTable,
  NDivider,
  NForm,
  NFormItem,
  NInput,
  NModal,
  NSelect,
  NSpace,
  NSwitch,
  NText,
  useMessage,
  type DataTableColumns,
} from 'naive-ui';
import { listProjectMembers } from '@/api/projects';
import {
  getVersionWecom,
  listVersionWecomRules,
  testVersionWecom,
  updateVersionWecom,
  updateVersionWecomRule,
} from '@/api/versionWecom';
import { apiErrorMessage } from '@/utils/apiError';
import type { VersionWecomNotifyRule } from '@/types/business';

const props = defineProps<{
  projectId: string;
  readOnly?: boolean;
}>();

const message = useMessage();
const wecom = ref({
  version_wecom_enabled: false,
  version_wecom_webhook_url: '' as string | null,
  app_public_url: '' as string | null,
});
const rules = ref<VersionWecomNotifyRule[]>([]);
const loadingRules = ref(false);
const memberOptions = ref<{ label: string; value: string }[]>([]);
const showRuleModal = ref(false);
const editingRule = ref<VersionWecomNotifyRule | null>(null);
const ruleForm = ref({
  message_template: '',
  notify_user_ids: [] as string[],
  enabled: true,
});

const ruleColumns = computed<DataTableColumns<VersionWecomNotifyRule>>(() => [
  { title: '事件', key: 'event_label', width: 140 },
  {
    title: '启用',
    key: 'enabled',
    width: 70,
    render: (row) => (row.enabled ? '是' : '否'),
  },
  {
    title: '@ 人数',
    key: 'notify_user_ids',
    width: 80,
    render: (row) => String(row.notify_user_ids?.length ?? 0),
  },
  {
    title: '操作',
    key: 'a',
    width: 80,
    render: (row) =>
      props.readOnly
        ? '—'
        : h(
            NButton,
            { size: 'small', quaternary: true, onClick: () => openRule(row) },
            () => '编辑'
          ),
  },
]);

function openRule(row: VersionWecomNotifyRule) {
  editingRule.value = row;
  ruleForm.value = {
    message_template: row.message_template,
    notify_user_ids: [...(row.notify_user_ids ?? [])],
    enabled: row.enabled,
  };
  showRuleModal.value = true;
}

async function loadIntegration() {
  const { data } = await getVersionWecom(props.projectId);
  wecom.value = {
    version_wecom_enabled: data.version_wecom_enabled,
    version_wecom_webhook_url: data.version_wecom_webhook_url ?? '',
    app_public_url: data.app_public_url ?? '',
  };
}

async function loadRules() {
  loadingRules.value = true;
  try {
    const { data } = await listVersionWecomRules(props.projectId);
    rules.value = data;
  } finally {
    loadingRules.value = false;
  }
}

async function loadMembers() {
  const { data } = await listProjectMembers(props.projectId);
  memberOptions.value = data.map((m) => ({
    label: m.user?.name ?? m.user_id,
    value: m.user_id,
  }));
}

async function saveIntegration() {
  try {
    await updateVersionWecom(props.projectId, {
      version_wecom_enabled: wecom.value.version_wecom_enabled,
      version_wecom_webhook_url: wecom.value.version_wecom_webhook_url?.trim() || null,
      app_public_url: wecom.value.app_public_url?.trim() || null,
    });
    message.success('已保存');
  } catch (e: unknown) {
    message.error(apiErrorMessage(e, '保存失败'));
  }
}

async function onTest() {
  try {
    await testVersionWecom(props.projectId);
    message.success('测试消息已发送');
  } catch (e: unknown) {
    message.error(apiErrorMessage(e, '发送失败'));
  }
}

async function onSaveRule() {
  if (!editingRule.value) return false;
  try {
    await updateVersionWecomRule(props.projectId, editingRule.value.event_key, {
      message_template: ruleForm.value.message_template,
      notify_user_ids: ruleForm.value.notify_user_ids,
      enabled: ruleForm.value.enabled,
    });
    message.success('规则已保存');
    showRuleModal.value = false;
    await loadRules();
    return true;
  } catch (e: unknown) {
    message.error(apiErrorMessage(e, '保存失败'));
    return false;
  }
}

async function load() {
  if (!props.projectId) return;
  await Promise.all([loadIntegration(), loadRules(), loadMembers()]);
}

onMounted(load);
watch(() => props.projectId, load);
</script>
