<template>
  <div v-if="loading && !req" class="panel-loading">
    <n-spin size="medium" />
  </div>
  <div v-else-if="req" class="requirement-detail-panel">
    <div class="header-block">
      <div class="panel-toolbar">
        <n-space :size="4" align="center">
          <n-button quaternary size="small" :disabled="!hasPrev" @click="emit('prev')">上一条</n-button>
          <n-button quaternary size="small" :disabled="!hasNext" @click="emit('next')">下一条</n-button>
        </n-space>
        <n-space :size="4" align="center">
          <template v-if="editMode">
            <n-button quaternary size="small" @click="cancelEdit">取消</n-button>
            <n-button size="small" type="primary" :loading="saving" @click="saveReq">保存</n-button>
          </template>
          <template v-else-if="canEdit">
            <n-button quaternary size="small" @click="enterEdit">编辑</n-button>
            <n-button
              v-if="canCloseRequirement"
              quaternary
              size="small"
              :loading="closeSaving"
              @click="onCloseRequirement"
            >
              关闭需求
            </n-button>
            <n-button quaternary size="small" type="error" @click="onDelete">删除</n-button>
          </template>
          <n-button quaternary size="small" @click="emit('close')">关闭</n-button>
        </n-space>
      </div>

      <div v-if="!editMode" class="panel-title-row">
        <n-text strong>{{ req.title }}</n-text>
        <n-tag
          :type="requirementPriorityTagType(req.priority)"
          size="small"
          round
          :bordered="false"
        >
          {{ projectConfig.priorityLabel(req.priority) }}
        </n-tag>
        <n-tag :type="requirementStatusTagType(req.status)" size="small" round :bordered="false">
          {{ requirementStatusLabel(req.status) }}
        </n-tag>
      </div>
    </div>

    <div class="panel-body" :class="{ 'panel-body--edit': editMode }">
      <template v-if="!editMode">
        <div v-if="req.status === 'closed'" class="status-banner closed-banner">
          <n-text depth="2">需求已关闭</n-text>
          <n-button v-if="canEdit" size="small" type="primary" :loading="nodeSaving" @click="onReopenClosed">
            重新打开
          </n-button>
        </div>

        <div class="workflow-block" @click.self="clearNodeSelection">
          <RequirementWorkflowCanvas
            mode="view"
            :nodes="canvasNodes"
            :req-type="req.req_type"
            :workflow-frozen="workflowFrozen"
            :selected-node-key="selectedNodeKey"
            @node-select="onNodeSelect"
          />
        </div>

        <div v-if="selectedNode" class="node-detail-block">
          <RequirementNodeDetailPanel
            :requirement="req"
            :node="selectedNode"
            :node-tasks="selectedNodeTasks"
            :member-options="memberOptions"
            :can-edit="!!canEdit"
            :workflow-frozen="workflowFrozen"
            :req-type="req.req_type"
            :loading="nodeSaving"
            @node-action="onNodeAction"
            @tasks-updated="onTasksUpdated"
          />
        </div>

        <div class="tabs-block">
          <n-tabs type="line" animated>
            <n-tab-pane name="info" tab="需求信息">
              <EntityDetailFieldList
                v-if="detailFieldContext"
                class="field-block"
                :rows="detailRows"
                :context="detailFieldContext"
                :project-id="req.project_id"
              />
              <div v-if="activeWorkflowRoles.length" class="people-fields field-block">
                <div class="field-pair">
                  <div v-for="role in activeWorkflowRoles" :key="role.key" class="field-cell">
                    <div class="field-label">{{ role.label }}</div>
                    <div class="field-value">{{ roleUserLabel(role.key) }}</div>
                  </div>
                </div>
              </div>
              <n-text v-else depth="3" class="empty-roles-hint">
                请先启用工作流节点，再配置相关人员
              </n-text>
            </n-tab-pane>
            <n-tab-pane name="comments" tab="评论">
              <n-space vertical style="width: 100%">
                <div v-for="c in comments" :key="c.id" class="comment-item">
                  <n-text strong>{{ commentAuthorLabel(c) }}</n-text>
                  <n-text depth="3" class="comment-time">{{ formatTime(c.created_at) }}</n-text>
                  <InlineMarkdownContent :text="c.body" :project-id="req.project_id" class="comment-body" />
                </div>
                <n-empty v-if="!comments.length" description="暂无评论" size="small" />
                <template v-if="canEdit">
                  <PasteImageTextarea
                    v-model="newComment"
                    :project-id="req.project_id"
                    placeholder="输入评论，支持粘贴截图"
                  />
                  <n-button
                    type="primary"
                    :disabled="!newComment.trim()"
                    :loading="commentSaving"
                    @click="submitComment"
                  >
                    发表评论
                  </n-button>
                </template>
              </n-space>
            </n-tab-pane>
            <n-tab-pane name="activities" tab="操作记录">
              <n-timeline v-if="activities.length" size="medium">
                <n-timeline-item v-for="a in activities" :key="a.id" :time="formatTime(a.created_at)">
                  {{ a.summary }}
                  <template v-if="a.actor?.name"> · {{ a.actor.name }}</template>
                </n-timeline-item>
              </n-timeline>
              <n-empty v-else description="暂无记录" size="small" />
            </n-tab-pane>
          </n-tabs>
        </div>
      </template>

      <RequirementFormEditor
        v-else-if="req"
        :project-id="req.project_id"
        v-model:form="form"
        v-model:custom-fields="customFields"
        v-model:selected-roles="selectedRoles"
        v-model:enabled-draft="enabledDraft"
        :workflow-nodes="editWorkflowNodeSources"
        :workflow-frozen="workflowFrozen"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import {
  NButton,
  NEmpty,
  NSpace,
  NSpin,
  NTabPane,
  NTabs,
  NTag,
  NText,
  NTimeline,
  NTimelineItem,
  useDialog,
  useMessage,
} from 'naive-ui';
import {
  createRequirementComment,
  deleteRequirement,
  listRequirementActivities,
  listRequirementComments,
  closeRequirement,
  reopenClosedRequirement,
  requirementNodeAction,
  syncRequirementStatus,
  updateRequirement,
  type RequirementNodeAction,
} from '@/api/requirements';
import { updateRequirementWorkflowEnabled } from '@/api/requirementWorkflow';
import EntityDetailFieldList from '@/components/EntityDetailFieldList.vue';
import InlineMarkdownContent from '@/components/InlineMarkdownContent.vue';
import PasteImageTextarea from '@/components/PasteImageTextarea.vue';
import RequirementFormEditor, { type RequirementFormModel } from '@/components/RequirementFormEditor.vue';
import RequirementNodeDetailPanel from '@/components/RequirementNodeDetailPanel.vue';
import RequirementWorkflowCanvas from '@/components/RequirementWorkflowCanvas.vue';
import { LEGACY_ROLE_ID_FIELDS } from '@/constants/requirementNodes';
import { requirementPriorityTagType } from '@/constants/requirementPriority';
import { requirementStatusLabel, requirementStatusTagType } from '@/constants/requirementStatus';
import {
  mergeCustomFields,
  validateCustomFields,
} from '@/constants/fieldTypes';
import { useProjectFieldSchema } from '@/composables/useProjectFieldSchema';
import { useProjectMemberOptions } from '@/composables/useProjectMemberOptions';
import { useRequirementProjectConfig } from '@/composables/useRequirementProjectConfig';
import { buildRequirementDetailRows, type RequirementDetailFieldContext } from '@/schemas/entityFieldSchema';
import { usePermissions } from '@/composables/usePermissions';
import type { Requirement, RequirementActivity, RequirementComment } from '@/types/business';
import { buildFullEnabledMap, syncEnabledDraftWithSelectedRoles } from '@/utils/requirementEditWorkflow';
import {
  expandWorkflowCanvasNodes,
  type WorkflowCanvasNode,
  type WorkflowNodeSource,
} from '@/utils/requirementWorkflowLayout';

