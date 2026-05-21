<template>
  <n-card title="项目设置">
    <n-form inline label-placement="left" style="margin-bottom: 12px">
      <n-form-item label="项目">
        <n-select
          v-model:value="selectedProjectId"
          :options="projectOptions"
          placeholder="选择项目"
          style="width: 240px"
          @update:value="onProjectChange"
        />
      </n-form-item>
    </n-form>
    <n-alert v-if="!selectedProjectId" type="info">请选择项目</n-alert>
    <template v-else>
      <n-alert
        v-if="selectedProjectId && ctx.projectId && selectedProjectId !== ctx.projectId"
        type="warning"
        style="margin-bottom: 12px"
      >
        顶栏当前项目与下方选择不一致。切换下方项目或保存模板后，顶栏会同步为所选项目；用例/缺陷编辑以顶栏项目为准。
      </n-alert>
    </template>
    <n-tabs v-if="selectedProjectId" v-model:value="tab" type="line">
      <n-tab-pane name="case" tab="用例字段">
        <div class="template-editor-layout">
          <TemplateFieldPanel
            class="template-editor-config"
            scene="case"
            :fields="caseFields"
            :saving="saving"
            @update:fields="caseFields = $event"
            @add="openFieldEdit('case', null)"
            @edit="(i) => openFieldEdit('case', i)"
            @save="saveTemplate('functional_case', caseFields)"
          />
          <TemplateEditPreview
            class="template-editor-preview"
            scene="case"
            :fields="caseFields"
            :project-id="selectedProjectId"
          />
        </div>
      </n-tab-pane>
      <n-tab-pane name="bug" tab="缺陷字段">
        <div class="template-editor-layout">
          <TemplateFieldPanel
            class="template-editor-config"
            scene="bug"
            :fields="bugFields"
            :saving="saving"
            @update:fields="bugFields = $event"
            @add="openFieldEdit('bug', null)"
            @edit="(i) => openFieldEdit('bug', i)"
            @save="saveTemplate('bug', bugFields)"
          />
          <TemplateEditPreview
            class="template-editor-preview"
            scene="bug"
            :fields="bugFields"
            :project-id="selectedProjectId"
            :bug-statuses="statuses"
          />
        </div>
      </n-tab-pane>
      <n-tab-pane name="status" tab="缺陷状态">
        <n-data-table :columns="statusColumns" :data="statuses" size="small" />
        <n-button size="small" style="margin-top: 8px" @click="openStatusModal()">添加状态</n-button>
      </n-tab-pane>
      <n-tab-pane name="wecom" tab="企微通知">
        <n-form label-placement="top" style="max-width: 960px">
          <n-divider title-placement="left">基础配置</n-divider>
          <n-form-item label="启用"><n-switch v-model:value="wecom.wecom_enabled" /></n-form-item>
          <n-form-item label="Webhook URL">
            <n-input v-model:value="wecom.wecom_webhook_url" type="textarea" :rows="2" />
          </n-form-item>
          <n-space>
            <n-button type="primary" @click="saveWecom">保存 Webhook</n-button>
            <n-button @click="onTestWecom">发送测试</n-button>
          </n-space>

          <n-divider title-placement="left">新建缺陷通知</n-divider>
          <n-form-item label="启用">
            <n-switch v-model:value="createRule.enabled" />
          </n-form-item>
          <n-form-item label="通知对象">
            <n-select
              v-model:value="createRule.notify_roles"
              :options="notifyRoleOptions"
              multiple
              style="max-width: 480px"
            />
          </n-form-item>
          <n-form-item label="消息模板">
            <n-input v-model:value="createRule.message_template" type="textarea" :rows="5" />
          </n-form-item>
          <n-button type="primary" @click="saveCreateRule">保存新建规则</n-button>

          <n-divider title-placement="left">状态流转通知</n-divider>
          <n-alert type="info" :bordered="false" style="margin-bottom: 12px">
            仅当配置了精确的「原状态 → 目标状态」规则且启用时才会发送企微；未配置的流转不会通知。
            占位符：{project} {num} {title} {from_status} {to_status} {reporter} {followers} {link}。
            @ 提醒需成员在「我的资料」填写企微绑定手机号或 userid。
          </n-alert>
          <n-data-table :columns="transitionRuleColumns" :data="transitionRules" size="small" />
          <n-button size="small" style="margin-top: 8px" @click="openTransitionModal()">添加流转规则</n-button>
        </n-form>
      </n-tab-pane>
    </n-tabs>

    <n-drawer v-model:show="showFieldDrawer" :width="720" placement="right">
      <n-drawer-content :title="fieldEditIndex === null ? '添加字段' : '编辑字段'">
        <n-grid :cols="2" :x-gap="16">
          <n-grid-item>
        <n-form label-placement="top">
          <n-form-item label="显示名称">
            <n-input v-model:value="fieldForm.name" placeholder="请输入显示名称" clearable />
          </n-form-item>
          <n-form-item label="类型">
            <n-select
              v-model:value="fieldForm.type"
              :options="FIELD_TYPE_OPTIONS"
              placeholder="请选择字段类型"
            />
          </n-form-item>
          <n-form-item label="必填"><n-switch v-model:value="fieldForm.required" /></n-form-item>
          <n-form-item v-if="isOptionFieldType(fieldForm.type)" label="选项（每行一个）">
            <n-input
              v-model:value="optionsText"
              type="textarea"
              :rows="4"
              :placeholder="selectOptionsPlaceholder"
            />
          </n-form-item>
        </n-form>
          </n-grid-item>
          <n-grid-item>
            <TemplateEditPreview
              :scene="fieldEditKind"
              :fields="draftPreviewFields"
              :project-id="selectedProjectId"
              :bug-statuses="statuses"
            />
          </n-grid-item>
        </n-grid>
        <template #footer>
          <n-button type="primary" @click="confirmFieldEdit">确定</n-button>
        </template>
      </n-drawer-content>
    </n-drawer>

    <n-modal
      v-model:show="showStatusModal"
      preset="dialog"
      :title="editingStatus ? '编辑状态' : '添加状态'"
      positive-text="保存"
      @positive-click="onSaveStatus"
    >
      <n-form label-width="100">
        <n-form-item label="状态标识">
          <n-input
            v-model:value="statusForm.key"
            :disabled="!!editingStatus"
            placeholder="英文标识，如 in_progress"
          />
        </n-form-item>
        <n-form-item label="名称">
          <n-input v-model:value="statusForm.label" placeholder="请输入状态名称" />
        </n-form-item>
        <n-form-item label="终态"><n-switch v-model:value="statusForm.is_terminal" /></n-form-item>
      </n-form>
    </n-modal>

    <n-modal
      v-model:show="showTransitionModal"
      preset="dialog"
      :title="editingTransitionRule ? '编辑流转规则' : '添加流转规则'"
      positive-text="保存"
      @positive-click="onSaveTransitionRule"
    >
      <n-form label-width="100">
        <n-form-item label="原状态">
          <n-select
            v-model:value="transitionForm.from_status_key"
            :options="statusKeyOptions"
            placeholder="选择原状态"
          />
        </n-form-item>
        <n-form-item label="目标状态">
          <n-select
            v-model:value="transitionForm.to_status_key"
            :options="statusKeyOptions"
            placeholder="选择目标状态"
          />
        </n-form-item>
        <n-form-item label="启用"><n-switch v-model:value="transitionForm.enabled" /></n-form-item>
        <n-form-item label="通知对象">
          <n-select
            v-model:value="transitionForm.notify_roles"
            :options="notifyRoleOptions"
            multiple
            style="width: 100%"
          />
        </n-form-item>
        <n-form-item label="消息模板">
          <n-input v-model:value="transitionForm.message_template" type="textarea" :rows="5" />
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
  NDivider,
  NDrawer,
  NDrawerContent,
  NForm,
  NFormItem,
  NGrid,
  NGridItem,
  NInput,
  NModal,
  NSelect,
  NSpace,
  NSwitch,
  NTabPane,
  NTabs,
  NTag,
  useDialog,
  useMessage,
  type DataTableColumns,
} from 'naive-ui';
import { switchContext } from '@/api/auth';
import {
  createBugStatus,
  deleteBugStatus,
  getTemplate,
  getWecom,
  listBugStatuses,
  testWecom,
  updateBugStatus,
  updateTemplate,
  updateWecom,
} from '@/api/templates';
import {
  createWecomNotifyRule,
  deleteWecomNotifyRule,
  listWecomNotifyRules,
  updateWecomNotifyRule,
  upsertCreateWecomRule,
} from '@/api/wecomRules';
import TemplateEditPreview from '@/components/TemplateEditPreview.vue';
import TemplateFieldPanel from '@/components/TemplateFieldPanel.vue';
import {
  FIELD_TYPE_OPTIONS,
  generateFieldId,
  isOptionFieldType,
  normalizeFieldSort,
  type FieldTypeValue,
} from '@/constants/fieldTypes';
import { useSettingScope } from '@/composables/useSettingScope';
import { invalidateProjectFieldSchemaCache } from '@/composables/useProjectFieldSchema';
import { validateTemplateFieldNames } from '@/schemas/entityFieldSchema';
import { useAuthStore } from '@/stores/auth';
import { useContextStore } from '@/stores/context';
import type { BugStatusDef, TemplateField, WecomNotifyRule } from '@/types/business';

