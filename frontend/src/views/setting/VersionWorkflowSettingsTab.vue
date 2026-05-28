<template>
  <div v-if="!projectId" class="wf-settings-empty">
    <n-text depth="3">请选择项目</n-text>
  </div>
  <div v-else class="wf-settings-root">
    <n-tabs v-model:value="sectionTab" type="line" class="wf-section-tabs">
      <n-tab-pane name="nodes" tab="工作流节点">
        <n-tabs v-model:value="versionTypeTab" type="segment" style="margin-bottom: 12px">
          <n-tab-pane name="app_release" tab="应用发版" />
          <n-tab-pane name="hotfix" tab="热修" />
        </n-tabs>
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
            <VersionWorkflowCanvas :nodes="previewNodes" :defs="defs" />
          </div>
        </div>
      </n-tab-pane>
      <n-tab-pane name="status-rules" tab="状态与节点映射" display-directive="if">
        <template v-if="sectionTab === 'status-rules'">
          <n-tabs v-model:value="statusRulesTypeTab" type="segment" style="margin-bottom: 12px">
            <n-tab-pane name="app_release" tab="应用发版" />
            <n-tab-pane name="hotfix" tab="热修" />
          </n-tabs>
          <VersionStatusRulesSettings
            :key="statusRulesTypeTab"
            :project-id="projectId"
            :version-type="statusRulesTypeTab"
            :workflow-nodes="defsByType[statusRulesTypeTab] ?? []"
            :read-only="readOnly"
          />
        </template>
      </n-tab-pane>
    </n-tabs>

    <n-drawer v-model:show="showModal" :width="480" placement="right">
      <n-drawer-content :title="editing ? '编辑节点' : '添加节点'" closable>
        <n-form label-placement="top">
          <n-form-item v-if="!editing" label="节点标识" required>
            <n-input
              v-model:value="nodeForm.node_key"
              placeholder="如 planning、live（创建后不可改）"
            />
          </n-form-item>
          <n-form-item label="节点名称" required>
            <n-input v-model:value="nodeForm.label" />
          </n-form-item>
          <n-form-item label="阶段列">
            <n-select
              v-model:value="nodeForm.lane_indexes"
              :options="laneOptions"
              multiple
              placeholder="至少选择一个阶段列"
            />
          </n-form-item>
          <n-form-item label="同阶段排序">
            <n-input-number v-model:value="nodeForm.sort_in_lane" :min="0" :max="20" />
          </n-form-item>
          <n-text depth="3">阶段列数字越小越靠前；同一列内节点可并行展示。</n-text>
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
  NTabPane,
  NTabs,
  NText,
  useDialog,
  useMessage,
  type DataTableColumns,
} from 'naive-ui';
import {
  createVersionWorkflowNode,
  deleteVersionWorkflowNode,
  listVersionWorkflowNodes,
  updateVersionWorkflowNode,
} from '@/api/versionWorkflow';
import VersionWorkflowCanvas from '@/components/VersionWorkflowCanvas.vue';
import VersionStatusRulesSettings from '@/views/setting/VersionStatusRulesSettings.vue';
import type { VersionType, VersionWorkflowNodeDef } from '@/types/business';
import { versionDefsToCanvasNodes } from '@/utils/versionWorkflowLayout';

const props = defineProps<{ projectId: string | null; readOnly?: boolean }>();

const message = useMessage();
const dialog = useDialog();
const sectionTab = ref<'nodes' | 'status-rules'>('nodes');
const versionTypeTab = ref<VersionType>('app_release');
const statusRulesTypeTab = ref<VersionType>('app_release');
const loading = ref(false);
const saving = ref(false);
const defs = ref<VersionWorkflowNodeDef[]>([]);
const defsByType = ref<Partial<Record<VersionType, VersionWorkflowNodeDef[]>>>({});
const showModal = ref(false);
const editing = ref<VersionWorkflowNodeDef | null>(null);
const nodeForm = ref({
  node_key: '',
  label: '',
  lane_indexes: [0] as number[],
  sort_in_lane: 0,
});

const maxLaneIndex = computed(() => {
  const fromDefs = defs.value.flatMap((d) => (d.lane_indexes?.length ? d.lane_indexes : [d.lane_index]));
  return Math.max(0, ...fromDefs, 0);
});

const laneOptions = computed(() => {
  const max = Math.max(maxLaneIndex.value + 1, 6);
  return Array.from({ length: max + 1 }, (_, i) => ({ label: String(i), value: i }));
});

const previewNodes = computed(() => versionDefsToCanvasNodes(defs.value, []));

const columns = computed<DataTableColumns<VersionWorkflowNodeDef>>(() => {
  const cols: DataTableColumns<VersionWorkflowNodeDef> = [
    { title: '标识', key: 'node_key', width: 140, ellipsis: { tooltip: true } },
    { title: '名称', key: 'label', width: 120 },
    {
      title: '阶段',
      key: 'lane_indexes',
      width: 80,
      render: (r) => (r.lane_indexes?.length ? r.lane_indexes : [r.lane_index]).join(', '),
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
        h(
          NButton,
          { size: 'tiny', quaternary: true, type: 'error', onClick: () => onRemove(row) },
          () => '删除'
        ),
      ]),
  });
  return cols;
});

function applyTabDefs() {
  defs.value = defsByType.value[versionTypeTab.value] ?? [];
}

async function load() {
  if (!props.projectId) {
    defs.value = [];
    defsByType.value = {};
    return;
  }
  loading.value = true;
  try {
    const [appRes, hotfixRes] = await Promise.all([
      listVersionWorkflowNodes(props.projectId, 'app_release'),
      listVersionWorkflowNodes(props.projectId, 'hotfix'),
    ]);
    defsByType.value = {
      app_release: appRes.data,
      hotfix: hotfixRes.data,
    };
    applyTabDefs();
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  editing.value = null;
  nodeForm.value = {
    node_key: '',
    label: '',
    lane_indexes: [0],
    sort_in_lane: 0,
  };
  showModal.value = true;
}

function openEdit(row: VersionWorkflowNodeDef) {
  editing.value = row;
  nodeForm.value = {
    node_key: row.node_key,
    label: row.label,
    lane_indexes: [...(row.lane_indexes?.length ? row.lane_indexes : [row.lane_index])],
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
  const lanePayload = {
    label: nodeForm.value.label.trim(),
    lane_indexes: [...nodeForm.value.lane_indexes].sort((a, b) => a - b),
    sort_in_lane: nodeForm.value.sort_in_lane,
  };
  try {
    if (editing.value) {
      await updateVersionWorkflowNode(props.projectId, editing.value.id, lanePayload);
      message.success('已保存');
    } else {
      if (!nodeForm.value.node_key.trim()) {
        message.warning('请填写节点标识');
        return;
      }
      await createVersionWorkflowNode(props.projectId, versionTypeTab.value, {
        node_key: nodeForm.value.node_key.trim(),
        ...lanePayload,
      });
      message.success('已添加');
    }
    showModal.value = false;
    await load();
  } catch (e: unknown) {
    const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
    message.error(typeof detail === 'string' ? detail : '保存失败');
  }
}

function onRemove(row: VersionWorkflowNodeDef) {
  if (!props.projectId) return;
  dialog.warning({
    title: '删除节点',
    content: `确定删除「${row.label}」？`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await deleteVersionWorkflowNode(props.projectId!, row.id);
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
watch(versionTypeTab, applyTabDefs);
</script>

<style scoped>
.wf-settings-root {
  min-width: 0;
}
.wf-section-tabs {
  min-width: 0;
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