const props = defineProps<{
  requirementId: string;
  hasPrev?: boolean;
  hasNext?: boolean;
}>();

const emit = defineEmits<{
  close: [];
  prev: [];
  next: [];
  deleted: [];
  updated: [Requirement];
}>();

const message = useMessage();
const dialog = useDialog();
const { canManageCatalog } = usePermissions();

const req = ref<Requirement | null>(null);
const activities = ref<RequirementActivity[]>([]);
const comments = ref<RequirementComment[]>([]);
const loading = ref(false);
const saving = ref(false);
const nodeSaving = ref(false);
const closeSaving = ref(false);
const commentSaving = ref(false);
const newComment = ref('');
const editMode = ref(false);
const enabledDraft = ref<Record<string, boolean>>({});
const selectedRoles = ref<string[]>([]);
const selectedNodeKey = ref<string | null>(null);

const { options: memberOptions } = useProjectMemberOptions(computed(() => req.value?.project_id ?? null));
const projectConfig = useRequirementProjectConfig(() => req.value?.project_id ?? null);
const schemaProjectId = computed(() => req.value?.project_id ?? null);
const fieldSchema = useProjectFieldSchema('requirement', schemaProjectId);
const customFields = ref<Record<string, unknown>>({});
const detailRows = computed(() => buildRequirementDetailRows(fieldSchema.templateFields.value));