const DEFAULT_CREATE_TEMPLATE =
  '【新建缺陷 {num}】{title}\n项目：{project}\n提出人：{reporter}\n跟进人：{followers}\n{link}';

const DEFAULT_TRANSITION_TEMPLATE =
  '【缺陷 {num}】{title}\n项目：{project}\n提出人：{reporter}\n跟进人：{followers}\n状态：{from_status} → {to_status}\n{link}';

const auth = useAuthStore();
const ctx = useContextStore();
const message = useMessage();
const dialog = useDialog();

const selectedProjectId = ref<string | null>(null);
const { restoreProject } = useSettingScope(selectedProjectId);

const tab = ref('case');
const saving = ref(false);
const caseFields = ref<TemplateField[]>([]);
const bugFields = ref<TemplateField[]>([]);
const statuses = ref<BugStatusDef[]>([]);
const wecom = ref({
  wecom_enabled: false,
  wecom_webhook_url: '' as string | null,
});

const createRule = ref({
  message_template: DEFAULT_CREATE_TEMPLATE,
  notify_roles: ['reporter', 'followers'] as string[],
  enabled: true,
});

const wecomRules = ref<WecomNotifyRule[]>([]);
const showTransitionModal = ref(false);
const editingTransitionRule = ref<WecomNotifyRule | null>(null);
const transitionForm = ref({
  from_status_key: '',
  to_status_key: '',
  message_template: DEFAULT_TRANSITION_TEMPLATE,
  notify_roles: ['reporter', 'followers'] as string[],
  enabled: true,
});

