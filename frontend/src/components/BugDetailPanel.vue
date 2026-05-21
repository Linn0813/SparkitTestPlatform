<template>
  <div v-if="loading && !bug" class="panel-loading">
    <n-spin size="medium" />
  </div>
  <div v-else-if="bug" class="bug-detail-panel">
    <div class="panel-toolbar">
      <n-space :size="4" align="center">
        <n-button quaternary size="small" :disabled="!hasPrev" @click="emit('prev')">上一条</n-button>
        <n-button quaternary size="small" :disabled="!hasNext" @click="emit('next')">下一条</n-button>
      </n-space>
      <n-space :size="4" align="center">
        <n-dropdown v-if="canEdit" trigger="click" :options="moreMenuOptions" @select="onMoreMenu">
          <n-button quaternary size="small">更多</n-button>
        </n-dropdown>
        <n-button quaternary size="small" @click="emit('close')">关闭</n-button>
      </n-space>
    </div>

    <div class="panel-title-row">
      <n-text strong class="bug-title">{{ bug.title }}</n-text>
      <n-dropdown
        v-if="!editMode"
        trigger="click"
        :options="statusMenuOptions"
        :disabled="!canChangeStatus || statusSaving"
        @select="onStatusMenuSelect"
      >
        <n-tag
          :type="currentStatusTagType"
          size="medium"
          round
          :bordered="false"
          class="status-chip"
          :class="{ 'status-chip--disabled': !canChangeStatus }"
        >
          <span v-if="statusSaving">更新中…</span>
          <template v-else>
            {{ currentStatusLabel }}
            <span v-if="canChangeStatus" class="status-caret">▾</span>
          </template>
        </n-tag>
      </n-dropdown>
    </div>

    <div class="panel-body">
    <template v-if="!editMode">
      <n-descriptions :column="2" label-placement="left" class="field-block">
        <n-descriptions-item label="提出人">{{ reporterLabel }}</n-descriptions-item>
        <n-descriptions-item label="跟进人">{{ followersLabel }}</n-descriptions-item>
        <n-descriptions-item label="规划迭代">{{ planVersionLabel }}</n-descriptions-item>
        <n-descriptions-item label="发现版本">{{ foundVersionLabel }}</n-descriptions-item>
        <n-descriptions-item label="关联需求" :span="2">{{ requirementsLabel }}</n-descriptions-item>
        <n-descriptions-item label="关联测试计划" :span="2">{{ plansLabel }}</n-descriptions-item>
        <SchemaTemplateFieldsView
          :fields="templateUiFields"
          :values="customFields"
          :project-id="bug.project_id"
          :member-label="memberName"
        />
      </n-descriptions>
      <n-text depth="3" class="section-label">描述</n-text>
      <InlineMarkdownContent
        v-if="bug.description?.trim()"
        :text="bug.description"
        :project-id="bug.project_id"
        class="desc-preview"
      />
      <n-text v-else depth="3">—</n-text>
    </template>

    <n-form v-else label-placement="top" class="field-block">
      <n-form-item label="缺陷标题" required>
        <n-input v-model:value="editForm.title" />
      </n-form-item>
      <n-form-item label="状态">
        <n-radio-group v-model:value="editForm.status_key" name="bug-status" size="small">
          <n-space wrap :size="[8, 8]">
            <n-radio-button v-for="opt in statusOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </n-radio-button>
          </n-space>
        </n-radio-group>
      </n-form-item>
      <n-form-item label="提出人">
        <n-select v-model:value="editForm.reporter_id" :options="memberOptions" filterable style="width: 100%" />
      </n-form-item>
      <n-form-item label="跟进人">
        <n-select
          v-model:value="editForm.follower_ids"
          :options="memberOptions"
          multiple
          filterable
          clearable
          style="width: 100%"
        />
      </n-form-item>
      <n-form-item label="规划迭代">
        <VersionSelect v-model="editForm.plan_version_id" :project-id="bug.project_id" />
      </n-form-item>
      <n-form-item label="发现版本">
        <VersionSelect v-model="editForm.found_version_id" :project-id="bug.project_id" />
      </n-form-item>
      <DynamicFieldForm
        v-if="templateUiFields.length"
        v-model="customFields"
        :fields="templateUiFields"
        :project-id="bug.project_id"
        :show-divider="templateUiFields.length > 0"
        title="自定义字段"
      />
      <n-form-item label="描述">
        <PasteImageTextarea v-model="editForm.description" :project-id="bug.project_id" />
      </n-form-item>
      <n-form-item label="附件">
        <n-upload :custom-request="onUpload" :show-file-list="false">
          <n-button>上传附件</n-button>
        </n-upload>
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
      <n-form-item label="关联测试计划">
        <n-select
          v-model:value="editForm.plan_ids"
          :options="planOptions"
          multiple
          filterable
          clearable
          style="width: 100%"
        />
      </n-form-item>
      <n-space>
        <n-button @click="cancelEdit">取消</n-button>
        <n-button type="primary" :loading="saving" @click="saveBug">保存</n-button>
      </n-space>
    </n-form>

    <n-tabs v-if="!editMode" type="line" class="tabs-block">
      <n-tab-pane name="comments" tab="评论">
        <n-space vertical style="width: 100%">
          <div v-for="c in comments" :key="c.id" class="comment-item">
            <n-text strong>{{ commentAuthorLabel(c) }}</n-text>
            <n-text depth="3" style="font-size: 12px; margin-left: 8px">{{ formatTime(c.created_at) }}</n-text>
            <InlineMarkdownContent :text="c.body" :project-id="bug.project_id" class="comment-body" />
          </div>
          <n-empty v-if="!comments.length" description="暂无评论" size="small" />
          <template v-if="canComment">
            <PasteImageTextarea
              v-model="newComment"
              :project-id="bug.project_id"
              placeholder="输入评论，支持粘贴截图"
            />
            <n-button type="primary" :disabled="!newComment.trim()" @click="submitComment">发表评论</n-button>
          </template>
        </n-space>
      </n-tab-pane>
      <n-tab-pane name="activities" tab="操作记录">
        <n-timeline style="margin-top: 8px">
          <n-timeline-item v-for="a in activities" :key="`${a.source}-${a.id}`" :time="formatTime(a.created_at)">
            <n-text strong>{{ activityActorLabel(a) }}</n-text>
            <span style="margin-left: 8px">{{ formatActivitySummary(a) }}</span>
          </n-timeline-item>
        </n-timeline>
        <n-empty v-if="!activities.length" description="暂无记录" size="small" />
      </n-tab-pane>
    </n-tabs>
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
  NRadioButton,
  NRadioGroup,
  NSelect,
  NSpace,
  NSpin,
  NTabPane,
  NTabs,
  NTag,
  NText,
  NTimeline,
  NTimelineItem,
  NUpload,
  useDialog,
  useMessage,
} from 'naive-ui';
import type { UploadCustomRequestOptions } from 'naive-ui';
import {
  createBugComment,
  deleteBug,
  getBug,
  listBugActivities,
  listBugComments,
  updateBug,
  uploadAttachment,
} from '@/api/bugs';
import { listPlans } from '@/api/plans';
import { listRequirements } from '@/api/requirements';
import { listBugStatuses } from '@/api/templates';
import DynamicFieldForm from '@/components/DynamicFieldForm.vue';
import SchemaTemplateFieldsView from '@/components/SchemaTemplateFieldsView.vue';
import InlineMarkdownContent from '@/components/InlineMarkdownContent.vue';
import PasteImageTextarea from '@/components/PasteImageTextarea.vue';
import VersionSelect from '@/components/VersionSelect.vue';
import { ensureContextForProject } from '@/composables/useProjectTemplate';
import { useProjectFieldSchema } from '@/composables/useProjectFieldSchema';
import { useProjectMemberOptions } from '@/composables/useProjectMemberOptions';
import { usePermissions } from '@/composables/usePermissions';
import { mergeCustomFields, validateCustomFields } from '@/constants/fieldTypes';
import type { BugActivity, BugComment, BugItem, BugStatusDef, Requirement, TestPlan } from '@/types/business';
import { displayUserLabel } from '@/utils/displayUser';
import { formatNumWithTitle } from '@/utils/entityNum';

