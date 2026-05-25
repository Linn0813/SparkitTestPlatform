<template>
  <div class="node-detail-panel">
    <div class="node-detail-header">
      <span class="status-dot" :class="nodeStateDotClass(node.state, node.enabled)" />
      <div class="node-detail-title">
        <n-text strong>{{ node.label }}</n-text>
        <n-tag size="small" round :bordered="false">{{ nodeStateLabel(node.state) }}</n-tag>
      </div>
      <div class="node-meta-inline">
        <n-text depth="3" class="meta-label">负责人</n-text>
        <n-space v-if="assigneeLabels.length" :size="4">
          <n-tag v-for="(name, i) in assigneeLabels" :key="i" size="small" round :bordered="false">
            {{ name }}
          </n-tag>
        </n-space>
        <n-text v-else depth="3">—</n-text>
      </div>
      <div class="node-meta-inline">
        <n-text depth="3" class="meta-label">节点排期</n-text>
        <n-text>{{ nodeScheduleLabel }}</n-text>
      </div>
      <n-space v-if="actionButtons.length" :size="4" class="node-detail-actions">
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
        <n-text depth="3" class="section-label">任务</n-text>
        <n-table :bordered="true" :single-line="false" size="small">
          <thead>
            <tr>
              <th>任务</th>
              <th>负责人</th>
              <th>估分</th>
              <th>排期</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="taskRows.length">
              <td v-for="(cell, i) in taskRows[0]" :key="i">{{ cell }}</td>
            </tr>
            <tr v-else>
              <td colspan="4" class="task-empty">暂无任务</td>
            </tr>
          </tbody>
        </n-table>
        <n-text v-if="canEdit" depth="3" class="edit-hint">
          负责人按节点角色取自需求「相关人员」（{{ roleHint }}）。
          <n-button text size="tiny" type="primary" @click="emit('edit-requirement')">编辑需求</n-button>
          修改；任务估分与排期暂未开放编辑，节点排期在完成节点后自动生成。
        </n-text>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue';
import { NButton, NSpace, NTable, NTag, NText } from 'naive-ui';
import { useRequirementProjectConfig } from '@/composables/useRequirementProjectConfig';
import type { RequirementNodeAction } from '@/api/requirements';
import type { Requirement, RequirementNodeProgress, RequirementType } from '@/types/business';
import { nodeStateDotClass, nodeStateLabel } from '@/utils/requirementWorkflowLayout';

const props = defineProps<{
  requirement: Requirement;
  node: RequirementNodeProgress;
  canEdit?: boolean;
  rejected?: boolean;
  reqType?: RequirementType;
  loading?: boolean;
}>();

const projectConfig = useRequirementProjectConfig(() => props.requirement.project_id);
watch(() => props.requirement.project_id, () => projectConfig.reload(), { immediate: true });

const emit = defineEmits<{
  'node-action': [nodeKey: string, action: RequirementNodeAction];
  'edit-requirement': [];
}>();

const assigneeLabels = computed(() => {
  const names: string[] = [];
  const seen = new Set<string>();
  const map: Record<string, { name?: string; email?: string } | null | undefined> = {
    frontend_rd: props.requirement.frontend_rd,
    backend_rd: props.requirement.backend_rd,
    pm: props.requirement.pm,
    tech_owner: props.requirement.tech_owner,
    qa: props.requirement.qa,
    designer: props.requirement.designer,
  };
  for (const roleKey of props.node.role_keys) {
    const ids = props.requirement.role_assignee_ids?.[roleKey];
    if (ids?.length) {
      for (const id of ids) {
        const fromRole = Object.values(map).find((u) => u && 'id' in u && (u as { id: string }).id === id);
        const label = fromRole?.name?.trim() || fromRole?.email;
        if (label && !seen.has(label)) {
          seen.add(label);
          names.push(label);
        }
      }
    }
    const u = map[roleKey];
    const label = u?.name?.trim() || u?.email;
    if (label && !seen.has(label)) {
      seen.add(label);
      names.push(label);
    }
  }
  return names;
});

const roleHint = computed(() =>
  props.node.role_keys.map((key) => projectConfig.roleLabel(key)).join('、')
);

const assigneeText = computed(() => (assigneeLabels.value.length ? assigneeLabels.value.join('、') : '—'));

const nodeScheduleLabel = computed(() => {
  const start = formatDateTime(props.node.started_at);
  const end = formatDateTime(props.node.completed_at);
  if (start === '—' && end === '—') return '—';
  return `${start} ~ ${end}`;
});

const taskRows = computed(() => [[props.node.label, assigneeText.value, '—', '—']]);

const actionButtons = computed((): {
  action: RequirementNodeAction;
  label: string;
  type?: 'primary' | 'error' | 'default';
}[] => {
  if (!props.canEdit || props.rejected || !props.node.enabled) return [];
  const node = props.node;
  const list: { action: RequirementNodeAction; label: string; type?: 'primary' | 'error' | 'default' }[] = [];
  if (node.state === 'pending' || node.state === 'in_progress') {
    list.push({ action: 'complete', label: '完成', type: 'primary' });
    if (node.state === 'in_progress' && node.node_key === 'req_review') {
      list.push({ action: 'reject', label: '不通过', type: 'error' });
    }
  } else if (node.state === 'completed' || node.state === 'skipped') {
    list.push({ action: 'reopen', label: '重开' });
  }
  return list;
});

function formatDateTime(iso: string | null): string {
  if (!iso) return '—';
  return iso.replace('T', ' ').slice(0, 16);
}
</script>

<style scoped>
.node-detail-panel {
  margin-top: 12px;
  padding: 12px 16px;
  border: 1px solid var(--n-border-color);
  border-radius: 8px;
  background: var(--n-color);
  box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.04);
}
.node-detail-header {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px 20px;
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
.node-detail-title {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.node-meta-inline {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.meta-label {
  flex-shrink: 0;
  font-size: 12px;
}
.node-detail-actions {
  flex-shrink: 0;
  margin-left: auto;
}
.task-table-section {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--n-divider-color);
}
.section-label {
  display: block;
  font-size: 12px;
  margin-bottom: 6px;
}
.task-empty {
  text-align: center;
  color: var(--n-text-color-3);
}
.edit-hint {
  display: block;
  margin-top: 8px;
  font-size: 12px;
  line-height: 1.6;
}
</style>