const notifyRoleOptions = [
  { label: '提出人', value: 'reporter' },
  { label: '跟进人', value: 'followers' },
  { label: '处理人', value: 'assignee' },
];

const showFieldDrawer = ref(false);
const fieldEditKind = ref<'case' | 'bug'>('case');
const fieldEditIndex = ref<number | null>(null);
const fieldForm = ref<TemplateField>({
  id: '',
  name: '',
  type: 'text',
  required: false,
  options: [],
  sort: 0,
});
const optionsText = ref('');
const selectOptionsPlaceholder = '每行一个选项，例如：致命、严重、一般';

const showStatusModal = ref(false);
const editingStatus = ref<BugStatusDef | null>(null);
const statusForm = ref({
  key: '',
  label: '',
  is_terminal: false,
});

const projectOptions = computed(() =>
  (auth.me?.projects ?? []).map((p) => ({ label: p.name, value: p.id }))
);

const statusKeyOptions = computed(() =>
  statuses.value.map((s) => ({ label: s.label, value: s.key }))
);

const transitionRules = computed(() =>
  wecomRules.value.filter((r) => r.kind === 'transition')
);

/** 字段编辑抽屉内：将当前表单草稿合并进列表，供右侧实时预览 */
const draftPreviewFields = computed<TemplateField[]>(() => {
  const base = fieldEditKind.value === 'case' ? [...caseFields.value] : [...bugFields.value];
  const options = isOptionFieldType(fieldForm.value.type)
    ? optionsText.value
        .split('\n')
        .map((s) => s.trim())
        .filter(Boolean)
    : fieldForm.value.options ?? [];
  const draftId =
    fieldEditIndex.value !== null ? fieldForm.value.id : fieldForm.value.id || '__draft_preview__';
  const draft: TemplateField = {
    ...fieldForm.value,
    id: draftId,
    name: fieldForm.value.name.trim() || '（未命名）',
    options,
  };
  if (fieldEditIndex.value === null) {
    const idx = base.findIndex((f) => f.id === draftId);
    if (idx >= 0) base[idx] = draft;
    else base.push(draft);
  } else {
    base[fieldEditIndex.value] = draft;
  }
  return normalizeFieldSort(base);
});

