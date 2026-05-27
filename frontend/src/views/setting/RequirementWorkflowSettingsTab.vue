<template>
  <div v-if="!projectId" class="wf-settings-empty">
    <n-text depth="3">请选择项目</n-text>
  </div>
  <div v-else class="wf-settings-root">
    <n-tabs v-model:value="sectionTab" type="line" class="wf-section-tabs">
      <n-tab-pane name="nodes" tab="工作流节点">
        <div class="wf-settings-layout">
          <div class="wf-settings-config">
            <n-space justify="space-between" align="center" style="margin-bottom: 8px">
              <n-text strong>节点列表</n-text>
              <n-button v-if="!readOnly" size="small" type="primary" @click="openCreate">添加节点</n-button>
            </n-space>
            <n-data-table size="small" :columns="columns" :data="defs" :loading="loading" />
          </div>
          <div class="wf-settings-preview">
            <n-text depth="3" class="preview-label">工作流预览</n-text>
            <RequirementWorkflowCanvas mode="preview" :nodes="previewNodes" />
          </div>
        </div>
      </n-tab-pane>
      <n-tab-pane name="status-rules" tab="状态与节点映射">
        <RequirementStatusRulesSettings :project-id="projectId" :workflow-nodes="defs" :read-only="readOnly" />
      </n-tab-pane>
    </n-tabs>

    <n-drawer v-model:show="showModal" :width="480" placement="right">
      <n-drawer-content :title="editing ? '编辑节点' : '添加节点'" closable>
        <n-form label-placement="top">
          <n-form-item label="节点名称" required>
            <n-input v-model:value="nodeForm.label" />
          </n-form-item>
          <n-form-item label="关联角色">
            <n-select
              v-model:value="nodeForm.role_keys"
              :options="roleOptions"
              multiple
              clearable
              placeholder="可选，不选则节点不绑定负责人角色"
            />
          </n-form-item>
          <n-form-item label="阶段列">
            <n-select
              v-model:value="nodeForm.lane_indexes"
              :options="laneOptions"
              multiple
              placeholder="至少选择一个阶段列"
            />
          </n-form-item>
          <n-form-item label="阻塞下一阶段">
            <n-switch v-model:value="nodeForm.blocks_lane_gate" />
            <n-text depth="3" style="margin-left: 8px">
              关闭后该节点未完成也不阻挡下一列节点开始
            </n-text>
          </n-form-item>
          <n-form-item label="同阶段排序">
            <n-input-number v-model:value="nodeForm.sort_in_lane" :min="0" :max="20" />
          </n-form-item>
          <n-text depth="3">阶段列数字越小越靠前；同一列内节点并行展示。节点可归属多列。</n-text>
        </n-form>
        <template #footer>
          <n-space justify="end">
            <n-button @click="showModal = false">取消</n-button>
            <n-button type="primary" :loading="saving" @click="onSaveNodeClick">保存</n-button>
          </n-space>
        </template>
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, h, onMounted, ref, watch } from 'vue';
import {
  NButton,
  NDataTable,
  NDrawer,
  NDrawerContent,
  NForm,
  NFormItem,
  NInput,
  NInputNumber,
  NSelect,
  NSpace,
  NSwitch,
  NText,
  useDialog,
  useMessage,
  type DataTableColumns,
} from 'naive-ui';
import {
  createRequirementWorkflowNode,
  deleteRequirementWorkflowNode,
  listRequirementWorkflowNodes,
  updateRequirementWorkflowNode,
} from '@/api/requirementWorkflow';
import RequirementWorkflowCanvas from '@/components/RequirementWorkflowCanvas.vue';
import RequirementStatusRulesSettings from '@/views/setting/RequirementStatusRulesSettings.vue';
import { useRequirementProjectConfig } from '@/composables/useRequirementProjectConfig';
import type { RequirementWorkflowNodeDef } from '@/types/business';
import { expandWorkflowCanvasNodes, type WorkflowNodeSource } from '@/utils/requirementWorkflowLayout';

const props = defineProps<{ projectId: string | null; readOnly?: boolean }>();

const message = useMessage();
const dialog = useDialog();
const projectConfig = useRequirementProjectConfig(() => props.projectId);
const roleOptions = computed(() =>
  projectConfig.roles.value.map((r) => ({ label: r.label, value: r.role_key }))
);
const sectionTab = ref<'nodes' | 'status-rules'>('nodes');
const loading = ref(false);
const saving = ref(false);
const defs = ref<RequirementWorkflowNodeDef[]>([]);
const showModal = ref(false);
const editing = ref<RequirementWorkflowNodeDef | null>(null);
const nodeForm = ref({
  label: '',
  role_keys: ['pm'] as string[],
  lane_indexes: [0] as number[],
  blocks_lane_gate: true,
  sort_in_lane: 0,
});

const maxLaneIndex = computed(() => {
  const fromDefs = defs.value.flatMap((d) => d.lane_indexes?.length ? d.lane_indexes : [d.lane_index]);
  return Math.max(0, ...fromDefs, 0);
});

const laneOptions = computed(() => {
  const max = Math.max(maxLaneIndex.value + 1, 6);
  return Array.from({ length: max + 1 }, (_, i) => ({ label: String(i), value: i }));
});