const detailFieldContext = computed<RequirementDetailFieldContext | null>(() => {
  if (!req.value) return null;
  return {
    req: req.value,
    customFields: customFields.value,
    templateFields: fieldSchema.templateFields.value,
    priorityLabel: projectConfig.priorityLabel,
    typeLabel: projectConfig.typeLabel,
    memberLabel: (userId: string) => memberOptions.value.find((o) => o.value === userId)?.label ?? userId,
  };
});

interface ProjectRoleField {
  key: string;
  label: string;
  idField?: string;
}

const projectRoleFields = computed<ProjectRoleField[]>(() =>
  projectConfig.roles.value.map((r) => ({
    key: r.role_key,
    label: r.label,
    idField: LEGACY_ROLE_ID_FIELDS[r.role_key],
  }))
);

const canEdit = computed(() => req.value && canManageCatalog(req.value.project_id));

const workflowFrozen = computed(() => req.value?.status === 'closed');

const canCloseRequirement = computed(() => {
  if (!canEdit.value || !req.value) return false;
  const s = req.value.status;
  return s !== 'closed' && s !== 'released';
});

const baseCanvasNodes = computed<WorkflowCanvasNode[]>(() =>
  expandWorkflowCanvasNodes(
    (req.value?.nodes ?? []).map(
      (n): WorkflowNodeSource => ({
        node_key: n.node_key,
        label: n.label,
        role_keys: n.role_keys,
        lane_index: n.lane_index,
        lane_indexes: n.lane_indexes,
        blocks_lane_gate: n.blocks_lane_gate,
        sort_in_lane: n.sort_in_lane,
        enabled: n.enabled,
        state: n.state,
      })
    )
  )
);

const canvasNodes = computed<WorkflowCanvasNode[]>(() =>
  baseCanvasNodes.value.filter((n) => n.enabled)
);

const editWorkflowNodeSources = computed<WorkflowNodeSource[]>(() =>
  (req.value?.nodes ?? []).map((n) => ({
    node_key: n.node_key,
    label: n.label,
    role_keys: n.role_keys,
    lane_index: n.lane_index,
    lane_indexes: n.lane_indexes,
    blocks_lane_gate: n.blocks_lane_gate,
    sort_in_lane: n.sort_in_lane,
    enabled: n.enabled,
    state: n.state,
  }))
);

const activeWorkflowRoles = computed(() => {
  const keys = new Set<string>();
  for (const node of req.value?.nodes ?? []) {
    if (!node.enabled) continue;
    for (const rk of node.role_keys) keys.add(rk);
  }
  return projectRoleFields.value.filter((r) => keys.has(r.key));
});