const statusColumns: DataTableColumns<BugStatusDef> = [
  { title: '标识', key: 'key', width: 120 },
  { title: '名称', key: 'label' },
  {
    title: '终态',
    key: 'is_terminal',
    width: 70,
    render: (r) => (r.is_terminal ? '是' : '否'),
  },
  {
    title: '操作',
    key: 'actions',
    width: 200,
    render: (row, index) =>
      h(NSpace, { size: 4 }, () => [
        h(NButton, { size: 'tiny', quaternary: true, disabled: index === 0, onClick: () => moveStatus(index, -1) }, () => '上移'),
        h(
          NButton,
          { size: 'tiny', quaternary: true, disabled: index === statuses.value.length - 1, onClick: () => moveStatus(index, 1) },
          () => '下移'
        ),
        h(NButton, { size: 'tiny', quaternary: true, type: 'primary', onClick: () => openStatusModal(row) }, () => '编辑'),
        h(NButton, { size: 'tiny', quaternary: true, type: 'error', onClick: () => removeStatus(row) }, () => '删除'),
      ]),
  },
];

const transitionRuleColumns: DataTableColumns<WecomNotifyRule> = [
  {
    title: '原状态',
    key: 'from_status_key',
    width: 120,
    render: (r) => r.from_status_label ?? r.from_status_key ?? '-',
  },
  {
    title: '目标状态',
    key: 'to_status_key',
    width: 120,
    render: (r) => r.to_status_label ?? r.to_status_key ?? '-',
  },
  {
    title: '启用',
    key: 'enabled',
    width: 70,
    render: (r) => h(NTag, { type: r.enabled ? 'success' : 'default', size: 'small' }, () => (r.enabled ? '是' : '否')),
  },
  {
    title: '操作',
    key: 'actions',
    width: 140,
    render: (row) =>
      h(NSpace, { size: 4 }, () => [
        h(NButton, { size: 'tiny', quaternary: true, type: 'primary', onClick: () => openTransitionModal(row) }, () => '编辑'),
        h(NButton, { size: 'tiny', quaternary: true, type: 'error', onClick: () => removeTransitionRule(row) }, () => '删除'),
      ]),
  },
];

function openFieldEdit(kind: 'case' | 'bug', index: number | null) {
  fieldEditKind.value = kind;
  fieldEditIndex.value = index;
  const list = kind === 'case' ? caseFields.value : bugFields.value;
  if (index === null) {
    fieldForm.value = {
      id: generateFieldId(),
      name: '',
      type: 'text',
      required: false,
      options: [],
      sort: list.length,
    };
    optionsText.value = '';
  } else {
    const row = list[index];
    fieldForm.value = { ...row, options: [...(row.options ?? [])] };
    optionsText.value = (row.options ?? []).join('\n');
  }
  showFieldDrawer.value = true;
}

function confirmFieldEdit() {
  const name = fieldForm.value.name.trim();
  if (!name) {
    message.warning('请填写显示名称');
    return;
  }
  const id = fieldEditIndex.value === null ? generateFieldId() : fieldForm.value.id;
  const options = isOptionFieldType(fieldForm.value.type)
    ? optionsText.value
        .split('\n')
        .map((s) => s.trim())
        .filter(Boolean)
    : [];
  if (isOptionFieldType(fieldForm.value.type) && !options.length) {
    message.warning('单选/多选字段至少需要一个选项');
    return;
  }
  const row: TemplateField = {
    ...fieldForm.value,
    id,
    name,
    type: fieldForm.value.type as FieldTypeValue,
    options,
  };
  const list = fieldEditKind.value === 'case' ? [...caseFields.value] : [...bugFields.value];
  if (fieldEditIndex.value === null) {
    list.push(row);
  } else {
    list[fieldEditIndex.value] = row;
  }
  const normalized = normalizeFieldSort(list);
  if (fieldEditKind.value === 'case') caseFields.value = normalized;
  else bugFields.value = normalized;
  showFieldDrawer.value = false;
}

