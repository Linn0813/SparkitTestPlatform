<template>
  <div class="node-detail-panel">
    <div class="node-detail-header">
      <div class="node-detail-title-row">
        <span class="status-dot" :class="nodeStateDotClass(node.state, node.enabled)" />
        <n-text strong>{{ node.label }}</n-text>
        <n-tag size="small" round :bordered="false">{{ nodeStateLabel(node.state) }}</n-tag>
        <span class="node-meta-divider" aria-hidden="true" />
        <div class="node-meta-item">
          <n-text depth="3" class="meta-label">负责人</n-text>
          <n-space v-if="assigneeLabels.length" :size="4" class="meta-value">
            <n-tag v-for="(name, i) in assigneeLabels" :key="i" size="small" round :bordered="false">
              {{ name }}
            </n-tag>
          </n-space>
          <n-text v-else depth="3" class="meta-value">—</n-text>
        </div>
        <span class="node-meta-divider" aria-hidden="true" />
        <div class="node-meta-item">
          <n-text depth="3" class="meta-label">节点排期</n-text>
          <n-text class="meta-value meta-value--schedule">{{ nodeScheduleLabel }}</n-text>
        </div>
      </div>
      <n-space v-if="actionButtons.length || gateHint" :size="4" class="node-detail-actions" align="center">
        <n-text v-if="gateHint" depth="3" class="gate-hint">{{ gateHint }}</n-text>
        <n-button
          v-for="act in actionButtons"
          :key="act.action"
          size="small"
          :type="act.type"
          :loading="loading"
          @click="emit('node-action', node.node_key, act.action)"
        >
          {{ act.label }}
        </n-button>
      </n-space>
    </div>

    <div class="node-detail-body">
      <div class="task-table-section">
        <div
          class="task-grid"
          :class="isTaskEditable ? 'task-grid--editable' : 'task-grid--readonly'"
        >
          <div class="task-grid-head">
            <span>任务</span>
            <span>负责人</span>
            <span>估分（人天）</span>
            <span>排期</span>
            <span v-if="isTaskEditable" class="task-grid-col-actions">操作</span>
          </div>

          <div
            v-for="task in nodeTasks"
            :key="task.id"
            class="task-grid-row"
            :class="{ 'task-grid-row--saving': isTaskSaving(task.id) }"
          >
            <div class="task-grid-cell">
              <n-input
                v-if="isTaskEditable"
                class="task-field"
                :value="titleDrafts[task.id] ?? task.title"
                size="small"
                :disabled="isTaskSaving(task.id)"
                @update:value="(v: string) => (titleDrafts[task.id] = v)"
                @blur="() => onTitleBlur(task)"
              />
              <span v-else class="task-cell-text">{{ task.title }}</span>
            </div>
            <div class="task-grid-cell">
              <n-select
                v-if="isTaskEditable"
                class="task-field"
                :value="effectiveAssigneeId(task)"
                :options="memberOptions"
                size="small"
                filterable
                clearable
                placeholder="选择负责人"
                :disabled="isTaskSaving(task.id)"
                @update:value="(v: string | null) => onTaskFieldChange(task, { assignee_id: v })"
              />
              <span v-else class="task-cell-text">{{ assigneeLabel(task) }}</span>
            </div>
            <div class="task-grid-cell task-grid-cell--estimate">
              <n-input-number
                v-if="isTaskEditable"
                class="task-field task-field--estimate"
                :value="estimateDrafts[task.id] ?? task.estimate_points"
                size="small"
                :min="0"
                :show-button="false"
                clearable
                placeholder="—"
                :disabled="isTaskSaving(task.id)"
                @update:value="(v: number | null) => onEstimateInput(task.id, v)"
                @blur="() => onEstimateBlur(task)"
              />
              <span v-else class="task-cell-text">{{ task.estimate_points ?? '—' }}</span>
            </div>
            <div class="task-grid-cell">
              <n-date-picker
                v-if="isTaskEditable"
                class="task-field"
                :formatted-value="taskScheduleRange(task)"
                type="daterange"
                size="small"
                value-format="yyyy-MM-dd"
                clearable
                :disabled="isTaskSaving(task.id)"
                @update:formatted-value="(v: [string, string] | null) => onScheduleChange(task, v)"
              />
              <span v-else class="task-cell-text task-cell-text--schedule">{{ taskScheduleLabel(task) }}</span>
            </div>
            <div v-if="isTaskEditable" class="task-grid-cell task-grid-col-actions">
              <n-button
                quaternary
                size="tiny"
                type="error"
                :disabled="isTaskSaving(task.id)"
                @click="onDeleteTask(task)"
              >
                删除
              </n-button>
            </div>
          </div>

          <div v-if="!nodeTasks.length" class="task-empty">暂无任务</div>
        </div>

        <n-button
          v-if="isTaskEditable"
          quaternary
          size="small"
          class="add-task-btn"
          :loading="addingTask"
          @click="onAddTask"
        >
          + 添加任务
        </n-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import {
  NButton,
  NDatePicker,
  NInput,
  NInputNumber,
  NSelect,
  NSpace,
  NTag,
  NText,
  useMessage,
} from 'naive-ui';
import {
  createRequirementNodeTask,
  deleteRequirementNodeTask,
  updateRequirementNodeTask,
} from '@/api/requirementNodeTasks';
import type { RequirementNodeAction } from '@/api/requirements';
import type {
  Requirement,
  RequirementNodeProgress,
  RequirementNodeTask,
  RequirementType,
} from '@/types/business';
import { gateBlockedReason, isNodeActionable } from '@/utils/requirementNodeGate';
import { nodeStateDotClass, nodeStateLabel } from '@/utils/requirementWorkflowLayout';