const selectedNode = computed(() => {
  if (!selectedNodeKey.value || !req.value) return null;
  return req.value.nodes.find((n) => n.node_key === selectedNodeKey.value) ?? null;
});

const selectedNodeTasks = computed(() => {
  if (!selectedNodeKey.value || !req.value?.node_tasks) return [];
  return req.value.node_tasks
    .filter((t) => t.node_key === selectedNodeKey.value)
    .sort((a, b) => a.sort - b.sort || a.created_at.localeCompare(b.created_at));
});

function onTasksUpdated(updated: Requirement) {
  req.value = updated;
}

function roleUserLabel(roleKey: string): string {
  if (!req.value) return '—';
  const ids = req.value.role_assignee_ids?.[roleKey];
  if (ids?.length) {
    const labels = ids
      .map((id) => memberOptions.value.find((o) => o.value === id)?.label)
      .filter((label): label is string => !!label);
    if (labels.length) return labels.join('、');
  }
  const map: Record<string, { id: string; name: string } | null | undefined> = {
    frontend_rd: req.value.frontend_rd,
    backend_rd: req.value.backend_rd,
    pm: req.value.pm,
    tech_owner: req.value.tech_owner,
    qa: req.value.qa,
    designer: req.value.designer,
  };
  const u = map[roleKey] as { name?: string; email?: string } | null | undefined;
  return u?.name?.trim() || '—';
}

function commentAuthorLabel(c: RequirementComment): string {
  return c.user?.name?.trim() || '未知用户';
}

function formatTime(iso: string): string {
  return iso.replace('T', ' ').slice(0, 16);
}

function collectRoleKeysFromNodes(useEnabledOnly: boolean): Set<string> {
  const keys = new Set<string>();
  for (const node of req.value?.nodes ?? []) {
    const enabled = enabledDraft.value[node.node_key] ?? node.enabled;
    if (useEnabledOnly && !enabled) continue;
    for (const rk of node.role_keys) keys.add(rk);
  }
  return keys;
}

function deriveSelectedRolesFromRequirement() {
  const keys = collectRoleKeysFromNodes(true);
  selectedRoles.value = projectRoleFields.value
    .filter((r) => keys.has(r.key))
    .map((r) => r.key);
}

async function ensureProjectRolesLoaded() {
  if (!projectRoleFields.value.length && req.value?.project_id) {
    await projectConfig.reload();
  }
}

function onNodeSelect(nodeKey: string) {
  selectedNodeKey.value = selectedNodeKey.value === nodeKey ? null : nodeKey;
}

function clearNodeSelection() {
  selectedNodeKey.value = null;
}

function syncEnabledDraft() {
  const map: Record<string, boolean> = {};
  for (const n of req.value?.nodes ?? []) {
    map[n.node_key] = n.enabled;
  }
  enabledDraft.value = map;
}

async function load() {
  loading.value = true;
  try {
    const [{ data: acts }, { data: cmts }] = await Promise.all([
      listRequirementActivities(props.requirementId),
      listRequirementComments(props.requirementId),
    ]);
    const { data: synced } = await syncRequirementStatus(props.requirementId);
    req.value = synced;
    activities.value = acts;
    comments.value = cmts;
    await Promise.all([projectConfig.reload(), fieldSchema.reload()]);
    customFields.value = mergeCustomFields(fieldSchema.templateFieldsForUi.value, synced.custom_fields);
    emit('updated', synced);
    syncEnabledDraft();
    selectedNodeKey.value = null;
  } finally {
    loading.value = false;
  }
}

