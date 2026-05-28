<template>
  <n-card
    :bordered="!embedded"
    :title="embedded ? undefined : '项目设置'"
    :content-style="embedded ? 'padding: 0' : undefined"
  >
    <n-alert v-if="!ctx.projectId" type="info" style="margin-bottom: 12px">请先在顶栏选择项目</n-alert>
    <template v-else>
      <n-alert v-if="!canEdit" type="info" :bordered="false" style="margin-bottom: 12px">
        仅项目管理员可修改项目设置，当前为只读浏览。
      </n-alert>
      <n-tabs v-model:value="tab" type="line">
      <n-tab-pane name="case" tab="用例字段">
        <div class="template-editor-layout">
          <TemplateFieldPanel
            class="template-editor-config"
            scene="case"
            :fields="caseFields"
            :saving="saving"
            :read-only="readOnly"
            @update:fields="caseFields = $event"
            @add="openFieldEdit('case', null)"
            @edit="(i) => openFieldEdit('case', i)"
            @save="saveTemplate('functional_case', caseFields)"
          />
          <TemplateEditPreview
            class="template-editor-preview"
            scene="case"
            :fields="caseFields"
            :project-id="ctx.projectId"
          />
        </div>
      </n-tab-pane>
      <n-tab-pane name="bug" tab="缺陷字段">
        <BugFieldSettingsTab
          :project-id="ctx.projectId"
          :bug-fields="bugFields"
          :statuses="statuses"
          :saving="saving"
          :read-only="readOnly"
          @update:bug-fields="bugFields = $event"
          @add-field="openFieldEdit('bug', null)"
          @edit-field="(i) => openFieldEdit('bug', i)"
          @refresh="load"
        />
      </n-tab-pane>
      <n-tab-pane name="req-roles" tab="需求角色">
        <RequirementRoleSettingsTab :project-id="ctx.projectId" :read-only="readOnly" />
      </n-tab-pane>
      <n-tab-pane name="req-fields" tab="需求字段">
        <RequirementFieldSettingsTab
          :project-id="ctx.projectId"
          :req-fields="reqFields"
          :saving="saving"
          :read-only="readOnly"
          @update:req-fields="reqFields = $event"
          @add-field="openFieldEdit('requirement', null)"
          @edit-field="(i) => openFieldEdit('requirement', i)"
        />
      </n-tab-pane>
      <n-tab-pane name="req-workflow" tab="需求工作流">
        <RequirementWorkflowSettingsTab :project-id="ctx.projectId" :read-only="readOnly" />
      </n-tab-pane>
      <n-tab-pane name="version-wecom" tab="版本企微">
        <VersionWecomSettingsTab v-if="ctx.projectId" :project-id="ctx.projectId" :read-only="readOnly" />
      </n-tab-pane>
      <n-tab-pane name="wecom" tab="企微通知">
        <n-form label-placement="top" style="max-width: 960px">
          <n-divider title-placement="left">基础配置</n-divider>
          <n-form-item label="启用"><n-switch v-model:value="wecom.wecom_enabled" :disabled="readOnly" /></n-form-item>
          <n-form-item label="Webhook URL">
            <n-input v-model:value="wecom.wecom_webhook_url" type="textarea" :rows="2" :disabled="readOnly" />
          </n-form-item>
          <n-form-item label="站点访问地址">
            <n-input
              v-model:value="wecom.app_public_url"
              placeholder="如 http://172.19.3.69:5174（企微通知 {link} 用，勿填 localhost）"
              clearable
              :disabled="readOnly"
            />
          </n-form-item>
          <n-space v-if="canEdit">
            <n-button type="primary" @click="saveWecomWebhook">保存 Webhook</n-button>
            <n-button @click="onTestWecom">发送测试</n-button>
          </n-space>

          <n-divider title-placement="left">通知规则</n-divider>
          <n-alert type="info" :bordered="false" style="margin-bottom: 12px">
            每条规则在编辑弹窗中保存后立即生效。占位符：{project} {num} {title} {from_status} {to_status}
            {reporter} {followers} {link}；评论另含 {commenter} {comment}，需求评论含 {status}。
            @ 提醒需通知对象本人在右上角「我的资料」填写企微 userid 或绑定手机号；未绑定则只发群消息、不会 @ 任何人。
          </n-alert>
          <n-data-table :columns="wecomRuleColumns" :data="sortedWecomRules" size="small" />
          <n-button v-if="canEdit" size="small" style="margin-top: 8px" @click="openRuleModal()">添加规则</n-button>
        </n-form>
      </n-tab-pane>
    </n-tabs>
    </template>

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
              :project-id="ctx.projectId"
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
      v-model:show="showRuleModal"
      preset="dialog"
      :title="editingRule ? '编辑通知规则' : '添加通知规则'"
      positive-text="保存"
      @positive-click="onSaveRule"
    >
      <n-form label-width="100">
        <n-form-item label="模块">
          <n-select
            v-model:value="ruleForm.entity_type"
            :options="entityTypeOptions"
            :disabled="!!editingRule"
            style="width: 100%"
          />
        </n-form-item>
        <n-form-item label="触发类型">
          <n-select
            v-model:value="ruleForm.kind"
            :options="ruleKindOptions"
            :disabled="!!editingRule"
            style="width: 100%"
          />
        </n-form-item>
        <template v-if="ruleForm.kind === 'transition'">
          <n-form-item label="原状态">
            <n-select
              v-model:value="ruleForm.from_status_keys"
              :options="statusKeyOptions"
              placeholder="选择原状态（可多选）"
              multiple
            />
          </n-form-item>
          <n-form-item label="目标状态">
            <n-select
              v-model:value="ruleForm.to_status_keys"
              :options="statusKeyOptions"
              placeholder="选择目标状态（可多选）"
              multiple
            />
          </n-form-item>
        </template>
        <n-form-item label="启用"><n-switch v-model:value="ruleForm.enabled" /></n-form-item>
        <n-form-item label="通知对象">
          <n-select
            v-model:value="ruleForm.notify_roles"
            :options="notifyRoleOptions"
            multiple
            style="width: 100%"
          />
        </n-form-item>
        <n-form-item label="消息模板">
          <n-input v-model:value="ruleForm.message_template" type="textarea" :rows="5" />
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
import {
  getTemplate,
  getWecom,
  listBugStatuses,
  testWecom,
  updateTemplate,
  updateWecom,
} from '@/api/templates';
import {
  createWecomNotifyRule,
  deleteWecomNotifyRule,
  listWecomNotifyRules,
  updateWecomNotifyRule,
  upsertCommentWecomRule,
  upsertCreateWecomRule,
} from '@/api/wecomRules';
import TemplateEditPreview from '@/components/TemplateEditPreview.vue';
import TemplateFieldPanel from '@/components/TemplateFieldPanel.vue';
import BugFieldSettingsTab from '@/views/setting/BugFieldSettingsTab.vue';
import RequirementFieldSettingsTab from '@/views/setting/RequirementFieldSettingsTab.vue';
import RequirementRoleSettingsTab from '@/views/setting/RequirementRoleSettingsTab.vue';
import RequirementWorkflowSettingsTab from '@/views/setting/RequirementWorkflowSettingsTab.vue';
import VersionWecomSettingsTab from '@/views/setting/VersionWecomSettingsTab.vue';
import {
  FIELD_TYPE_OPTIONS,
  generateFieldId,
  isOptionFieldType,
  normalizeFieldSort,
  type FieldTypeValue,
} from '@/constants/fieldTypes';
import { invalidateProjectFieldSchemaCache } from '@/composables/useProjectFieldSchema';
import { usePermissions } from '@/composables/usePermissions';
import { validateTemplateFieldNames } from '@/schemas/entityFieldSchema';
import { apiErrorMessage } from '@/utils/apiError';
import { useContextStore } from '@/stores/context';
import type {
  BugStatusDef,
  TemplateField,
  WecomEntityType,
  WecomNotifyRule,
  WecomRuleKind,
} from '@/types/business';