const previewNodes = computed(() =>
  expandWorkflowCanvasNodes(
    defs.value.map(
      (d): WorkflowNodeSource => ({
        node_key: d.node_key,
        label: d.label,
        role_keys: d.role_keys,
        lane_index: d.lane_index,
        lane_indexes: d.lane_indexes,
        blocks_lane_gate: d.blocks_lane_gate,
        sort_in_lane: d.sort_in_lane,
        enabled: true,
        state: 'pending',
      })
    )
  )
);

const columns = computed<DataTableColumns<RequirementWorkflowNodeDef>>(() => {
  const cols: DataTableColumns<RequirementWorkflowNodeDef> = [
  { title: '名称', key: 'label', width: 120 },
  {
    title: '角色',
    key: 'role_keys',
    width: 140,
    render: (r) =>
      r.role_keys.length ? r.role_keys.map((k) => projectConfig.roleLabel(k)).join('、') : '—',
  },
  {
    title: '阶段',
    key: 'lane_indexes',
    width: 80,
    render: (r) => (r.lane_indexes?.length ? r.lane_indexes : [r.lane_index]).join(', '),
  },
  {
    title: '阻塞',
    key: 'blocks_lane_gate',
    width: 56,
    render: (r) => (r.blocks_lane_gate ? '是' : '否'),
  },
  { title: '排序', key: 'sort_in_lane', width: 60 },
  ];
  if (props.readOnly) return cols;
  cols.push({
    title: '操作',
    key: 'a',
    width: 140,
    render: (row) =>
      h(NSpace, { size: 4 }, () => [
        h(NButton, { size: 'tiny', quaternary: true, onClick: () => openEdit(row) }, () => '编辑'),
        h(NButton, { size: 'tiny', quaternary: true, type: 'error', onClick: () => onRemove(row) }, () => '删除'),
      ]),
  });
  return cols;
});

async function load() {
  if (!props.projectId) {
    defs.value = [];
    return;
  }
  loading.value = true;
  try {
    await projectConfig.reload();
    const { data } = await listRequirementWorkflowNodes(props.projectId);
    defs.value = data;
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  editing.value = null;
  nodeForm.value = {
    label: '',
    role_keys: [],
    lane_indexes: [2, 3],
    blocks_lane_gate: false,
    sort_in_lane: 0,
  };
  showModal.value = true;
}

function openEdit(row: RequirementWorkflowNodeDef) {
  editing.value = row;
  nodeForm.value = {
    label: row.label,
    role_keys: [...row.role_keys],
    lane_indexes: [...(row.lane_indexes?.length ? row.lane_indexes : [row.lane_index])],
    blocks_lane_gate: row.blocks_lane_gate,
    sort_in_lane: row.sort_in_lane,
  };
  showModal.value = true;
}

async function onSaveNodeClick() {
  saving.value = true;
  try {
    await saveNode();
  } finally {
    saving.value = false;
  }
}

async function saveNode() {
  if (!props.projectId || !nodeForm.value.label.trim()) {
    message.warning('请填写节点名称');
    return;
  }
  if (!nodeForm.value.lane_indexes.length) {
    message.warning('请至少选择一个阶段列');
    return;
  }
  const payload = {
    label: nodeForm.value.label.trim(),
    role_keys: nodeForm.value.role_keys,
    lane_indexes: [...nodeForm.value.lane_indexes].sort((a, b) => a - b),
    blocks_lane_gate: nodeForm.value.blocks_lane_gate,
    sort_in_lane: nodeForm.value.sort_in_lane,
  };
  try {
    if (editing.value) {
      await updateRequirementWorkflowNode(props.projectId, editing.value.id, payload);
      message.success('已保存');
    } else {
      await createRequirementWorkflowNode(props.projectId, payload);
      message.success('已添加');
    }
    showModal.value = false;
    await load();
  } catch (e: unknown) {
    const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
    message.error(typeof detail === 'string' ? detail : '保存失败');
  }
}

function onRemove(row: RequirementWorkflowNodeDef) {
  if (!props.projectId) return;
  dialog.warning({
    title: '删除节点',
    content: `确定删除「${row.label}」？`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await deleteRequirementWorkflowNode(props.projectId!, row.id);
        message.success('已删除');
        await load();
      } catch (e: unknown) {
        const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
        message.error(typeof detail === 'string' ? detail : '删除失败');
      }
    },
  });
}

onMounted(load);
watch(() => props.projectId, load);
</script>

<style scoped>
.wf-settings-root {
  min-width: 0;
}
.wf-section-tabs :deep(.n-tab-pane) {
  padding-top: 12px;
}
.wf-settings-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 16px;
  align-items: start;
}
.wf-settings-config,
.wf-settings-preview {
  min-width: 0;
  max-width: 100%;
}
.wf-settings-preview {
  overflow: hidden;
}
@media (max-width: 1100px) {
  .wf-settings-layout {
    grid-template-columns: 1fr;
  }
}
.preview-label {
  display: block;
  margin-bottom: 8px;
  font-size: 13px;
}
.wf-settings-empty {
  padding: 24px;
}
</style>