const props = defineProps<{
  requirement: Requirement;
  node: RequirementNodeProgress;
  nodeTasks: RequirementNodeTask[];
  memberOptions: { label: string; value: string }[];
  canEdit?: boolean;
  rejected?: boolean;
  reqType?: RequirementType;
  loading?: boolean;
}>();

const emit = defineEmits<{
  'node-action': [nodeKey: string, action: RequirementNodeAction];
  'tasks-updated': [requirement: Requirement];
}>();

const message = useMessage();
const savingTaskIds = ref<Set<string>>(new Set());
const addingTask = ref(false);
const titleDrafts = ref<Record<string, string>>({});
const estimateDrafts = ref<Record<string, number | null>>({});

const isTaskEditable = computed(() => Boolean(props.canEdit && !props.rejected && props.node.enabled));

const assigneeLabels = computed(() => {
  const labels: string[] = [];
  const seenIds = new Set<string>();

  for (const task of props.nodeTasks) {
    if (!task.assignee_id || seenIds.has(task.assignee_id)) continue;
    seenIds.add(task.assignee_id);
    const label = assigneeLabel(task);
    if (label !== '—') labels.push(label);
  }

  for (const roleKey of props.node.role_keys) {
    const ids = props.requirement.role_assignee_ids?.[roleKey];
    if (ids?.length) {
      for (const id of ids) {
        if (seenIds.has(id)) continue;
        seenIds.add(id);
        const opt = props.memberOptions.find((o) => o.value === id);
        labels.push(opt?.label ?? id);
      }
      continue;
    }
    const legacyUser = legacyRoleUser(roleKey);
    if (legacyUser?.id && !seenIds.has(legacyUser.id)) {
      seenIds.add(legacyUser.id);
      labels.push(legacyUser.name?.trim() || legacyUser.id);
    }
  }

  return labels;
});

const nodeScheduleLabel = computed(() => {
  const start = formatDate(props.node.planned_schedule_start ?? null);
  const end = formatDate(props.node.planned_schedule_end ?? null);
  if (start === '—' && end === '—') return '—';
  return `${start} ~ ${end}`;
});

const workflowNodes = computed(() => props.requirement.nodes ?? []);

const gateHint = computed(() => {
  if (!props.canEdit || props.rejected || !props.node.enabled) return null;
  if (props.node.state !== 'pending') return null;
  return gateBlockedReason(workflowNodes.value, props.node.node_key);
});

