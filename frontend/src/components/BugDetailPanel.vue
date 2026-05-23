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
        <template v-if="editMode">
          <n-button quaternary size="small" @click="cancelEdit">取消</n-button>
          <n-button size="small" type="primary" :loading="saving" @click="saveBug">保存</n-button>
        </template>
        <template v-else-if="canEdit">
          <n-button quaternary size="small" @click="enterEdit">编辑</n-button>
          <n-button quaternary size="small" type="error" @click="onDelete">删除</n-button>
        </template>
        <n-button quaternary size="small" @click="emit('close')">关闭</n-button>
      </n-space>
    </div>

    <div v-if="!editMode" class="panel-title-row">
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

    <div class="panel-body" :class="{ 'panel-body--edit': editMode }">
    <template v-if="!editMode">
      <n-descriptions :column="2" label-placement="left" class="field-block">
        <n-descriptions-item
          v-for="field in templateUiFields"
          :key="field.id"
          :label="field.name"
          :span="isRichtextType(field.type) ? 2 : 1"
        >
          <InlineMarkdownContent
            v-if="isRichtextType(field.type) && richTextHasContent(customFields[field.id])"
            :text="richTextPlain(customFields[field.id])"
            :project-id="bug.project_id"
          />
          <template v-else>{{ formatTemplateFieldValue(field, customFields[field.id], templateFieldCtx) }}</template>
        </n-descriptions-item>
        <n-descriptions-item label="提出人">{{ reporterLabel }}</n-descriptions-item>
        <n-descriptions-item label="跟进人">{{ followersLabel }}</n-descriptions-item>
        <n-descriptions-item label="规划迭代">{{ planVersionLabel }}</n-descriptions-item>
        <n-descriptions-item label="发现版本">{{ foundVersionLabel }}</n-descriptions-item>
        <n-descriptions-item label="关联需求" :span="2">{{ requirementsLabel }}</n-descriptions-item>
        <n-descriptions-item label="关联测试计划" :span="2">{{ plansLabel }}</n-descriptions-item>
      </n-descriptions>
      <n-text depth="3" class="section-label">描述</n-text>
      <InlineMarkdownContent
        v-if="bug.description?.trim()"
        :text="bug.description"
        :project-id="bug.project_id"
        class="desc-preview"
      />
      <n-text v-else depth="3">—</n-text>
      <n-text depth="3" class="section-label">附件</n-text>
      <div v-if="attachments.length" class="attachment-list">
        <div v-for="att in attachments" :key="att.id" class="attachment-item">
          <n-space align="center" :size="8" wrap>
            <n-text>{{ att.filename }}</n-text>
            <a
              v-if="!isPreviewableAttachment(att.filename)"
              :href="att.url"
              target="_blank"
              rel="noopener noreferrer"
              class="attachment-link"
            >
              查看
            </a>
            <a :href="attachmentDownloadUrl(att.url)" class="attachment-link attachment-link--muted">
              下载
            </a>
          </n-space>
          <n-text depth="3" class="attachment-meta">
            {{ formatFileSize(att.size) }} · {{ formatTime(att.created_at) }}
          </n-text>
          <n-image
            v-if="isImageAttachment(att.filename)"
            :src="att.url"
            :alt="att.filename"
            object-fit="contain"
            class="attachment-thumb"
          />
          <video
            v-else-if="isVideoAttachment(att.filename)"
            :src="att.url"
            controls
            preload="metadata"
            class="attachment-video"
          />
        </div>
      </div>
      <n-text v-else depth="3">—</n-text>
    </template>

    <BugFormFields
      v-else
      v-model="editForm"
      v-model:custom-fields="customFields"
      mode="edit"
      class="field-block"
      :project-id="bug.project_id"
      :template-fields="templateUiFields"
      :status-options="statusOptions"
      :member-options="memberOptions"
      :member-name-options="memberNameOptions"
      :requirement-options="requirementOptions"
      :plan-options="planOptions"
    >
      <template #attachments>
        <n-space vertical :size="8" style="width: 100%">
          <n-upload :custom-request="onUpload" :show-file-list="false">
            <n-button size="small">上传附件</n-button>
          </n-upload>
          <div v-if="attachments.length" class="attachment-list attachment-list--compact">
            <div v-for="att in attachments" :key="att.id" class="attachment-item attachment-item--compact">
              <n-space align="center" justify="space-between" style="width: 100%">
                <div class="attachment-item-main">
                  <n-space align="center" :size="8" wrap>
                    <n-text>{{ att.filename }}</n-text>
                    <a
                      v-if="!isPreviewableAttachment(att.filename)"
                      :href="att.url"
                      target="_blank"
                      rel="noopener noreferrer"
                      class="attachment-link"
                    >
                      查看
                    </a>
                    <a :href="attachmentDownloadUrl(att.url)" class="attachment-link attachment-link--muted">
                      下载
                    </a>
                  </n-space>
                  <n-text depth="3" class="attachment-meta">
                    {{ formatFileSize(att.size) }} · {{ formatTime(att.created_at) }}
                  </n-text>
                </div>
                <n-button size="tiny" quaternary type="error" @click="onDeleteAttachment(att)">
                  删除
                </n-button>
              </n-space>
              <n-image
                v-if="isImageAttachment(att.filename)"
                :src="att.url"
                :alt="att.filename"
                object-fit="contain"
                class="attachment-thumb attachment-thumb--compact"
              />
              <video
                v-else-if="isVideoAttachment(att.filename)"
                :src="att.url"
                controls
                preload="metadata"
                class="attachment-video attachment-video--compact"
              />
            </div>
          </div>
        </n-space>
      </template>
    </BugFormFields>

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
  NImage,
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
  deleteBugAttachment,
  getBug,
  listBugActivities,
  listBugAttachments,
  listBugComments,
  updateBug,
  uploadAttachment,
} from '@/api/bugs';
import { listPlans } from '@/api/plans';
import { listRequirements } from '@/api/requirements';
import { listBugStatuses } from '@/api/templates';
import BugFormFields, { type BugFormModel } from '@/components/BugFormFields.vue';
import InlineMarkdownContent from '@/components/InlineMarkdownContent.vue';
import PasteImageTextarea from '@/components/PasteImageTextarea.vue';
import {
  formatTemplateFieldValue,
  isRichtextType,
  richTextHasContent,
  richTextPlain,
} from '@/schemas/entityFieldSchema';
import { ensureContextForProject } from '@/composables/useProjectTemplate';
import { useProjectFieldSchema } from '@/composables/useProjectFieldSchema';
import { useProjectMemberOptions } from '@/composables/useProjectMemberOptions';
import { usePermissions } from '@/composables/usePermissions';
import { useContextStore } from '@/stores/context';
import { mergeCustomFields, validateCustomFields } from '@/constants/fieldTypes';
import {
  attachmentDownloadUrl,
  isImageAttachment,
  isPreviewableAttachment,
  isVideoAttachment,
} from '@/utils/attachmentPreview';
import type { BugActivity, BugAttachment, BugComment, BugItem, BugStatusDef, Requirement, TestPlan } from '@/types/business';
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
const attachments = ref<BugAttachment[]>([]);
const newComment = ref('');

