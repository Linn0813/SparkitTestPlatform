<template>
  <n-form label-placement="top" style="max-width: 960px">
    <n-divider title-placement="left">版本企微</n-divider>
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
      触发节点来自「版本工作流」配置；节点完成后发送企微通知。占位符：{version} {project} {node}
      {operator} {link}。不需要的通知可删除或关闭启用。@ 对象须绑定企微手机号。
    </n-alert>
    <n-data-table :columns="ruleColumns" :data="rules" :loading="loadingRules" size="small" />
    <n-button
      v-if="!readOnly && availableNodeOptions.length"
      size="small"
      style="margin-top: 8px"
      @click="openRuleModal()"
    >
      添加规则
    </n-button>

    <n-modal
      v-model:show="showRuleModal"
      preset="dialog"
      :title="editingRule ? '编辑通知规则' : '添加通知规则'"
      positive-text="保存"
      @positive-click="onSaveRule"
    >
      <n-form label-placement="top">
        <n-form-item label="工作流节点">
          <n-text v-if="editingRule">{{ editingRule.node_label }}</n-text>
          <n-select
            v-else
            v-model:value="ruleForm.node_key"
            :options="availableNodeOptions"
            placeholder="选择工作流节点"
            @update:value="onNodeKeyChange"
          />
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
  useDialog,
  useMessage,
  type DataTableColumns,
} from 'naive-ui';
import { listProjectMembers } from '@/api/projects';
import {
  createVersionWecomRule,
  deleteVersionWecomRule,
  getVersionWecom,
  listVersionWecomRuleOptions,
  listVersionWecomRules,
  patchVersionWecomRule,
  testVersionWecom,
  updateVersionWecom,
} from '@/api/versionWecom';
import { apiErrorMessage } from '@/utils/apiError';
import type { VersionWecomNotifyRule, VersionWecomNotifyRuleOption } from '@/types/business';

const props = defineProps<{
  projectId: string;
  readOnly?: boolean;
}>();

const message = useMessage();
const dialog = useDialog();
const wecom = ref({
  version_wecom_enabled: false,
  version_wecom_webhook_url: '' as string | null,
  app_public_url: '' as string | null,
});
const rules = ref<VersionWecomNotifyRule[]>([]);
const ruleOptions = ref<VersionWecomNotifyRuleOption[]>([]);
const loadingRules = ref(false);
const memberOptions = ref<{ label: string; value: string }[]>([]);
const showRuleModal = ref(false);
const editingRule = ref<VersionWecomNotifyRule | null>(null);
const ruleForm = ref({
  node_key: null as string | null,
  message_template: '',
  notify_user_ids: [] as string[],
  enabled: true,
});

const availableNodeOptions = computed(() =>
  ruleOptions.value
    .filter((o) => !o.configured)
    .map((o) => ({ label: o.node_label, value: o.node_key }))
);

const ruleColumns = computed<DataTableColumns<VersionWecomNotifyRule>>(() => {
  const cols: DataTableColumns<VersionWecomNotifyRule> = [
    { title: '工作流节点', key: 'node_label', width: 140 },
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
  ];
  if (!props.readOnly) {
    cols.push({
      title: '操作',
      key: 'actions',
      width: 140,
      render: (row) =>
        h(NSpace, { size: 4 }, () => [
          h(
            NButton,
            { size: 'tiny', quaternary: true, type: 'primary', onClick: () => openRuleModal(row) },
            () => '编辑'
          ),
          h(
            NButton,
            { size: 'tiny', quaternary: true, type: 'error', onClick: () => removeRule(row) },
            () => '删除'
          ),
        ]),
    });
  }
  return cols;
});

function defaultTemplateForNode(nodeKey: string): string {
  return ruleOptions.value.find((o) => o.node_key === nodeKey)?.default_message_template ?? '';
}

function onNodeKeyChange(nodeKey: string | null) {
  if (!nodeKey || editingRule.value) return;
  if (!ruleForm.value.message_template.trim()) {
    ruleForm.value.message_template = defaultTemplateForNode(nodeKey);
  }
}

function openRuleModal(row?: VersionWecomNotifyRule) {
  editingRule.value = row ?? null;
  if (row) {
    ruleForm.value = {
      node_key: row.node_key,
      message_template: row.message_template,
      notify_user_ids: [...(row.notify_user_ids ?? [])],
      enabled: row.enabled,
    };
  } else {
    const first = availableNodeOptions.value[0]?.value ?? null;
    ruleForm.value = {
      node_key: first,
      message_template: first ? defaultTemplateForNode(first) : '',
      notify_user_ids: [],
      enabled: true,
    };
  }
  showRuleModal.value = true;
}

function removeRule(row: VersionWecomNotifyRule) {
  dialog.warning({
    title: '删除通知规则',
    content: `确定删除「${row.node_label}」的通知规则？删除后该节点完成时将不再发送企微消息。`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await deleteVersionWecomRule(props.projectId, row.id);
        message.success('规则已删除');
        await Promise.all([loadRules(), loadRuleOptions()]);
      } catch (e: unknown) {
        message.error(apiErrorMessage(e, '删除失败'));
      }
    },
  });
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

async function loadRuleOptions() {
  const { data } = await listVersionWecomRuleOptions(props.projectId);
  ruleOptions.value = data;
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
  const template = ruleForm.value.message_template.trim();
  if (!template) {
    message.warning('请填写消息模板');
    return false;
  }
  try {
    if (editingRule.value) {
      await patchVersionWecomRule(props.projectId, editingRule.value.id, {
        message_template: template,
        notify_user_ids: ruleForm.value.notify_user_ids,
        enabled: ruleForm.value.enabled,
      });
    } else {
      if (!ruleForm.value.node_key) {
        message.warning('请选择工作流节点');
        return false;
      }
      await createVersionWecomRule(props.projectId, {
        node_key: ruleForm.value.node_key,
        message_template: template,
        notify_user_ids: ruleForm.value.notify_user_ids,
        enabled: ruleForm.value.enabled,
      });
    }
    message.success('规则已保存');
    showRuleModal.value = false;
    await Promise.all([loadRules(), loadRuleOptions()]);
    return true;
  } catch (e: unknown) {
    message.error(apiErrorMessage(e, '保存失败'));
    return false;
  }
}

async function load() {
  if (!props.projectId) return;
  await Promise.all([loadIntegration(), loadRules(), loadRuleOptions(), loadMembers()]);
}

onMounted(load);
watch(() => props.projectId, load);
</script>