function syncFormFromReq() {
  if (!req.value) return;
  const roleUserIds: Record<string, string[]> = {};
  for (const role of projectRoleFields.value) {
    const stored = req.value.role_assignee_ids?.[role.key];
    if (stored?.length) {
      roleUserIds[role.key] = [...stored];
    } else if (role.idField) {
      const single = req.value[role.idField as keyof Requirement] as string | null | undefined;
      roleUserIds[role.key] = single ? [single] : [];
    } else {
      roleUserIds[role.key] = [];
    }
  }
  form.value = {
    title: req.value.title,
    external_url: req.value.external_url ?? '',
    version_id: req.value.version_id,
    priority: req.value.priority,
    req_type: req.value.req_type,
    roleUserIds,
  };
  customFields.value = mergeCustomFields(fieldSchema.templateFieldsForUi.value, req.value.custom_fields);
}

const form = ref<RequirementFormModel>({
  title: '',
  external_url: '',
  version_id: null,
  priority: 'p1',
  req_type: 'feature',
  roleUserIds: {},
});

async function enterEdit() {
  clearNodeSelection();
  syncEnabledDraft();
  await ensureProjectRolesLoaded();
  syncFormFromReq();
  deriveSelectedRolesFromRequirement();
  editMode.value = true;
}

async function cancelEdit() {
  syncEnabledDraft();
  await ensureProjectRolesLoaded();
  deriveSelectedRolesFromRequirement();
  syncFormFromReq();
  editMode.value = false;
}

async function saveReq() {
  if (!req.value || !form.value.title.trim()) {
    message.warning('请填写标题');
    return;
  }
  const fieldErr = validateCustomFields(fieldSchema.templateFieldsForUi.value, customFields.value);
  if (fieldErr) {
    message.warning(fieldErr);
    return;
  }
  saving.value = true;
  try {
    const workflowSources = editWorkflowNodeSources.value;
    enabledDraft.value = syncEnabledDraftWithSelectedRoles(
      workflowSources,
      selectedRoles.value,
      enabledDraft.value
    );
    const enabledPayload = buildFullEnabledMap(
      workflowSources,
      selectedRoles.value,
      enabledDraft.value
    );
    const role_assignee_ids: Record<string, string[]> = {};
    const roleKeys = new Set<string>();
    for (const node of workflowSources) {
      if (!enabledPayload[node.node_key]) continue;
      for (const rk of node.role_keys) {
        if (selectedRoles.value.includes(rk)) roleKeys.add(rk);
      }
    }
    for (const roleKey of roleKeys) {
      role_assignee_ids[roleKey] = form.value.roleUserIds[roleKey] ?? [];
    }
    await updateRequirement(req.value.id, {
      title: form.value.title.trim(),
      external_url: form.value.external_url.trim() || null,
      version_id: form.value.version_id,
      priority: form.value.priority,
      req_type: form.value.req_type,
      role_assignee_ids,
      custom_fields: customFields.value,
    });
    await updateRequirementWorkflowEnabled(req.value.id, enabledPayload);
    const { data: synced } = await syncRequirementStatus(req.value.id);
    req.value = synced;
    syncEnabledDraft();
    const selected = req.value.nodes.find((n) => n.node_key === selectedNodeKey.value);
    if (!selected?.enabled) {
      selectedNodeKey.value = null;
    }
    editMode.value = false;
    message.success('已保存');
    emit('updated', synced);
  } catch (e: unknown) {
    const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
    message.error(typeof detail === 'string' ? detail : '保存失败');
  } finally {
    saving.value = false;
  }
}

function onDelete() {
  if (!req.value) return;
  dialog.warning({
    title: '删除需求',
    content: `确定删除「${req.value.title}」？`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      await deleteRequirement(req.value!.id);
      message.success('已删除');
      emit('deleted');
    },
  });
}

async function onNodeAction(nodeKey: string, action: RequirementNodeAction) {
  if (!req.value) return;
  nodeSaving.value = true;
  try {
    const { data } = await requirementNodeAction(req.value.id, nodeKey, action);
    req.value = data;
    const { data: acts } = await listRequirementActivities(req.value.id);
    activities.value = acts;
    message.success('已更新');
    emit('updated', data);
  } catch (e: unknown) {
    const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
    message.error(typeof detail === 'string' ? detail : '操作失败');
  } finally {
    nodeSaving.value = false;
  }
}

