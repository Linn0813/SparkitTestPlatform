<template>
  <div v-if="loading && !caseItem" class="panel-loading">
    <n-spin size="medium" />
  </div>
  <div v-else-if="caseItem" class="case-detail-panel">
    <div class="panel-toolbar">
      <n-space :size="4" align="center">
        <n-button quaternary size="small" :disabled="!hasPrev" @click="emit('prev')">上一条</n-button>
        <n-button quaternary size="small" :disabled="!hasNext" @click="emit('next')">下一条</n-button>
      </n-space>
      <n-space :size="4" align="center">
        <template v-if="editMode">
          <n-button quaternary size="small" @click="cancelEdit">取消</n-button>
          <n-button size="small" type="primary" :loading="saving" @click="saveCase">保存</n-button>
        </template>
        <template v-else-if="canEdit">
          <n-button quaternary size="small" @click="enterEdit">编辑</n-button>
          <n-button quaternary size="small" type="error" @click="onDelete">删除</n-button>
        </template>
        <n-button quaternary size="small" @click="emit('close')">关闭</n-button>
      </n-space>
    </div>

    <div class="panel-title-row">
      <n-text strong class="case-title">{{ caseItem.title }}</n-text>
      <n-dropdown
        v-if="planExecution && !editMode"
        trigger="click"
        :options="resultMenuOptions"
        :disabled="planExecution.readOnly || resultSaving"
        @select="onResultMenuSelect"
      >
        <n-tag
          :type="currentResultTagType"
          size="medium"
          round
          :bordered="false"
          class="status-chip"
          :class="{ 'status-chip--disabled': planExecution.readOnly }"
        >
          <span v-if="resultSaving">更新中…</span>
          <template v-else>
            {{ currentResultLabel }}
            <span v-if="!planExecution.readOnly" class="status-caret">▾</span>
          </template>
        </n-tag>
      </n-dropdown>
      <n-tag v-else-if="!editMode" size="medium" round :bordered="false" type="info">{{ caseItem.priority }}</n-tag>
    </div>

    <div class="panel-body">
      <template v-if="!editMode">
        <n-descriptions :column="2" label-placement="left" class="field-block">
          <n-descriptions-item label="模块">{{ moduleLabel }}</n-descriptions-item>
          <n-descriptions-item label="优先级">{{ caseItem.priority }}</n-descriptions-item>
          <n-descriptions-item label="关联需求" :span="2">{{ requirementsLabel }}</n-descriptions-item>
          <n-descriptions-item
            v-for="field in templateUiFields"
            :key="field.id"
            :label="field.name"
            :span="isRichtextType(field.type) ? 2 : 1"
          >
            <InlineMarkdownContent
              v-if="isRichtextType(field.type) && richTextHasContent(customFields[field.id])"
              :text="richTextPlain(customFields[field.id])"
              :project-id="caseItem.project_id"
            />
            <template v-else>{{ formatTemplateFieldValue(field, customFields[field.id]) }}</template>
          </n-descriptions-item>
        </n-descriptions>
        <n-text depth="3" class="section-label">前置条件</n-text>
        <InlineMarkdownContent
          v-if="caseItem.precondition?.trim()"
          :text="caseItem.precondition"
          :project-id="caseItem.project_id"
          class="text-preview"
        />
        <n-text v-else depth="3">—</n-text>
        <n-text depth="3" class="section-label">步骤</n-text>
        <n-text v-if="caseItem.step_text?.trim()" class="text-block">{{ caseItem.step_text }}</n-text>
        <n-text v-else depth="3">—</n-text>
        <n-text depth="3" class="section-label">预期结果</n-text>
        <n-text v-if="caseItem.expected_result?.trim()" class="text-block">{{ caseItem.expected_result }}</n-text>
        <n-text v-else depth="3">—</n-text>

        <template v-if="planExecution && !editMode">
          <n-text depth="3" class="section-label">执行记录</n-text>
          <n-space vertical style="width: 100%">
            <div v-for="c in execComments" :key="c.id" class="comment-item">
              <n-text strong>{{ commentAuthorLabel(c) }}</n-text>
              <n-text depth="3" style="font-size: 12px; margin-left: 8px">{{ formatTime(c.created_at) }}</n-text>
              <InlineMarkdownContent
                :text="c.body"
                :project-id="caseItem.project_id"
                class="comment-body"
              />
            </div>
            <n-empty v-if="!execComments.length" description="暂无执行记录" size="small" />
            <template v-if="!planExecution.readOnly">
              <PasteImageTextarea
                v-model="newExecComment"
                :project-id="caseItem.project_id"
                placeholder="记录执行过程、环境、截图说明等"
              />
              <n-button
                type="primary"
                :disabled="!newExecComment.trim()"
                :loading="commentSaving"
                @click="submitExecComment"
              >
                发表记录
              </n-button>
            </template>
          </n-space>
        </template>
      </template>

      <n-form v-else label-placement="top" class="field-block">
        <n-form-item label="用例标题" required>
          <n-input v-model:value="editForm.title" />
        </n-form-item>
        <n-form-item label="模块" required>
          <n-select
            v-model:value="editForm.module_id"
            :options="moduleOptions"
            filterable
            style="width: 100%"
          />
        </n-form-item>
        <n-form-item label="优先级">
          <n-select v-model:value="editForm.priority" :options="priorityOptions" style="width: 100%" />
        </n-form-item>
        <n-form-item label="前置条件">
          <PasteImageTextarea v-model="editForm.precondition" :project-id="caseItem.project_id" />
        </n-form-item>
        <n-form-item label="步骤">
          <n-input v-model:value="editForm.step_text" type="textarea" :rows="4" />
        </n-form-item>
        <n-form-item label="预期结果">
          <n-input v-model:value="editForm.expected_result" type="textarea" :rows="4" />
        </n-form-item>
        <n-form-item label="关联需求">
          <n-select
            v-model:value="editForm.requirement_ids"
            :options="requirementOptions"
            multiple
            filterable
            clearable
            style="width: 100%"
          />
        </n-form-item>
        <DynamicFieldForm
          v-if="templateUiFields.length"
          v-model="customFields"
          :fields="templateUiFields"
          :project-id="caseItem.project_id"
        />
      </n-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import {
  NButton,
  NDescriptions,
  NDescriptionsItem,
  NDropdown,
  NEmpty,
  NForm,
  NFormItem,
  NInput,
  NSelect,
  NSpace,
  NSpin,
  NTag,
  NText,
  useDialog,
  useMessage,
} from 'naive-ui';
import { deleteCase, getCase, updateCase } from '@/api/cases';
import { createPlanCaseComment, listPlanCaseComments, updatePlanResult } from '@/api/plans';
import { fetchRequirementOptions, requirementOptionsParams } from '@/api/requirements';
import { PLAN_RESULT_OPTIONS, planResultLabel, planResultTagType } from '@/constants/planStatus';
import DynamicFieldForm from '@/components/DynamicFieldForm.vue';
import InlineMarkdownContent from '@/components/InlineMarkdownContent.vue';
import PasteImageTextarea from '@/components/PasteImageTextarea.vue';
import {
  formatTemplateFieldValue,
  isRichtextType,
  richTextHasContent,
  richTextPlain,
} from '@/schemas/entityFieldSchema';
import { useCaseModules } from '@/composables/useCaseModules';
import { ensureContextForProject } from '@/composables/useProjectTemplate';
import { useProjectFieldSchema } from '@/composables/useProjectFieldSchema';
import { useProjectMemberOptions } from '@/composables/useProjectMemberOptions';
import { usePermissions } from '@/composables/usePermissions';
import { mergeCustomFields, validateCustomFields } from '@/constants/fieldTypes';
import type { PlanCaseResultComment, TestCase } from '@/types/business';
import type { RequirementSelectOption } from '@/api/requirements';
import { displayUserLabel } from '@/utils/displayUser';
import { modulePathLabel } from '@/utils/moduleTree';
import { requirementOptionLabel } from '@/utils/requirementLabel';