const props = defineProps<{
  bugId: string;
  hasPrev?: boolean;
  hasNext?: boolean;
}>();

const emit = defineEmits<{
  prev: [];
  next: [];
  close: [];
  deleted: [];
  updated: [];
}>();

const message = useMessage();
const dialog = useDialog();
const { canManageBugs, canChangeBugStatus, canCommentBug } = usePermissions();

const bug = ref<BugItem | null>(null);
const loading = ref(false);
const editMode = ref(false);
const saving = ref(false);
const statusSaving = ref(false);
const viewStatusKey = ref<string | null>(null);

const statuses = ref<BugStatusDef[]>([]);
const customFields = ref<Record<string, unknown>>({});
const requirements = ref<Requirement[]>([]);
const plans = ref<TestPlan[]>([]);
const comments = ref<BugComment[]>([]);
const activities = ref<BugActivity[]>([]);
const newComment = ref('');

const editForm = ref({
  title: '',
  status_key: '',
  description: '',
  reporter_id: null as string | null,
  follower_ids: [] as string[],
  requirement_ids: [] as string[],
  plan_ids: [] as string[],
  plan_version_id: null as string | null,
  found_version_id: null as string | null,
});

const projectIdRef = computed(() => bug.value?.project_id ?? null);
const { options: memberOptions } = useProjectMemberOptions(projectIdRef);
const fieldSchema = useProjectFieldSchema('bug', projectIdRef);
const templateUiFields = computed(() => fieldSchema.templateFieldsForUi.value);