function openStatusModal(row?: BugStatusDef) {
  editingStatus.value = row ?? null;
  statusForm.value = row
    ? {
        key: row.key,
        label: row.label,
        is_terminal: row.is_terminal,
      }
    : {
        key: '',
        label: '',
        is_terminal: false,
      };
  showStatusModal.value = true;
}

function applyWecomRules(rules: WecomNotifyRule[]) {
  wecomRules.value = rules;
  const create = rules.find((r) => r.kind === 'create');
  createRule.value = {
    message_template: create?.message_template ?? DEFAULT_CREATE_TEMPLATE,
    notify_roles: [...(create?.notify_roles ?? ['reporter', 'followers'])],
    enabled: create?.enabled ?? true,
  };
}

function openTransitionModal(row?: WecomNotifyRule) {
  editingTransitionRule.value = row ?? null;
  transitionForm.value = row
    ? {
        from_status_key: row.from_status_key ?? '',
        to_status_key: row.to_status_key ?? '',
        message_template: row.message_template,
        notify_roles: [...(row.notify_roles ?? ['reporter', 'followers'])],
        enabled: row.enabled,
      }
    : {
        from_status_key: '',
        to_status_key: '',
        message_template: DEFAULT_TRANSITION_TEMPLATE,
        notify_roles: ['reporter', 'followers'],
        enabled: true,
      };
  showTransitionModal.value = true;
}

function removeTransitionRule(row: WecomNotifyRule) {
  dialog.warning({
    title: '确认删除',
    content: `删除流转规则「${row.from_status_label ?? row.from_status_key} → ${row.to_status_label ?? row.to_status_key}」？`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      const projectId = await syncContext();
      if (!projectId) return;
      try {
        await deleteWecomNotifyRule(projectId, row.id);
        message.success('已删除');
        await loadWecomRules(projectId);
      } catch {
        message.error('删除失败');
      }
    },
  });
}

async function onSaveTransitionRule() {
  const projectId = await syncContext();
  if (!projectId) return false;
  const f = transitionForm.value;
  if (!f.from_status_key || !f.to_status_key) {
    message.warning('请选择原状态和目标状态');
    return false;
  }
  if (f.from_status_key === f.to_status_key) {
    message.warning('原状态与目标状态不能相同');
    return false;
  }
  if (!f.message_template.trim()) {
    message.warning('请填写消息模板');
    return false;
  }
  try {
    if (editingTransitionRule.value) {
      await updateWecomNotifyRule(projectId, editingTransitionRule.value.id, {
        from_status_key: f.from_status_key,
        to_status_key: f.to_status_key,
        message_template: f.message_template.trim(),
        notify_roles: f.notify_roles,
        enabled: f.enabled,
      });
    } else {
      await createWecomNotifyRule(projectId, {
        kind: 'transition',
        from_status_key: f.from_status_key,
        to_status_key: f.to_status_key,
        message_template: f.message_template.trim(),
        notify_roles: f.notify_roles,
        enabled: f.enabled,
      });
    }
    showTransitionModal.value = false;
    message.success('已保存');
    await loadWecomRules(projectId);
    return true;
  } catch {
    message.error('保存失败');
    return false;
  }
}

async function loadWecomRules(projectId: string) {
  const { data } = await listWecomNotifyRules(projectId);
  applyWecomRules(data);
}

async function moveStatus(index: number, delta: number) {
  const projectId = await syncContext();
  if (!projectId) return;
  const j = index + delta;
  if (j < 0 || j >= statuses.value.length) return;
  const list = [...statuses.value];
  [list[index], list[j]] = [list[j], list[index]];
  await Promise.all(list.map((s, i) => updateBugStatus(projectId, s.id, { sort: i })));
  await load();
}

function removeStatus(row: BugStatusDef) {
  dialog.warning({
    title: '确认删除',
    content: `删除状态「${row.label}」？已有缺陷若使用该状态需手动调整。`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      const projectId = await syncContext();
      if (!projectId) return;
      try {
        await deleteBugStatus(projectId, row.id);
        message.success('已删除');
        await load();
      } catch {
        message.error('删除失败');
      }
    },
  });
}