export interface PlanExecutionContext {
  planId: string;
  planCaseId: string;
  result: string;
  readOnly: boolean;
}

const props = defineProps<{
  caseId: string;
  hasPrev?: boolean;
  hasNext?: boolean;
  planExecution?: PlanExecutionContext | null;
}>();

const emit = defineEmits<{
  prev: [];
  next: [];
  close: [];
  deleted: [];
  updated: [];
  'execution-updated': [];
}>();

const message = useMessage();
const dialog = useDialog();
const { canManageCases } = usePermissions();
const { modules, moduleOptions, loadModules } = useCaseModules();

const caseItem = ref<TestCase | null>(null);
const loading = ref(false);
const editMode = ref(false);
const saving = ref(false);
const resultSaving = ref(false);
const commentSaving = ref(false);
const execResult = ref('not_run');
const execComments = ref<PlanCaseResultComment[]>([]);
const newExecComment = ref('');
const requirements = ref<RequirementSelectOption[]>([]);
const customFields = ref<Record<string, unknown>>({});

const projectIdRef = computed(() => caseItem.value?.project_id ?? null);
const { nameByUserId } = useProjectMemberOptions(projectIdRef);

const resultMenuOptions = computed(() =>
  PLAN_RESULT_OPTIONS.map((o) => ({ label: o.label, key: o.value }))
);