const canEdit = computed(() => canManageBugs(bug.value?.project_id));
const canChangeStatus = computed(() => canChangeBugStatus(bug.value?.project_id));
const canComment = computed(() => canCommentBug(bug.value?.project_id));

const statusOptions = computed(() => statuses.value.map((x) => ({ label: x.label, value: x.key })));

const statusMenuOptions = computed(() =>
  statuses.value.map((x) => ({ label: x.label, key: x.key }))
);

const currentStatusLabel = computed(() => statusLabel(viewStatusKey.value ?? bug.value?.status_key));

const currentStatusTagType = computed(() => {
  const key = viewStatusKey.value ?? bug.value?.status_key;
  const row = statuses.value.find((s) => s.key === key);
  if (row?.is_terminal) return 'success';
  if (key === 'pending_confirm' || key === 'new') return 'warning';
  if (key === 'processing' || key === 'in_progress') return 'info';
  return 'default';
});

function onStatusMenuSelect(key: string) {
  if (key && key !== viewStatusKey.value) {
    onStatusChange(key);
  }
}

const statusLabelMap = computed(() => {
  const m = new Map<string, string>();
  for (const s of statuses.value) m.set(s.key, s.label);
  return m;
});

function statusLabel(key: string | null | undefined): string {
  if (!key) return '—';
  return statusLabelMap.value.get(key) ?? key;
}

function formatActivitySummary(a: BugActivity): string {
  if (a.action_type === 'status_change' || a.source === 'status_history') {
    const detail = a.detail ?? {};
    const fromKey = detail.from_status as string | null | undefined;
    const toKey = detail.to_status as string | null | undefined;
    if (fromKey !== undefined || toKey !== undefined) {
      return `状态变更：${statusLabel(fromKey)} → ${statusLabel(toKey)}`;
    }
  }
  return a.summary;
}

const moreMenuOptions = [
  { label: '编辑', key: 'edit' },
  { label: '删除', key: 'delete' },
];

const requirementOptions = computed(() =>
  requirements.value.map((r) => ({ label: r.title, value: r.id }))
);
const planOptions = computed(() => plans.value.map((p) => ({ label: p.name, value: p.id })));

function formatTime(iso: string) {
  return new Date(iso).toLocaleString('zh-CN');
}

function memberName(userId: string | null | undefined): string {
  if (!userId) return '—';
  return memberOptions.value.find((o) => o.value === userId)?.label ?? userId;
}

function commentAuthorLabel(c: BugComment): string {
  return displayUserLabel(c.user, c.user_id, memberName(c.user_id));
}

function activityActorLabel(a: BugActivity): string {
  const id = a.actor?.id;
  return displayUserLabel(a.actor, id, id ? memberName(id) : null) || '系统';
}

const reporterLabel = computed(() =>
  displayUserLabel(bug.value?.reporter, bug.value?.reporter_id, memberName(bug.value?.reporter_id))
);

const followersLabel = computed(() => {
  if (!bug.value) return '—';
  const names = bug.value.followers?.map((f) => f.name).filter(Boolean);
  if (names?.length) return names.join('、');
  if (bug.value.follower_ids?.length) {
    return bug.value.follower_ids.map((id) => memberName(id)).join('、');
  }
  return '—';
});

const planVersionLabel = computed(() => bug.value?.plan_version?.name ?? '—');
const foundVersionLabel = computed(() => bug.value?.found_version?.name ?? '—');

function linkTitles(ids: string[] | undefined, list: { id: string; title?: string; name?: string }[]) {
  if (!ids?.length) return '—';
  const labels = ids
    .map((id) => {
      const row = list.find((x) => x.id === id);
      return row ? (row.title ?? row.name ?? id) : null;
    })
    .filter(Boolean) as string[];
  return labels.length ? labels.join('、') : '—';
}

const requirementsLabel = computed(() => linkTitles(bug.value?.requirement_ids, requirements.value));
const plansLabel = computed(() => linkTitles(bug.value?.plan_ids, plans.value));