withDefaults(defineProps<{ embedded?: boolean }>(), { embedded: false });

const DEFAULT_CREATE_TEMPLATE =
  '【新建缺陷 {num}】{title}\n项目：{project}\n提出人：{reporter}\n跟进人：{followers}\n{link}';

const DEFAULT_TRANSITION_TEMPLATE =
  '【缺陷 {num}】{title}\n项目：{project}\n提出人：{reporter}\n跟进人：{followers}\n状态：{from_status} → {to_status}\n{link}';

const DEFAULT_BUG_COMMENT_TEMPLATE =
  '【缺陷 {num} 新评论】{title}\n项目：{project}\n评论人：{commenter}\n内容：{comment}\n{link}';

const DEFAULT_REQUIREMENT_COMMENT_TEMPLATE =
  '【需求 {num} 新评论】{title}\n项目：{project}\n状态：{status}\n评论人：{commenter}\n内容：{comment}\n{link}';

const ctx = useContextStore();
const { canManageProjectConfig } = usePermissions();
const message = useMessage();
const dialog = useDialog();

const canEdit = computed(() => canManageProjectConfig(ctx.projectId));
const readOnly = computed(() => !canEdit.value);

const tab = ref('case');
const saving = ref(false);
const caseFields = ref<TemplateField[]>([]);
const bugFields = ref<TemplateField[]>([]);
const reqFields = ref<TemplateField[]>([]);
const statuses = ref<BugStatusDef[]>([]);
const wecom = ref({
  wecom_enabled: false,
  wecom_webhook_url: '' as string | null,
  app_public_url: '' as string | null,
});

