<template>
  <div class="edit-layout">
    <section class="edit-layout__form">
      <n-form
        label-placement="left"
        label-width="80"
        size="small"
        class="requirement-edit-form"
      >
        <n-form-item label="标题" required>
          <n-input
            :value="form.title"
            size="small"
            :placeholder="titlePlaceholder"
            @update:value="(v: string) => updateForm({ title: v })"
          />
        </n-form-item>
        <n-grid :cols="2" :x-gap="12" :y-gap="0">
          <n-gi>
            <n-form-item label="优先级">
              <n-space :size="4" wrap>
                <n-tag
                  v-for="opt in priorityTagOptions"
                  :key="opt.value"
                  checkable
                  size="small"
                  :checked="form.priority === opt.value"
                  @update:checked="(v: boolean) => v && updateForm({ priority: opt.value })"
                >
                  {{ opt.label }}
                </n-tag>
              </n-space>
            </n-form-item>
          </n-gi>
          <n-gi>
            <n-form-item label="需求类型">
              <n-space :size="4" wrap>
                <n-tag
                  v-for="opt in typeTagOptions"
                  :key="opt.value"
                  checkable
                  size="small"
                  :checked="form.req_type === opt.value"
                  @update:checked="(v: boolean) => v && updateForm({ req_type: opt.value })"
                >
                  {{ opt.label }}
                </n-tag>
              </n-space>
            </n-form-item>
          </n-gi>
          <n-gi :span="2">
            <n-form-item label="PRD 链接">
              <n-input
                :value="form.external_url"
                size="small"
                placeholder="可选"
                @update:value="(v: string) => updateForm({ external_url: v })"
              />
            </n-form-item>
          </n-gi>
          <n-gi :span="2">
            <n-form-item label="关联版本">
              <VersionSelect
                :model-value="form.version_id"
                :project-id="projectId"
                @update:model-value="(v: string | null) => updateForm({ version_id: v })"
              />
            </n-form-item>
          </n-gi>
        </n-grid>
        <template v-if="activeWorkflowRoles.length">
          <n-grid :cols="2" :x-gap="12" :y-gap="0">
            <n-gi v-for="role in activeWorkflowRoles" :key="role.key">
              <n-form-item :label="role.label">
                <n-select
                  :value="form.roleUserIds[role.key]"
                  :options="memberOptions"
                  multiple
                  filterable
                  clearable
                  size="small"
                  placeholder="选择负责人"
                  @update:value="(v: string[]) => setRoleUsers(role.key, v)"
                />
              </n-form-item>
            </n-gi>
          </n-grid>
        </template>
        <n-text v-else depth="3" class="empty-roles-hint">
          请先启用工作流节点，再配置相关人员
        </n-text>
        <DynamicFieldForm
          v-if="templateUiFields.length"
          :model-value="customFields"
          :fields="templateUiFields"
          :project-id="projectId"
          :columns="2"
          compact
          @update:model-value="emit('update:customFields', $event)"
        />
      </n-form>
    </section>
    <section v-if="showWorkflow" class="edit-layout__workflow">
      <div class="filter-block filter-block--compact">
        <div class="filter-row">
          <n-text depth="3" class="filter-label">角色</n-text>
          <n-space :size="6" wrap class="filter-tags">
            <n-tag
              v-for="role in projectRoleFields"
              :key="role.key"
              checkable
              size="small"
              :checked="selectedRoles.includes(role.key)"
              @update:checked="(v: boolean) => toggleRole(role.key, v)"
            >
              {{ role.label }}
            </n-tag>
          </n-space>
        </div>
        <div class="filter-row">
          <n-text depth="3" class="filter-label">节点</n-text>
          <n-space :size="6" wrap class="filter-tags">
            <n-tag
              v-for="node in workflowNodeOptions"
              :key="node.node_key"
              checkable
              size="small"
              :checked="isNodeEnabled(node.node_key)"
              @update:checked="(v: boolean) => onToggleEnabled(node.node_key, v)"
            >
              {{ node.label }}
            </n-tag>
          </n-space>
        </div>
      </div>
      <div class="workflow-block workflow-block--compact">
        <RequirementWorkflowCanvas
          mode="view"
          :nodes="workflowCanvasNodes"
          :req-type="form.req_type"
          :workflow-frozen="workflowFrozen"
          :selected-node-key="null"
        />
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue';
import { NForm, NFormItem, NGi, NGrid, NInput, NSelect, NSpace, NTag, NText } from 'naive-ui';
import DynamicFieldForm from '@/components/DynamicFieldForm.vue';
import RequirementWorkflowCanvas from '@/components/RequirementWorkflowCanvas.vue';
import VersionSelect from '@/components/VersionSelect.vue';
import { useProjectFieldSchema } from '@/composables/useProjectFieldSchema';
import { useProjectMemberOptions } from '@/composables/useProjectMemberOptions';
import { useRequirementProjectConfig } from '@/composables/useRequirementProjectConfig';
import type { RequirementNodeState, RequirementPriority, RequirementType } from '@/types/business';
import { syncEnabledDraftWithSelectedRoles } from '@/utils/requirementEditWorkflow';
import {
  expandWorkflowCanvasNodes,
  type WorkflowCanvasNode,
  type WorkflowNodeSource,
} from '@/utils/requirementWorkflowLayout';

export interface RequirementFormModel {
  title: string;
  external_url: string;
  version_id: string | null;
  priority: RequirementPriority;
  req_type: RequirementType;
  roleUserIds: Record<string, string[]>;
}

