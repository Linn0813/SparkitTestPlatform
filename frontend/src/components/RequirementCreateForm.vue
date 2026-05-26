<template>
  <RequirementFormEditor
    v-if="projectId"
    :project-id="projectId"
    v-model:form="form"
    v-model:custom-fields="customFields"
    v-model:selected-roles="selectedRoles"
    v-model:enabled-draft="createEnabledDraft"
    :workflow-nodes="workflowNodeSources"
    :show-workflow="showWorkflow"
    title-placeholder="需求标题"
  />
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { listRequirementWorkflowNodes } from '@/api/requirementWorkflow';
import RequirementFormEditor, { type RequirementFormModel } from '@/components/RequirementFormEditor.vue';
import { defaultWorkflowNodeEnabled } from '@/constants/requirementNodes';
import { mergeCustomFields, validateCustomFields } from '@/constants/fieldTypes';
import { useProjectFieldSchema } from '@/composables/useProjectFieldSchema';
import { useRequirementProjectConfig } from '@/composables/useRequirementProjectConfig';
import type { RequirementPriority, RequirementType, RequirementWorkflowNodeDef } from '@/types/business';
import type { WorkflowNodeSource } from '@/utils/requirementWorkflowLayout';

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

const form = ref<RequirementFormModel>({
  title: '',
  external_url: '',
  version_id: null,
  priority: 'p1',
  req_type: 'feature',
  roleUserIds: {},
});

const customFields = ref<Record<string, unknown>>({});
const workflowDefs = ref<RequirementWorkflowNodeDef[]>([]);
const selectedRoles = ref<string[]>([]);
const createEnabledDraft = ref<Record<string, boolean>>({});

function defaultNodeEnabled(nodeKey: string): boolean {
  return defaultWorkflowNodeEnabled(nodeKey, form.value.req_type);
}

function defToSource(d: RequirementWorkflowNodeDef): WorkflowNodeSource {
  const enabled = createEnabledDraft.value[d.node_key] ?? defaultNodeEnabled(d.node_key);
  return {
    node_key: d.node_key,
    label: d.label,
    role_keys: d.role_keys,
    lane_index: d.lane_index,
    lane_indexes: d.lane_indexes,
    blocks_lane_gate: d.blocks_lane_gate,
    sort_in_lane: d.sort_in_lane,
    enabled,
    state: 'pending',
  };
}

const workflowNodeSources = computed(() => workflowDefs.value.map(defToSource));

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
    .map((r) => r.role_key);
});

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

async function loadWorkflowDefs() {
  if (!props.projectId || !props.showWorkflow) {
    workflowDefs.value = [];
    createEnabledDraft.value = {};
    return;
  }
  const { data } = await listRequirementWorkflowNodes(props.projectId);
  workflowDefs.value = data;
  syncCreateEnabledDraft();
}

function reset() {
  form.value = {
    title: '',
    external_url: '',
    version_id: null,
    priority: 'p1',
    req_type: 'feature',
    roleUserIds: {},
  };
  customFields.value = mergeCustomFields(fieldSchema.templateFieldsForUi.value, {});
  selectedRoles.value = projectConfig.roles.value.map((r) => r.role_key);
  syncCreateEnabledDraft();
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
  for (const roleKey of activeWorkflowRoles.value) {
    assignees[roleKey] = form.value.roleUserIds[roleKey] ?? [];
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