const actionButtons = computed((): {
  action: RequirementNodeAction;
  label: string;
  type?: 'primary' | 'error' | 'default';
}[] => {
  if (!props.canEdit || props.rejected || !props.node.enabled) return [];
  const node = props.node;
  const nodes = workflowNodes.value;
  const list: { action: RequirementNodeAction; label: string; type?: 'primary' | 'error' | 'default' }[] = [];

  if (node.state === 'pending' || node.state === 'in_progress') {
    if (isNodeActionable(nodes, node)) {
      list.push({ action: 'complete', label: '完成', type: 'primary' });
      if (node.node_key === 'req_review') {
        list.push({ action: 'reject', label: '不通过', type: 'error' });
      }
    }
  } else if (node.state === 'completed' || node.state === 'skipped') {
    list.push({ action: 'reopen', label: '重开' });
  }
  return list;
});

function legacyRoleUser(roleKey: string): { id: string; name?: string; email?: string } | null {
  const map: Record<string, { id: string; name?: string; email?: string } | null | undefined> = {
    frontend_rd: props.requirement.frontend_rd,
    backend_rd: props.requirement.backend_rd,
    pm: props.requirement.pm,
    tech_owner: props.requirement.tech_owner,
    qa: props.requirement.qa,
    designer: props.requirement.designer,
  };
  const u = map[roleKey];
  return u?.id ? u : null;
}

function effectiveAssigneeId(task: RequirementNodeTask): string | null {
  if (task.assignee_id) return task.assignee_id;
  const ids = props.requirement.role_assignee_ids?.[task.role_key];
  if (ids?.[0]) return ids[0];
  return legacyRoleUser(task.role_key)?.id ?? null;
}

function assigneeLabel(task: RequirementNodeTask): string {
  const u = task.assignee;
  if (u?.name?.trim()) return u.name.trim();
  const effectiveId = effectiveAssigneeId(task);
  if (effectiveId) {
    const opt = props.memberOptions.find((o) => o.value === effectiveId);
    return opt?.label ?? effectiveId;
  }
  return '—';
}

function formatDate(iso: string | null): string {
  if (!iso) return '—';
  return iso.slice(0, 10);
}

function taskScheduleRange(task: RequirementNodeTask): [string, string] | null {
  if (task.scheduled_start && task.scheduled_end) {
    return [task.scheduled_start.slice(0, 10), task.scheduled_end.slice(0, 10)];
  }
  return null;
}

function taskScheduleLabel(task: RequirementNodeTask): string {
  const start = formatDate(task.scheduled_start);
  const end = formatDate(task.scheduled_end);
  if (start === '—' && end === '—') return '—';
  return `${start} ~ ${end}`;
}

function isTaskSaving(taskId: string): boolean {
  return savingTaskIds.value.has(taskId);
}

function markTaskSaving(taskId: string, saving: boolean) {
  const next = new Set(savingTaskIds.value);
  if (saving) next.add(taskId);
  else next.delete(taskId);
  savingTaskIds.value = next;
}

async function onTitleBlur(task: RequirementNodeTask) {
  const draft = titleDrafts.value[task.id];
  if (draft === undefined || draft === task.title) {
    delete titleDrafts.value[task.id];
    return;
  }
  await onTaskFieldChange(task, { title: draft });
  delete titleDrafts.value[task.id];
}

function onEstimateInput(taskId: string, value: number | null) {
  estimateDrafts.value[taskId] = value;
}

async function onEstimateBlur(task: RequirementNodeTask) {
  if (!(task.id in estimateDrafts.value)) return;
  const draft = estimateDrafts.value[task.id];
  delete estimateDrafts.value[task.id];
  const current = task.estimate_points ?? null;
  if (draft === current) return;
  await onTaskFieldChange(task, { estimate_points: draft });
}