const ctx = useContextStore();

const editForm = ref<BugFormModel>({
  title: '',
  status_key: '',
  description: '',
  reporter_id: null,
  follower_ids: [],
  requirement_ids: [],
  plan_ids: [],
  plan_version_id: null,
  found_version_id: null,
});

const schemaProjectId = computed(() => bug.value?.project_id ?? ctx.projectId);
const projectIdRef = computed(() => bug.value?.project_id ?? ctx.projectId);
const { options: memberOptions, nameOptions: memberNameOptions, nameByUserId } =
  useProjectMemberOptions(projectIdRef);
const fieldSchema = useProjectFieldSchema('bug', schemaProjectId);
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

const requirementOptions = computed(() =>
  requirements.value.map((r) => ({ label: r.title, value: r.id }))
);
const planOptions = computed(() => plans.value.map((p) => ({ label: p.name, value: p.id })));

function formatTime(iso: string) {
  return new Date(iso).toLocaleString('zh-CN');
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function memberName(userId: string | null | undefined): string {
  if (!userId) return '—';
  return nameByUserId.value.get(userId) ?? userId;
}

const templateFieldCtx = computed(() => ({ memberLabel: memberName }));

function commentAuthorLabel(c: BugComment): string {
  return displayUserLabel(c.user, c.user_id, memberName(c.user_id));
}

function activityActorLabel(a: BugActivity): string {
  const id = a.actor?.id;
  return displayUserLabel(a.actor, id, id ? memberName(id) : null) || '系统';
}

const reporterLabel = computed(() => {
  if (!bug.value) return '—';
  const name = bug.value.reporter?.name?.trim();
  if (name) return name;
  return memberName(bug.value.reporter_id);
});

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

async function loadAttachments() {
  const { data } = await listBugAttachments(props.bugId);
  attachments.value = data;
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
    await Promise.all([loadCommentsAndActivities(), loadAttachments()]);
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
  await Promise.all([loadAttachments(), loadCommentsAndActivities()]);
}

function onDeleteAttachment(att: BugAttachment) {
  dialog.warning({
    title: '删除附件',
    content: `确定删除附件「${att.filename}」？`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await deleteBugAttachment(props.bugId, att.id);
        message.success('已删除');
        await Promise.all([loadAttachments(), loadCommentsAndActivities()]);
      } catch (e: unknown) {
        const detail =
          e && typeof e === 'object' && 'response' in e
            ? (e as { response?: { data?: { detail?: string } } }).response?.data?.detail
            : undefined;
        message.error(typeof detail === 'string' ? detail : '删除失败');
      }
    },
  });
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

.panel-body--edit {
  padding: 12px 16px 16px;
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

.attachment-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.attachment-item {
  padding: 10px 12px;
  border: 1px solid var(--n-border-color);
  border-radius: 8px;
  background: var(--n-color);
}

.attachment-item-main {
  min-width: 0;
  flex: 1;
}

.attachment-link {
  color: var(--n-primary-color, #18a058);
  text-decoration: none;
  word-break: break-all;
}

.attachment-link:hover {
  text-decoration: underline;
}

.attachment-link--muted {
  font-size: 12px;
}

.attachment-meta {
  display: block;
  margin-top: 4px;
  font-size: 12px;
}

.attachment-thumb {
  display: block;
  margin-top: 8px;
  max-width: 100%;
  max-height: 200px;
  border-radius: 4px;
}

.attachment-video {
  display: block;
  margin-top: 8px;
  max-width: 100%;
  max-height: 360px;
  border-radius: 4px;
  background: #000;
}

.attachment-list--compact {
  gap: 6px;
}

.attachment-item--compact {
  padding: 6px 8px;
}

.attachment-thumb--compact {
  max-height: 120px;
}

.attachment-video--compact {
  max-height: 240px;
  margin-top: 6px;
}
</style>