function onCloseRequirement() {
  if (!req.value) return;
  dialog.warning({
    title: '关闭需求',
    content: `确定关闭「${req.value.title}」？关闭后工作流将冻结，可稍后重新打开。`,
    positiveText: '关闭',
    negativeText: '取消',
    onPositiveClick: async () => {
      closeSaving.value = true;
      try {
        const { data } = await closeRequirement(req.value!.id);
        req.value = data;
        clearNodeSelection();
        const { data: acts } = await listRequirementActivities(req.value.id);
        activities.value = acts;
        message.success('需求已关闭');
        emit('updated', data);
      } catch (e: unknown) {
        const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
        message.error(typeof detail === 'string' ? detail : '关闭失败');
      } finally {
        closeSaving.value = false;
      }
    },
  });
}

async function onReopenClosed() {
  if (!req.value) return;
  nodeSaving.value = true;
  try {
    const { data } = await reopenClosedRequirement(req.value.id);
    req.value = data;
    const { data: acts } = await listRequirementActivities(req.value.id);
    activities.value = acts;
    message.success('已重新打开');
    emit('updated', data);
  } catch (e: unknown) {
    const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
    message.error(typeof detail === 'string' ? detail : '操作失败');
  } finally {
    nodeSaving.value = false;
  }
}

async function submitComment() {
  if (!req.value || !newComment.value.trim()) return;
  commentSaving.value = true;
  try {
    const { data } = await createRequirementComment(req.value.id, newComment.value.trim());
    comments.value = [...comments.value, data];
    newComment.value = '';
    const { data: acts } = await listRequirementActivities(req.value.id);
    activities.value = acts;
    message.success('评论已发表');
  } finally {
    commentSaving.value = false;
  }
}

watch(() => props.requirementId, () => {
  editMode.value = false;
  selectedNodeKey.value = null;
  newComment.value = '';
  void load();
}, { immediate: true });
</script>

<style scoped>
.panel-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 240px;
}
.requirement-detail-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.header-block {
  position: sticky;
  top: 0;
  z-index: 2;
  background: var(--n-color);
  border-bottom: 1px solid var(--n-divider-color);
}
.panel-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
}
.panel-title-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  padding: 0 16px 12px;
}
.panel-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: auto;
  padding: 12px 16px 24px;
}
.panel-body--edit {
  padding: 8px 12px 16px;
}
.workflow-block {
  padding: 12px;
  border-radius: 8px;
  background: var(--n-color-modal);
}
.tabs-block {
  flex: 1;
  min-height: 200px;
  margin-top: 16px;
  overflow: auto;
}
.field-block {
  margin-top: 8px;
  min-width: 0;
  overflow: hidden;
}
.section-label {
  display: block;
  margin: 16px 0 8px;
  font-size: 13px;
}
.empty-roles-hint {
  display: block;
  margin-top: 8px;
  font-size: 13px;
}
.people-fields {
  padding-top: 4px;
  border-top: 1px solid var(--n-divider-color);
}
.people-fields .field-pair {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px 24px;
}
.people-fields .field-cell {
  display: grid;
  grid-template-columns: 100px minmax(0, 1fr);
  gap: 8px 12px;
  align-items: start;
  min-width: 0;
}
.people-fields .field-label {
  font-size: 13px;
  color: var(--n-text-color-3);
  line-height: 1.5;
}
.people-fields .field-value {
  font-size: 14px;
  line-height: 1.5;
  word-break: break-word;
  min-width: 0;
}
.status-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
  padding: 8px 12px;
  border-radius: 6px;
}
.closed-banner {
  background: var(--n-color-modal);
  border: 1px solid var(--n-border-color);
}
.comment-item {
  padding: 8px 0;
  border-bottom: 1px solid var(--n-divider-color);
}
.comment-time {
  font-size: 12px;
  margin-left: 8px;
}
.comment-body {
  margin-top: 4px;
}
</style>