function fillEditForm(b: BugItem) {
  editForm.value = {
    title: b.title,
    status_key: b.status_key,
    description: b.description ?? '',
    reporter_id: b.reporter_id,
    follower_ids: [...(b.follower_ids ?? [])],
    requirement_ids: [...(b.requirement_ids ?? [])],
    plan_ids: [...(b.plan_ids ?? [])],
    plan_version_id: b.plan_version_id ?? null,
    found_version_id: b.found_version_id ?? null,
  };
  customFields.value = mergeCustomFields(fieldSchema.templateFieldsForUi.value, b.custom_fields);
}

async function loadCommentsAndActivities() {
  const [c, a] = await Promise.all([listBugComments(props.bugId), listBugActivities(props.bugId)]);
  comments.value = c.data;
  activities.value = a.data;
}

async function load() {
  loading.value = true;
  try {
    const b = await getBug(props.bugId);
    bug.value = b.data;
    viewStatusKey.value = b.data.status_key;
    const projectId = b.data.project_id;
    await ensureContextForProject(projectId);
    const [, s, req, pl] = await Promise.all([
      fieldSchema.reload(true),
      listBugStatuses(projectId),
      listRequirements(),
      listPlans(),
    ]);
    statuses.value = s.data;
    requirements.value = req.data;
    plans.value = pl.data;
    customFields.value = mergeCustomFields(fieldSchema.templateFieldsForUi.value, b.data.custom_fields);
    fillEditForm(b.data);
    await loadCommentsAndActivities();
  } finally {
    loading.value = false;
  }
}

function enterEdit() {
  if (!bug.value) return;
  fillEditForm(bug.value);
  editMode.value = true;
}

function cancelEdit() {
  if (bug.value) {
    fillEditForm(bug.value);
    viewStatusKey.value = bug.value.status_key;
    customFields.value = mergeCustomFields(fieldSchema.templateFieldsForUi.value, bug.value.custom_fields);
  }
  editMode.value = false;
}

function onMoreMenu(key: string) {
  if (key === 'edit') enterEdit();
  if (key === 'delete') onDelete();
}

async function onStatusChange(key: string) {
  if (!bug.value || key === bug.value.status_key) return;
  statusSaving.value = true;
  try {
    await updateBug(props.bugId, { status_key: key });
    message.success('状态已更新');
    await load();
    emit('updated');
  } catch {
    viewStatusKey.value = bug.value.status_key;
    message.error('状态更新失败');
  } finally {
    statusSaving.value = false;
  }
}

async function saveBug() {
  if (!bug.value) return;
  const err = validateCustomFields(fieldSchema.templateFieldsForUi.value, customFields.value);
  if (err) {
    message.warning(err);
    return;
  }
  if (!editForm.value.title.trim()) {
    message.warning('请填写缺陷标题');
    return;
  }
  saving.value = true;
  try {
    await updateBug(props.bugId, {
      title: editForm.value.title.trim(),
      status_key: editForm.value.status_key,
      description: editForm.value.description || undefined,
      custom_fields: customFields.value,
      requirement_ids: editForm.value.requirement_ids,
      plan_ids: editForm.value.plan_ids,
      plan_version_id: editForm.value.plan_version_id,
      found_version_id: editForm.value.found_version_id,
      reporter_id: editForm.value.reporter_id ?? undefined,
      follower_ids: editForm.value.follower_ids,
    });
    message.success('已保存');
    editMode.value = false;
    await load();
    emit('updated');
  } finally {
    saving.value = false;
  }
}

function onDelete() {
  if (!bug.value) return;
  dialog.warning({
    title: '删除缺陷',
    content: `确定删除缺陷「${formatNumWithTitle(bug.value.num, bug.value.title)}」？`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      await deleteBug(props.bugId);
      message.success('已删除');
      emit('deleted');
    },
  });
}

async function submitComment() {
  if (!newComment.value.trim()) return;
  await createBugComment(props.bugId, newComment.value.trim());
  newComment.value = '';
  message.success('评论已发表');
  await loadCommentsAndActivities();
}

async function onUpload({ file }: UploadCustomRequestOptions) {
  if (!file.file) return;
  await uploadAttachment(props.bugId, file.file as File);
  message.success('已上传');
  await loadCommentsAndActivities();
}

watch(
  () => props.bugId,
  () => {
    editMode.value = false;
    load();
  },
  { immediate: true }
);
</script>

<style scoped>
.panel-loading {
  display: flex;
  justify-content: center;
  padding: 48px;
}

.bug-detail-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.panel-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px 8px;
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

.bug-title {
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

.desc-preview {
  width: 100%;
  padding: 12px;
  background: var(--n-color-modal);
  border-radius: 6px;
  border: 1px solid var(--n-border-color);
}

.tabs-block {
  margin-top: 20px;
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