async function onTaskFieldChange(
  task: RequirementNodeTask,
  patch: {
    title?: string;
    assignee_id?: string | null;
    role_key?: string;
    estimate_points?: number | null;
    scheduled_start?: string | null;
    scheduled_end?: string | null;
  }
) {
  markTaskSaving(task.id, true);
  try {
    const { data } = await updateRequirementNodeTask(
      props.requirement.id,
      props.node.node_key,
      task.id,
      patch
    );
    emit('tasks-updated', data);
  } catch (e: unknown) {
    message.error((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? '保存失败');
  } finally {
    markTaskSaving(task.id, false);
  }
}

async function onScheduleChange(task: RequirementNodeTask, range: [string, string] | null) {
  await onTaskFieldChange(task, {
    scheduled_start: range?.[0] ?? null,
    scheduled_end: range?.[1] ?? null,
  });
}

async function onAddTask() {
  const defaultRole = props.node.role_keys[0];
  if (!defaultRole) {
    message.warning('该节点未配置角色');
    return;
  }
  addingTask.value = true;
  try {
    const { data } = await createRequirementNodeTask(props.requirement.id, props.node.node_key, {
      title: props.node.label,
      role_key: defaultRole,
    });
    emit('tasks-updated', data);
  } catch (e: unknown) {
    message.error((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? '添加失败');
  } finally {
    addingTask.value = false;
  }
}

async function onDeleteTask(task: RequirementNodeTask) {
  markTaskSaving(task.id, true);
  try {
    const { data } = await deleteRequirementNodeTask(
      props.requirement.id,
      props.node.node_key,
      task.id
    );
    emit('tasks-updated', data);
  } catch (e: unknown) {
    message.error((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? '删除失败');
  } finally {
    markTaskSaving(task.id, false);
  }
}
</script>

<style scoped>
.node-detail-panel {
  margin-top: 12px;
  padding: 12px 16px;
  border: 1px solid var(--n-border-color);
  border-radius: 8px;
  background: var(--n-color);
}

.node-detail-header {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px 12px;
}

.node-detail-title-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px 12px;
  min-width: 0;
  flex: 1;
}

.node-detail-actions {
  flex-shrink: 0;
  margin-left: auto;
}

.gate-hint {
  font-size: 12px;
  white-space: nowrap;
}

.node-meta-item {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.node-meta-divider {
  width: 1px;
  height: 14px;
  background: var(--n-divider-color);
  flex-shrink: 0;
}

.meta-label {
  flex-shrink: 0;
  font-size: 12px;
}

.meta-value {
  min-width: 0;
}

.meta-value--schedule {
  font-variant-numeric: tabular-nums;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot-pending { background: #aeaeb2; }
.dot-active { background: #ffa200; }
.dot-done { background: #00c261; }
.dot-disabled { background: #dcdcdc; }

.task-table-section {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: 6px;
  background: var(--n-color-modal);
}

.add-task-btn {
  margin-top: 8px;
}

.task-grid {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.task-grid--editable .task-grid-head,
.task-grid--editable .task-grid-row {
  grid-template-columns:
    minmax(96px, 1.2fr)
    minmax(120px, 1.5fr)
    minmax(72px, 88px)
    minmax(168px, 1.6fr)
    44px;
}

.task-grid--readonly .task-grid-head,
.task-grid--readonly .task-grid-row {
  grid-template-columns:
    minmax(96px, 1.2fr)
    minmax(120px, 1.5fr)
    minmax(72px, 88px)
    minmax(168px, 1.6fr);
}

.task-grid-head,
.task-grid-row {
  display: grid;
  column-gap: 8px;
  align-items: center;
}

.task-grid-head {
  padding-bottom: 6px;
  border-bottom: 1px solid var(--n-divider-color);
  font-size: 12px;
  color: var(--n-text-color-3);
}

.task-grid-row {
  padding: 4px 0;
  border-radius: 4px;
  transition: background 0.15s ease;
}

.task-grid-row:hover {
  background: var(--n-color-hover);
}

.task-grid-row--saving {
  opacity: 0.65;
  pointer-events: none;
}

.task-grid-cell {
  min-width: 0;
}

.task-grid-col-actions {
  display: flex;
  justify-content: center;
}

.task-cell-text {
  display: block;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-cell-text--schedule {
  font-variant-numeric: tabular-nums;
}

.task-field {
  width: 100%;
  min-width: 0;
}

.task-field--estimate :deep(.n-input__input-el) {
  text-align: center;
}

.task-empty {
  padding: 16px 0;
  text-align: center;
  font-size: 13px;
  color: var(--n-text-color-3);
}
</style>