const props = withDefaults(
  defineProps<{
    projectId: string;
    form: RequirementFormModel;
    customFields: Record<string, unknown>;
    selectedRoles: string[];
    enabledDraft: Record<string, boolean>;
    workflowNodes: WorkflowNodeSource[];
    showWorkflow?: boolean;
    workflowFrozen?: boolean;
    titlePlaceholder?: string;
  }>(),
  {
    showWorkflow: true,
    workflowFrozen: false,
    titlePlaceholder: '',
  }
);

const emit = defineEmits<{
  'update:form': [RequirementFormModel];
  'update:customFields': [Record<string, unknown>];
  'update:selectedRoles': [string[]];
  'update:enabledDraft': [Record<string, boolean>];
}>();

const projectIdRef = computed(() => props.projectId);
const projectConfig = useRequirementProjectConfig(() => props.projectId);
const fieldSchema = useProjectFieldSchema('requirement', projectIdRef);
const { options: memberOptions } = useProjectMemberOptions(projectIdRef);

const templateUiFields = computed(() => fieldSchema.templateFieldsForUi.value);

const priorityTagOptions = computed(() =>
  projectConfig.priorityOptions.value.map((o) => ({ label: o.label, value: o.option_key }))
);
const typeTagOptions = computed(() =>
  projectConfig.typeOptions.value.map((o) => ({ label: o.label, value: o.option_key }))
);

const projectRoleFields = computed(() =>
  projectConfig.roles.value.map((r) => ({ key: r.role_key, label: r.label }))
);

watch(
  () => props.projectId,
  (pid) => {
    if (pid) void projectConfig.reload();
  },
  { immediate: true }
);

function updateForm(patch: Partial<RequirementFormModel>) {
  emit('update:form', { ...props.form, ...patch });
}

function setRoleUsers(roleKey: string, userIds: string[]) {
  emit('update:form', {
    ...props.form,
    roleUserIds: { ...props.form.roleUserIds, [roleKey]: userIds },
  });
}

function isNodeEnabled(nodeKey: string): boolean {
  const node = props.workflowNodes.find((n) => n.node_key === nodeKey);
  return props.enabledDraft[nodeKey] ?? node?.enabled ?? false;
}

/** 与后端 update_requirement_enabled_nodes 一致，用于编辑态画布预览 */
function previewNodeState(n: WorkflowNodeSource, enabled: boolean): RequirementNodeState {
  if (!enabled) return 'skipped';
  if (n.state === 'skipped') return 'pending';
  return n.state;
}

const workflowNodeOptions = computed(() => {
  const roleSet = new Set(props.selectedRoles);
  return props.workflowNodes.filter((n) => n.role_keys.some((rk) => roleSet.has(rk)));
});

const editCanvasNodes = computed<WorkflowCanvasNode[]>(() =>
  expandWorkflowCanvasNodes(
    props.workflowNodes.map((n) => {
      const enabled = props.enabledDraft[n.node_key] ?? n.enabled;
      return {
        ...n,
        enabled,
        state: previewNodeState(n, enabled),
      };
    })
  )
);

const workflowCanvasNodes = computed(() => {
  const roleSet = new Set(props.selectedRoles);
  return editCanvasNodes.value.filter((n) => n.role_keys.some((rk) => roleSet.has(rk)));
});

const activeWorkflowRoles = computed(() => {
  const roleSet = new Set(props.selectedRoles);
  const keys = new Set<string>();
  for (const node of props.workflowNodes) {
    const enabled = props.enabledDraft[node.node_key] ?? node.enabled;
    if (!enabled) continue;
    for (const rk of node.role_keys) {
      if (roleSet.has(rk)) keys.add(rk);
    }
  }
  return projectRoleFields.value.filter((r) => keys.has(r.key));
});

function toggleRole(roleKey: string, checked: boolean) {
  const nextRoles = checked
    ? [...new Set([...props.selectedRoles, roleKey])]
    : props.selectedRoles.filter((k) => k !== roleKey);
  const nextEnabled = syncEnabledDraftWithSelectedRoles(
    props.workflowNodes,
    nextRoles,
    props.enabledDraft
  );
  emit('update:selectedRoles', nextRoles);
  emit('update:enabledDraft', nextEnabled);
}

function onToggleEnabled(nodeKey: string, enabled: boolean) {
  emit('update:enabledDraft', { ...props.enabledDraft, [nodeKey]: enabled });
}
</script>

<style scoped>
.edit-layout {
  display: grid;
  grid-template-columns: minmax(300px, 1fr) minmax(260px, 1fr);
  gap: 12px;
  align-items: start;
}
@media (max-width: 960px) {
  .edit-layout {
    grid-template-columns: 1fr;
  }
}
.edit-layout__form {
  min-width: 0;
}
.edit-layout__workflow {
  min-width: 0;
}
.requirement-edit-form :deep(.n-form-item) {
  margin-bottom: 6px;
}
.filter-block {
  margin-bottom: 12px;
  padding: 8px 10px;
  border: 1px solid var(--n-border-color);
  border-radius: 8px;
  background: var(--n-color-modal);
}
.filter-block--compact {
  margin-bottom: 8px;
  padding: 6px 8px;
}
.filter-tags {
  flex: 1;
  min-width: 0;
}
.filter-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}
.filter-row + .filter-row {
  margin-top: 8px;
}
.filter-label {
  flex-shrink: 0;
  width: 36px;
  padding-top: 2px;
  font-size: 12px;
}
.workflow-block {
  padding: 12px;
  border-radius: 8px;
  background: var(--n-color-modal);
}
.workflow-block--compact {
  padding: 8px;
}
.empty-roles-hint {
  display: block;
  margin-top: 8px;
  font-size: 13px;
}
</style>
