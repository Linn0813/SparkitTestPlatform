<template>
  <n-form label-placement="top" class="requirement-create-form">
    <n-form-item label="需求标题" required>
      <n-input v-model:value="form.title" placeholder="需求标题" />
    </n-form-item>
    <n-grid :cols="2" :x-gap="12">
      <n-gi>
        <n-form-item label="优先级">
          <n-select v-model:value="form.priority" :options="prioritySelectOptions" />
        </n-form-item>
      </n-gi>
      <n-gi>
        <n-form-item label="需求类型">
          <n-select v-model:value="form.req_type" :options="typeSelectOptions" />
        </n-form-item>
      </n-gi>
    </n-grid>
    <n-form-item label="PRD 链接">
      <n-input v-model:value="form.external_url" placeholder="可选，粘贴禅道/Jira/PRD 链接" />
    </n-form-item>
    <n-form-item label="关联版本">
      <VersionSelect v-model="form.version_id" :project-id="projectId" />
    </n-form-item>

    <DynamicFieldForm
      v-if="templateUiFields.length"
      v-model="customFields"
      :fields="templateUiFields"
      :project-id="projectId"
      title="扩展字段"
      :columns="2"
      compact
    />

    <template v-if="showWorkflow">
      <div class="workflow-section">
        <n-text depth="3" class="section-label">角色</n-text>
        <n-text depth="3" class="section-hint">勾选本需求涉及的角色，用于筛选可执行的工作流节点</n-text>
        <n-space :size="6" wrap class="section-tags">
          <n-tag
            v-for="role in projectConfig.roles.value"
            :key="role.role_key"
            checkable
            size="small"
            :checked="selectedRoles.includes(role.role_key)"
            @update:checked="(v: boolean) => onToggleRole(role.role_key, v)"
          >
            {{ role.label }}
          </n-tag>
        </n-space>
      </div>

      <div v-if="createNodeOptions.length" class="workflow-section">
        <n-text depth="3" class="section-label">工作流节点</n-text>
        <n-text depth="3" class="section-hint">勾选本需求要执行的节点，未勾选将跳过</n-text>
        <n-space :size="6" wrap class="section-tags">
          <n-tag
            v-for="node in createNodeOptions"
            :key="node.node_key"
            checkable
            size="small"
            :checked="createEnabledDraft[node.node_key] ?? defaultNodeEnabled(node.node_key)"
            @update:checked="(v: boolean) => onToggleNode(node.node_key, v)"
          >
            {{ node.label }}
          </n-tag>
        </n-space>
      </div>

      <div v-if="activeWorkflowRoles.length" class="workflow-section">
        <n-text depth="3" class="section-label">相关人员</n-text>
        <n-grid :cols="2" :x-gap="12">
          <n-gi v-for="role in activeWorkflowRoles" :key="role.key">
            <n-form-item :label="role.label">
              <n-select
                v-model:value="roleUserIds[role.key]"
                :options="memberOptions"
                multiple
                filterable
                clearable
                placeholder="选择负责人"
              />
            </n-form-item>
          </n-gi>
        </n-grid>
      </div>
      <n-text v-else-if="workflowDefs.length" depth="3" class="empty-hint">
        请至少启用一个工作流节点后再配置相关人员
      </n-text>
    </template>
  </n-form>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { NForm, NFormItem, NGi, NGrid, NInput, NSelect, NSpace, NTag, NText } from 'naive-ui';
import { listRequirementWorkflowNodes } from '@/api/requirementWorkflow';
import DynamicFieldForm from '@/components/DynamicFieldForm.vue';
import VersionSelect from '@/components/VersionSelect.vue';
import { defaultWorkflowNodeEnabled } from '@/constants/requirementNodes';
import { mergeCustomFields, validateCustomFields } from '@/constants/fieldTypes';
import { useProjectFieldSchema } from '@/composables/useProjectFieldSchema';
import { useProjectMemberOptions } from '@/composables/useProjectMemberOptions';
import { useRequirementProjectConfig } from '@/composables/useRequirementProjectConfig';
import type { RequirementPriority, RequirementType, RequirementWorkflowNodeDef } from '@/types/business';

export interface RequirementCreatePayload {
  title: string;
  external_url: string | null;
  version_id: string | null;
  priority: RequirementPriority;
  req_type: RequirementType;
  custom_fields: Record<string, unknown>;
  role_assignee_ids: Record<string, string[]>;
  enabled: Record<string, boolean>;
}

const props = withDefaults(
  defineProps<{
    projectId: string | null;
    showWorkflow?: boolean;
  }>(),
  { showWorkflow: true }
);

const projectConfig = useRequirementProjectConfig(() => props.projectId);
const fieldSchema = useProjectFieldSchema('requirement', computed(() => props.projectId));
const { options: memberOptions } = useProjectMemberOptions(computed(() => props.projectId));

const templateUiFields = computed(() => fieldSchema.templateFieldsForUi.value);

const prioritySelectOptions = computed(() =>
  projectConfig.priorityOptions.value.map((o) => ({ label: o.label, value: o.option_key }))
);
const typeSelectOptions = computed(() =>
  projectConfig.typeOptions.value.map((o) => ({ label: o.label, value: o.option_key }))
);

const form = ref({
  title: '',
  external_url: '',
  version_id: null as string | null,
  priority: 'p1' as RequirementPriority,
  req_type: 'feature' as RequirementType,
});