async function onSaveStatus() {
  const projectId = await syncContext();
  if (!projectId) return false;
  if (!statusForm.value.key.trim() || !statusForm.value.label.trim()) {
    message.warning('请填写状态标识和名称');
    return false;
  }
  try {
    if (editingStatus.value) {
      await updateBugStatus(projectId, editingStatus.value.id, {
        label: statusForm.value.label,
        is_terminal: statusForm.value.is_terminal,
      });
    } else {
      await createBugStatus(projectId, {
        ...statusForm.value,
        sort: statuses.value.length,
      });
    }
    showStatusModal.value = false;
    message.success('已保存');
    await load();
    return true;
  } catch {
    message.error('保存失败');
    return false;
  }
}

async function syncContext(): Promise<string | null> {
  if (!selectedProjectId.value) return null;
  const { data } = await switchContext(selectedProjectId.value);
  ctx.applyFromMe(data);
  auth.user = data.user;
  auth.me = data;
  return selectedProjectId.value;
}

async function onProjectChange() {
  await load();
}

async function load() {
  if (!selectedProjectId.value) {
    caseFields.value = [];
    bugFields.value = [];
    statuses.value = [];
    wecom.value = { wecom_enabled: false, wecom_webhook_url: null };
    wecomRules.value = [];
    createRule.value = {
      message_template: DEFAULT_CREATE_TEMPLATE,
      notify_roles: ['reporter', 'followers'],
      enabled: true,
    };
    return;
  }
  try {
    const projectId = await syncContext();
    if (!projectId) return;
    const [c, b, s, w, rules] = await Promise.all([
      getTemplate(projectId, 'functional_case'),
      getTemplate(projectId, 'bug'),
      listBugStatuses(projectId),
      getWecom(projectId),
      listWecomNotifyRules(projectId),
    ]);
    caseFields.value = c.data.fields as TemplateField[];
    bugFields.value = b.data.fields as TemplateField[];
    statuses.value = s.data.sort((a, b) => a.sort - b.sort);
    wecom.value = {
      wecom_enabled: w.data.wecom_enabled,
      wecom_webhook_url: w.data.wecom_webhook_url,
    };
    applyWecomRules(rules.data);
  } catch {
    message.error('加载项目设置失败，请确认是否选择了正确的项目且有权限');
  }
}

async function saveTemplate(scene: 'functional_case' | 'bug', fields: TemplateField[]) {
  const projectId = await syncContext();
  if (!projectId) return;
  const nameErr = validateTemplateFieldNames(scene, fields);
  if (nameErr) {
    message.warning(nameErr);
    return;
  }
  saving.value = true;
  try {
    await updateTemplate(projectId, scene, normalizeFieldSort(fields));
    invalidateProjectFieldSchemaCache(projectId, scene);
    message.success('已保存');
    await load();
  } catch {
    message.error('保存失败');
  } finally {
    saving.value = false;
  }
}

async function saveWecom() {
  const projectId = await syncContext();
  if (!projectId) return;
  try {
    await updateWecom(projectId, wecom.value);
    message.success('已保存 Webhook 配置');
  } catch {
    message.error('保存失败');
  }
}

async function saveCreateRule() {
  const projectId = await syncContext();
  if (!projectId) return;
  if (!createRule.value.message_template.trim()) {
    message.warning('请填写新建缺陷消息模板');
    return;
  }
  try {
    await upsertCreateWecomRule(projectId, {
      message_template: createRule.value.message_template.trim(),
      notify_roles: createRule.value.notify_roles,
      enabled: createRule.value.enabled,
    });
    message.success('已保存新建规则');
    await loadWecomRules(projectId);
  } catch {
    message.error('保存失败');
  }
}

async function onTestWecom() {
  const projectId = await syncContext();
  if (!projectId) return;
  try {
    await testWecom(projectId);
    message.success('测试消息已发送');
  } catch {
    message.error('发送失败');
  }
}

async function init() {
  const validProjectIds = projectOptions.value.map((o) => o.value as string);
  restoreProject(validProjectIds, ctx.projectId ?? validProjectIds[0] ?? null);
  await load();
}

onMounted(init);
</script>

<style scoped>
.template-editor-layout {
  display: grid;
  grid-template-columns: 1fr 400px;
  gap: 20px;
  align-items: start;
}

@media (max-width: 1100px) {
  .template-editor-layout {
    grid-template-columns: 1fr;
  }

  .template-editor-preview {
    order: -1;
  }
}
</style>