const currentResultLabel = computed(() => planResultLabel(execResult.value));

const currentResultTagType = computed(() => planResultTagType(execResult.value));

const editForm = ref({
  title: '',
  module_id: '',
  priority: 'P2',
  precondition: '',
  step_text: '',
  expected_result: '',
  requirement_ids: [] as string[],
});

const priorityOptions = ['P0', 'P1', 'P2', 'P3'].map((v) => ({ label: v, value: v }));

const projectIdRefForSchema = computed(() => caseItem.value?.project_id ?? null);
const fieldSchema = useProjectFieldSchema('functional_case', projectIdRefForSchema);
const templateUiFields = computed(() => fieldSchema.templateFieldsForUi.value);

const canEdit = computed(() => canManageCases(caseItem.value?.project_id));

const requirementOptions = computed(() =>
  requirements.value.map((r) => ({
    label: requirementOptionLabel(r, { showNum: false }),
    value: r.id,
  }))
);

const moduleLabel = computed(() => {
  if (!caseItem.value) return '—';
  return (
    caseItem.value.module_path ||
    modulePathLabel(modules.value, caseItem.value.module_id) ||
    '—'
  );
});

const requirementsLabel = computed(() => {
  if (!caseItem.value) return '—';
  const ids = caseItem.value.requirement_ids ?? [];
  if (!ids.length) return '—';
  const labels = ids
    .map((id) => requirements.value.find((r) => r.id === id)?.title)
    .filter(Boolean) as string[];
  return labels.length ? labels.join('、') : '—';
});

function formatTime(iso: string) {
  return new Date(iso).toLocaleString('zh-CN');
}

function memberName(userId: string | null | undefined): string {
  if (!userId) return '—';
  return nameByUserId.value.get(userId) ?? userId;
}

function commentAuthorLabel(c: PlanCaseResultComment): string {
  return displayUserLabel(c.user, c.user_id, memberName(c.user_id));
}

function fillEditForm(c: TestCase) {
  editForm.value = {
    title: c.title,
    module_id: c.module_id,
    priority: c.priority,
    precondition: c.precondition ?? '',
    step_text: c.step_text ?? '',
    expected_result: c.expected_result ?? '',
    requirement_ids: [...(c.requirement_ids ?? [])],
  };
  customFields.value = mergeCustomFields(fieldSchema.templateFieldsForUi.value, c.custom_fields);
}

async function loadExecutionComments() {
  if (!props.planExecution) {
    execComments.value = [];
    return;
  }
  const { data } = await listPlanCaseComments(
    props.planExecution.planId,
    props.planExecution.planCaseId
  );
  execComments.value = data;
}

async function load() {
  loading.value = true;
  try {
    const { data } = await getCase(props.caseId);
    caseItem.value = data;
    await ensureContextForProject(data.project_id);
    await loadModules();
    const [, req] = await Promise.all([
      fieldSchema.reload(),
      fetchRequirementOptions(requirementOptionsParams(data.requirement_ids)),
    ]);
    requirements.value = req;
    customFields.value = mergeCustomFields(fieldSchema.templateFieldsForUi.value, data.custom_fields);
    fillEditForm(data);
    await loadExecutionComments();
  } finally {
    loading.value = false;
  }
}

function enterEdit() {
  if (!caseItem.value) return;
  fillEditForm(caseItem.value);
  editMode.value = true;
}

function cancelEdit() {
  if (caseItem.value) {
    fillEditForm(caseItem.value);
    customFields.value = mergeCustomFields(
      fieldSchema.templateFieldsForUi.value,
      caseItem.value.custom_fields
    );
  }
  editMode.value = false;
}