const customFields = ref<Record<string, unknown>>({});
const workflowDefs = ref<RequirementWorkflowNodeDef[]>([]);
const selectedRoles = ref<string[]>([]);
const createEnabledDraft = ref<Record<string, boolean>>({});
const roleUserIds = ref<Record<string, string[]>>({});

const createNodeOptions = computed(() => {
  const roleSet = new Set(selectedRoles.value);
  return workflowDefs.value.filter((n) => n.role_keys.some((rk) => roleSet.has(rk)));
});

const activeWorkflowRoles = computed(() => {
  const keys = new Set<string>();
  for (const node of workflowDefs.value) {
    const enabled = createEnabledDraft.value[node.node_key] ?? defaultNodeEnabled(node.node_key);
    if (!enabled) continue;
    for (const rk of node.role_keys) {
      if (selectedRoles.value.includes(rk)) keys.add(rk);
    }
  }
  return projectConfig.roles.value
    .filter((r) => keys.has(r.role_key))
    .map((r) => ({ key: r.role_key, label: r.label }));
});

function defaultNodeEnabled(nodeKey: string): boolean {
  return defaultWorkflowNodeEnabled(nodeKey, form.value.req_type);
}

function syncCreateEnabledDraft() {
  const map: Record<string, boolean> = {};
  for (const d of workflowDefs.value) {
    const prev = createEnabledDraft.value[d.node_key];
    map[d.node_key] = prev !== undefined ? prev : defaultNodeEnabled(d.node_key);
  }
  createEnabledDraft.value = map;
}

function syncSelectedRoles() {
  if (!selectedRoles.value.length && projectConfig.roles.value.length) {
    selectedRoles.value = projectConfig.roles.value.map((r) => r.role_key);
  }
}

function pruneNodesWithoutRoles() {
  const roleSet = new Set(selectedRoles.value);
  const next = { ...createEnabledDraft.value };
  for (const node of workflowDefs.value) {
    if (!node.role_keys.some((rk) => roleSet.has(rk))) {
      next[node.node_key] = false;
    }
  }
  createEnabledDraft.value = next;
}

function onToggleRole(roleKey: string, checked: boolean) {
  if (checked) {
    if (!selectedRoles.value.includes(roleKey)) {
      selectedRoles.value = [...selectedRoles.value, roleKey];
    }
  } else {
    selectedRoles.value = selectedRoles.value.filter((k) => k !== roleKey);
    pruneNodesWithoutRoles();
  }
}

function onToggleNode(nodeKey: string, enabled: boolean) {
  createEnabledDraft.value = { ...createEnabledDraft.value, [nodeKey]: enabled };
}

async function loadWorkflowDefs() {
  if (!props.projectId || !props.showWorkflow) {
    workflowDefs.value = [];
    createEnabledDraft.value = {};
    return;
  }
  const { data } = await listRequirementWorkflowNodes(props.projectId);
  workflowDefs.value = data;
  syncCreateEnabledDraft();
  pruneNodesWithoutRoles();
}

function reset() {
  form.value = {
    title: '',
    external_url: '',
    version_id: null,
    priority: 'p1',
    req_type: 'feature',
  };
  customFields.value = mergeCustomFields(fieldSchema.templateFieldsForUi.value, {});
  selectedRoles.value = projectConfig.roles.value.map((r) => r.role_key);
  roleUserIds.value = {};
  syncCreateEnabledDraft();
  pruneNodesWithoutRoles();
}

function validate(): string | null {
  if (!form.value.title.trim()) return '请填写标题';
  return validateCustomFields(fieldSchema.templateFieldsForUi.value, customFields.value);
}

function getPayload(): RequirementCreatePayload {
  const enabled: Record<string, boolean> = {};
  for (const d of workflowDefs.value) {
    enabled[d.node_key] = createEnabledDraft.value[d.node_key] ?? defaultNodeEnabled(d.node_key);
  }
  const assignees: Record<string, string[]> = {};
  for (const role of activeWorkflowRoles.value) {
    assignees[role.key] = roleUserIds.value[role.key] ?? [];
  }
  return {
    title: form.value.title.trim(),
    external_url: form.value.external_url.trim() || null,
    version_id: form.value.version_id,
    priority: form.value.priority,
    req_type: form.value.req_type,
    custom_fields: { ...customFields.value },
    role_assignee_ids: assignees,
    enabled,
  };
}

async function prepare() {
  await Promise.all([projectConfig.reload(), fieldSchema.reload()]);
  customFields.value = mergeCustomFields(fieldSchema.templateFieldsForUi.value, {});
  syncSelectedRoles();
  await loadWorkflowDefs();
}

watch(
  () => form.value.req_type,
  () => {
    if (workflowDefs.value.length) syncCreateEnabledDraft();
  }
);

watch(
  () => props.projectId,
  () => {
    void prepare();
  }
);

defineExpose({ reset, validate, getPayload, prepare });
</script>

<style scoped>
.workflow-section {
  margin-top: 16px;
}

.section-label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 4px;
}

.section-hint {
  display: block;
  font-size: 12px;
  margin-bottom: 8px;
}

.section-tags {
  margin-bottom: 4px;
}

.empty-hint {
  display: block;
  margin-top: 12px;
  font-size: 12px;
}
</style>