const wecomRules = ref<WecomNotifyRule[]>([]);
const showRuleModal = ref(false);
const editingRule = ref<WecomNotifyRule | null>(null);
const ruleForm = ref({
  entity_type: 'bug' as WecomEntityType,
  kind: 'transition' as WecomRuleKind,
  from_status_keys: [] as string[],
  to_status_keys: [] as string[],
  message_template: DEFAULT_TRANSITION_TEMPLATE,
  notify_roles: ['reporter', 'followers'] as string[],
  enabled: true,
});

const entityTypeOptions = [
  { label: '缺陷', value: 'bug' as const },
  { label: '需求', value: 'requirement' as const },
];

const bugNotifyRoleOptions = [
  { label: '提出人', value: 'reporter' },
  { label: '跟进人', value: 'followers' },
  { label: '处理人', value: 'assignee' },
];

const requirementNotifyRoleOptions = [
  { label: '创建人', value: 'creator' },
  { label: '产品经理', value: 'pm' },
  { label: '测试', value: 'qa' },
  { label: '技术负责人', value: 'tech_owner' },
  { label: '前端研发', value: 'frontend_rd' },
  { label: '后端研发', value: 'backend_rd' },
  { label: '设计师', value: 'designer' },
  { label: '各角色负责人', value: 'role_assignees' },
  { label: '节点任务处理人', value: 'task_assignees' },
];

const notifyRoleOptions = computed(() =>
  ruleForm.value.entity_type === 'requirement'
    ? requirementNotifyRoleOptions
    : bugNotifyRoleOptions
);

const showFieldDrawer = ref(false);
const fieldEditKind = ref<'case' | 'bug' | 'requirement'>('case');
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

const statusKeyOptions = computed(() =>
  statuses.value.map((s) => ({ label: s.label, value: s.key }))
);

const hasCreateRule = computed(() =>
  wecomRules.value.some((r) => r.entity_type === 'bug' && r.kind === 'create')
);

function hasCommentRule(entityType: WecomEntityType) {
  return wecomRules.value.some((r) => r.entity_type === entityType && r.kind === 'comment');
}

const ruleKindOptions = computed(() => {
  const entity = ruleForm.value.entity_type;
  const opts: { label: string; value: WecomRuleKind }[] = [];
  if (entity === 'bug') {
    if (!hasCreateRule.value || editingRule.value?.kind === 'create') {
      opts.push({ label: '新建缺陷', value: 'create' });
    }
    opts.push({ label: '状态流转', value: 'transition' });
  }
  if (!hasCommentRule(entity) || editingRule.value?.kind === 'comment') {
    opts.push({ label: '新评论', value: 'comment' });
  }
  return opts;
});