async function saveCase() {
  if (!caseItem.value) return;
  const err = validateCustomFields(fieldSchema.templateFieldsForUi.value, customFields.value);
  if (err) {
    message.warning(err);
    return;
  }
  if (!editForm.value.title.trim()) {
    message.warning('请填写用例标题');
    return;
  }
  if (!editForm.value.module_id) {
    message.warning('请选择模块');
    return;
  }
  saving.value = true;
  try {
    const { data } = await updateCase(props.caseId, {
      title: editForm.value.title.trim(),
      module_id: editForm.value.module_id,
      priority: editForm.value.priority,
      precondition: editForm.value.precondition || null,
      step_text: editForm.value.step_text || null,
      expected_result: editForm.value.expected_result || null,
      requirement_ids: editForm.value.requirement_ids,
      custom_fields: customFields.value,
    });
    caseItem.value = data;
    editMode.value = false;
    message.success('已保存');
    emit('updated');
  } finally {
    saving.value = false;
  }
}

function onDelete() {
  dialog.warning({
    title: '删除用例',
    content: '确定删除该用例？此操作不可恢复。',
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      await deleteCase(props.caseId);
      message.success('已删除');
      emit('deleted');
    },
  });
}

function syncExecutionFromProps() {
  if (!props.planExecution) return;
  execResult.value = props.planExecution.result;
}

function onResultMenuSelect(key: string) {
  if (key && key !== execResult.value) {
    onResultChange(key);
  }
}

async function onResultChange(result: string) {
  if (!props.planExecution || props.planExecution.readOnly) return;
  const prev = execResult.value;
  execResult.value = result;
  resultSaving.value = true;
  try {
    await updatePlanResult(props.planExecution.planId, {
      plan_case_id: props.planExecution.planCaseId,
      result,
    });
    message.success('执行结果已更新');
    emit('execution-updated');
  } catch {
    execResult.value = prev;
    message.error('执行结果更新失败');
  } finally {
    resultSaving.value = false;
  }
}

async function submitExecComment() {
  if (!props.planExecution || !newExecComment.value.trim()) return;
  commentSaving.value = true;
  try {
    const { data } = await createPlanCaseComment(
      props.planExecution.planId,
      props.planExecution.planCaseId,
      newExecComment.value.trim()
    );
    execComments.value = [...execComments.value, data];
    newExecComment.value = '';
    message.success('执行记录已发表');
    emit('execution-updated');
  } finally {
    commentSaving.value = false;
  }
}

watch(
  () => props.caseId,
  () => {
    editMode.value = false;
    load();
  },
  { immediate: true }
);

watch(
  () => props.planExecution,
  async () => {
    syncExecutionFromProps();
    await loadExecutionComments();
  },
  { immediate: true, deep: true }
);
</script>

<style scoped>
.panel-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
}

.case-detail-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.panel-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border-bottom: 1px solid var(--n-border-color);
  flex-shrink: 0;
}

.panel-title-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 0 16px 12px;
  border-bottom: 1px solid var(--n-border-color);
  flex-shrink: 0;
}

.case-title {
  font-size: 17px;
  line-height: 1.4;
  flex: 1;
  min-width: 0;
  word-break: break-word;
}

.status-chip {
  cursor: pointer;
  font-weight: 600;
  flex-shrink: 0;
  user-select: none;
}

.status-chip--disabled {
  cursor: default;
  opacity: 0.85;
}

.status-caret {
  margin-left: 4px;
  font-size: 11px;
  opacity: 0.75;
}

.panel-body {
  flex: 1;
  overflow: auto;
  padding: 16px 20px 24px;
  min-height: 0;
}

.field-block {
  margin-top: 0;
}

.section-label {
  display: block;
  margin-top: 16px;
  margin-bottom: 8px;
}

.text-preview {
  width: 100%;
  padding: 12px;
  background: var(--n-color-modal);
  border-radius: 6px;
  border: 1px solid var(--n-border-color);
}

.text-block {
  white-space: pre-wrap;
  word-break: break-word;
  display: block;
  padding: 12px;
  background: var(--n-color-modal);
  border-radius: 6px;
  border: 1px solid var(--n-border-color);
}

.comment-item {
  padding: 12px;
  border: 1px solid var(--n-border-color);
  border-radius: 8px;
  background: var(--n-color);
}

.comment-body {
  margin-top: 8px;
}
</style>