const sortedWecomRules = computed(() =>
  [...wecomRules.value].sort((a, b) => {
    const entityOrder = (r: WecomNotifyRule) => (r.entity_type === 'bug' ? 0 : 1);
    if (entityOrder(a) !== entityOrder(b)) return entityOrder(a) - entityOrder(b);
    const kindOrder = (r: WecomNotifyRule) => {
      if (r.kind === 'create') return 0;
      if (r.kind === 'comment') return 1;
      return 2;
    };
    if (kindOrder(a) !== kindOrder(b)) return kindOrder(a) - kindOrder(b);
    const af = a.from_status_key ?? '';
    const bf = b.from_status_key ?? '';
    if (af !== bf) return af.localeCompare(bf);
    return (a.to_status_key ?? '').localeCompare(b.to_status_key ?? '');
  })
);

function formatEntityType(entityType: WecomEntityType | undefined) {
  if (entityType === 'requirement') return '需求';
  return '缺陷';
}

function formatRuleKind(row: WecomNotifyRule) {
  if (row.kind === 'create') return '新建缺陷';
  if (row.kind === 'comment') return '新评论';
  return '状态流转';
}

function formatNotifyRoles(roles: string[]) {
  const map: Record<string, string> = {
    reporter: '提出人',
    followers: '跟进人',
    assignee: '处理人',
    creator: '创建人',
    pm: '产品经理',
    qa: '测试',
    tech_owner: '技术负责人',
    frontend_rd: '前端研发',
    backend_rd: '后端研发',
    designer: '设计师',
    role_assignees: '各角色负责人',
    task_assignees: '节点任务处理人',
  };
  return roles.map((r) => map[r] ?? r).join('、') || '-';
}

function defaultTemplateForRule(entityType: WecomEntityType, kind: WecomRuleKind) {
  if (kind === 'create') return DEFAULT_CREATE_TEMPLATE;
  if (kind === 'comment') {
    return entityType === 'requirement'
      ? DEFAULT_REQUIREMENT_COMMENT_TEMPLATE
      : DEFAULT_BUG_COMMENT_TEMPLATE;
  }
  return DEFAULT_TRANSITION_TEMPLATE;
}

function defaultRolesForRule(entityType: WecomEntityType, kind: WecomRuleKind) {
  if (kind === 'comment') {
    return entityType === 'requirement'
      ? ['creator', 'role_assignees', 'task_assignees']
      : ['reporter', 'followers', 'assignee'];
  }
  if (kind === 'create') return ['reporter', 'followers'];
  return ['reporter', 'followers'];
}

/** 字段编辑抽屉内：将当前表单草稿合并进列表，供右侧实时预览 */
const draftPreviewFields = computed<TemplateField[]>(() => {
  const base =
    fieldEditKind.value === 'case'
      ? [...caseFields.value]
      : fieldEditKind.value === 'bug'
        ? [...bugFields.value]
        : [...reqFields.value];
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

const wecomRuleColumns = computed<DataTableColumns<WecomNotifyRule>>(() => {
  const cols: DataTableColumns<WecomNotifyRule> = [
  {
    title: '模块',
    key: 'entity_type',
    width: 72,
    render: (r) => formatEntityType(r.entity_type),
  },
  {
    title: '触发',
    key: 'kind',
    width: 100,
    render: (r) => formatRuleKind(r),
  },
  {
    title: '原状态',
    key: 'from_status_key',
    width: 120,
    render: (r) => (r.kind === 'create' ? '-' : (r.from_status_label ?? r.from_status_key ?? '-')),
  },
  {
    title: '目标状态',
    key: 'to_status_key',
    width: 120,
    render: (r) => (r.kind === 'create' ? '-' : (r.to_status_label ?? r.to_status_key ?? '-')),
  },
  {
    title: '通知对象',
    key: 'notify_roles',
    ellipsis: { tooltip: true },
    render: (r) => formatNotifyRoles(r.notify_roles ?? []),
  },
  {
    title: '启用',
    key: 'enabled',
    width: 70,
    render: (r) => h(NTag, { type: r.enabled ? 'success' : 'default', size: 'small' }, () => (r.enabled ? '是' : '否')),
  },
  ];
  if (canEdit.value) {
    cols.push({
      title: '操作',
      key: 'actions',
      width: 140,
      render: (row) =>
        h(NSpace, { size: 4 }, () => [
          h(NButton, { size: 'tiny', quaternary: true, type: 'primary', onClick: () => openRuleModal(row) }, () => '编辑'),
          row.kind !== 'create'
            ? h(NButton, { size: 'tiny', quaternary: true, type: 'error', onClick: () => removeRule(row) }, () => '删除')
            : null,
        ]),
    });
  }
  return cols;
});

function openFieldEdit(kind: 'case' | 'bug' | 'requirement', index: number | null) {
  if (readOnly.value) return;
  fieldEditKind.value = kind;
  fieldEditIndex.value = index;
  const list =
    kind === 'case' ? caseFields.value : kind === 'bug' ? bugFields.value : reqFields.value;
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
  const list =
    fieldEditKind.value === 'case'
      ? [...caseFields.value]
      : fieldEditKind.value === 'bug'
        ? [...bugFields.value]
        : [...reqFields.value];
  if (fieldEditIndex.value === null) {
    list.push(row);
  } else {
    list[fieldEditIndex.value] = row;
  }
  const normalized = normalizeFieldSort(list);
  if (fieldEditKind.value === 'case') caseFields.value = normalized;
  else if (fieldEditKind.value === 'bug') bugFields.value = normalized;
  else reqFields.value = normalized;
  showFieldDrawer.value = false;
}

function applyWecomRules(rules: WecomNotifyRule[]) {
  wecomRules.value = rules;
}

function ruleStatusKeys(row: WecomNotifyRule, side: 'from' | 'to'): string[] {
  if (side === 'from') {
    if (row.from_status_keys?.length) return row.from_status_keys;
    if (row.from_status_key) return [row.from_status_key];
    return [];
  }
  if (row.to_status_keys?.length) return row.to_status_keys;
  if (row.to_status_key) return [row.to_status_key];
  return [];
}

function openRuleModal(row?: WecomNotifyRule) {
  if (readOnly.value) return;
  editingRule.value = row ?? null;
  if (row) {
    ruleForm.value = {
      entity_type: row.entity_type ?? 'bug',
      kind: row.kind,
      from_status_keys: [...ruleStatusKeys(row, 'from')],
      to_status_keys: [...ruleStatusKeys(row, 'to')],
      message_template: row.message_template,
      notify_roles: [...(row.notify_roles ?? defaultRolesForRule(row.entity_type ?? 'bug', row.kind))],
      enabled: row.enabled,
    };
  } else {
    const entity_type: WecomEntityType = 'bug';
    let kind: WecomRuleKind = 'transition';
    if (!hasCreateRule.value) kind = 'create';
    else if (!hasCommentRule(entity_type)) kind = 'comment';
    ruleForm.value = {
      entity_type,
      kind,
      from_status_keys: [],
      to_status_keys: [],
      message_template: defaultTemplateForRule(entity_type, kind),
      notify_roles: defaultRolesForRule(entity_type, kind),
      enabled: true,
    };
  }
  showRuleModal.value = true;
}

function removeRule(row: WecomNotifyRule) {
  if (row.kind === 'create') {
    message.warning('新建缺陷规则不可删除，请编辑后关闭启用');
    return;
  }
  const desc =
    row.kind === 'transition'
      ? `删除流转规则「${row.from_status_label ?? row.from_status_key} → ${row.to_status_label ?? row.to_status_key}」？`
      : `删除${formatEntityType(row.entity_type)}评论通知规则？`;
  dialog.warning({
    title: '确认删除',
    content: desc,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      const projectId = ctx.projectId;
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

async function onSaveRule() {
  const projectId = ctx.projectId;
  if (!projectId) return false;
  const f = ruleForm.value;
  if (!f.message_template.trim()) {
    message.warning('请填写消息模板');
    return false;
  }
  if (f.kind === 'transition') {
    if (!f.from_status_keys.length || !f.to_status_keys.length) {
      message.warning('请至少选择一个原状态和一个目标状态');
      return false;
    }
    const overlap = f.from_status_keys.filter((k) => f.to_status_keys.includes(k));
    if (overlap.length) {
      message.warning('原状态与目标状态不能有相同项');
      return false;
    }
  }
  try {
    const payload = {
      message_template: f.message_template.trim(),
      notify_roles: f.notify_roles,
      enabled: f.enabled,
    };
    if (f.kind === 'create') {
      if (editingRule.value) {
        await updateWecomNotifyRule(projectId, editingRule.value.id, payload);
      } else {
        await upsertCreateWecomRule(projectId, payload);
      }
    } else if (f.kind === 'comment') {
      if (editingRule.value) {
        await updateWecomNotifyRule(projectId, editingRule.value.id, payload);
      } else {
        await upsertCommentWecomRule(projectId, {
          entity_type: f.entity_type,
          ...payload,
        });
      }
    } else if (editingRule.value) {
      await updateWecomNotifyRule(projectId, editingRule.value.id, {
        ...payload,
        from_status_keys: f.from_status_keys,
        to_status_keys: f.to_status_keys,
      });
    } else {
      await createWecomNotifyRule(projectId, {
        entity_type: f.entity_type,
        kind: 'transition',
        from_status_keys: f.from_status_keys,
        to_status_keys: f.to_status_keys,
        ...payload,
      });
    }
    showRuleModal.value = false;
    message.success('已保存');
    await loadWecomRules(projectId);
    return true;
  } catch (e) {
    message.error(apiErrorMessage(e, '保存失败'));
    return false;
  }
}

async function loadWecomRules(projectId: string) {
  const { data } = await listWecomNotifyRules(projectId);
  applyWecomRules(data);
}

async function load() {
  if (!ctx.projectId) {
    caseFields.value = [];
    bugFields.value = [];
    reqFields.value = [];
    statuses.value = [];
    wecom.value = { wecom_enabled: false, wecom_webhook_url: null, app_public_url: null };
    wecomRules.value = [];
    return;
  }
  try {
    const projectId = ctx.projectId;
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
      app_public_url: w.data.app_public_url,
    };
    applyWecomRules(rules.data);
  } catch {
    message.error('加载项目设置失败，请确认是否选择了正确的项目且有权限');
  }
}

async function saveTemplate(scene: 'functional_case' | 'bug' | 'requirement', fields: TemplateField[]) {
  const projectId = ctx.projectId;
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

async function saveWecomWebhook(): Promise<boolean> {
  const projectId = ctx.projectId;
  if (!projectId) return false;
  try {
    const { data } = await updateWecom(projectId, wecom.value);
    wecom.value = {
      wecom_enabled: data.wecom_enabled,
      wecom_webhook_url: data.wecom_webhook_url,
      app_public_url: data.app_public_url,
    };
    message.success('Webhook 已保存');
    return true;
  } catch (e) {
    message.error(apiErrorMessage(e, '保存失败'));
    return false;
  }
}

async function onTestWecom() {
  const projectId = ctx.projectId;
  if (!projectId) return;
  const url = wecom.value.wecom_webhook_url?.trim();
  if (!url) {
    message.warning('请先填写 Webhook URL');
    return;
  }
  const saved = await saveWecomWebhook();
  if (!saved) return;
  try {
    await testWecom(projectId);
    message.success('测试消息已发送，请到企微群查看');
  } catch (e) {
    message.error(apiErrorMessage(e, '发送失败，请确认 Webhook URL 已保存且有效'));
  }
}

watch(
  () => ruleForm.value.entity_type,
  (entityType) => {
    if (!showRuleModal.value || editingRule.value) return;
    const { kind } = ruleForm.value;
    if (entityType === 'requirement' && (kind === 'create' || kind === 'transition')) {
      ruleForm.value.kind = 'comment';
      ruleForm.value.message_template = defaultTemplateForRule(entityType, 'comment');
      ruleForm.value.notify_roles = defaultRolesForRule(entityType, 'comment');
    }
  }
);

watch(() => ctx.projectId, () => {
  void load();
});

onMounted(() => {
  void load();
});
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
