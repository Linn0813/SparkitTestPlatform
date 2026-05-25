<template>
  <div class="status-rules-settings">
    <n-space justify="space-between" align="center" style="margin-bottom: 8px">
      <div>
        <n-text strong>状态与节点映射</n-text>
        <n-text depth="3" style="display: block; margin-top: 4px; font-size: 12px; max-width: 720px">
          按优先级从小到大匹配。当前阶段节点：阶段含关联节点且仍有未完成项时命中。
          草稿请只关联 PRD 输出、设计中只关联需求设计（优先级：草稿 &lt; 设计中）；发版未完成用待发版规则。
        </n-text>
      </div>
      <n-space v-if="!readOnly" :size="8">
        <n-button size="small" @click="addRule">添加规则</n-button>
        <n-button size="small" type="primary" :loading="saving" :disabled="!projectId" @click="onSave">
          保存映射
        </n-button>
      </n-space>
    </n-space>

    <n-data-table size="small" :columns="columns" :data="draft" :loading="loading" :row-key="rowKey" />
  </div>
</template>

<script setup lang="ts">
import { computed, h, onMounted, ref, watch } from 'vue';
import {
  NButton,
  NDataTable,
  NInputNumber,
  NSelect,
  NSpace,
  NText,
  useMessage,
  type DataTableColumns,
  type SelectOption,
} from 'naive-ui';
import {
  listRequirementStatusRules,
  saveRequirementStatusRules,
  syncProjectRequirementStatuses,
} from '@/api/requirementStatusRules';
import { REQUIREMENT_STATUS_OPTIONS } from '@/constants/requirementStatus';
import type { RequirementStatus, RequirementStatusRule, RequirementWorkflowNodeDef } from '@/types/business';

const props = defineProps<{
  projectId: string | null;
  workflowNodes: RequirementWorkflowNodeDef[];
  readOnly?: boolean;
}>();

const message = useMessage();
const loading = ref(false);
const saving = ref(false);

type StatusRuleTrigger = 'lane' | 'node_completed' | 'status_hold';

type DraftRule = {
  _key: string;
  status: RequirementStatus;
  node_keys: string[];
  sort: number;
  trigger_type: StatusRuleTrigger;
};

const TRIGGER_OPTIONS: { label: string; value: StatusRuleTrigger }[] = [
  { label: '当前阶段节点', value: 'lane' },
  { label: '节点已完成', value: 'node_completed' },
  { label: '状态保持', value: 'status_hold' },
];

const draft = ref<DraftRule[]>([]);

const statusOptions = computed<SelectOption[]>(() =>
  REQUIREMENT_STATUS_OPTIONS.map((o) => ({ label: o.label, value: o.value }))
);

const nodeOptions = computed<SelectOption[]>(() =>
  props.workflowNodes.map((n) => ({ label: n.label, value: n.node_key }))
);

function rowKey(row: DraftRule) {
  return row._key;
}

function toDraft(rules: RequirementStatusRule[]): DraftRule[] {
  return rules.map((r, i) => ({
    _key: r.id || `new-${i}`,
    status: r.status,
    node_keys: [...r.node_keys],
    sort: r.sort,
    trigger_type: (r.trigger_type as StatusRuleTrigger) || 'lane',
  }));
}

async function load() {
  if (!props.projectId) {
    draft.value = [];
    return;
  }
  loading.value = true;
  try {
    const { data } = await listRequirementStatusRules(props.projectId);
    draft.value = toDraft(data);
  } finally {
    loading.value = false;
  }
}

function addRule() {
  const maxSort = draft.value.length ? Math.max(...draft.value.map((r) => r.sort)) + 1 : 0;
  draft.value = [
    ...draft.value,
    {
      _key: `new-${Date.now()}`,
      status: 'draft',
      node_keys: [],
      sort: maxSort,
      trigger_type: 'lane',
    },
  ];
}

function removeRule(row: DraftRule) {
  draft.value = draft.value.filter((r) => r._key !== row._key);
}

async function onSave() {
  if (!props.projectId) return;
  if (!draft.value.length) {
    message.warning('至少保留一条映射规则');
    return;
  }
  saving.value = true;
  try {
    const { data } = await saveRequirementStatusRules(
      props.projectId,
      draft.value.map((r) => ({
        status: r.status,
        node_keys: r.node_keys,
        sort: r.sort,
        trigger_type: r.trigger_type,
      }))
    );
    draft.value = toDraft(data);
    const { data: syncResult } = await syncProjectRequirementStatuses(props.projectId);
    message.success(
      syncResult.updated_count > 0
        ? `状态映射已保存，已按最新规则更新 ${syncResult.updated_count} 条需求状态`
        : '状态映射已保存'
    );
  } catch (e: unknown) {
    const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
    message.error(typeof detail === 'string' ? detail : '保存失败');
  } finally {
    saving.value = false;
  }
}

const columns = computed<DataTableColumns<DraftRule>>(() => {
  const readOnly = props.readOnly;
  const cols: DataTableColumns<DraftRule> = [
  {
    title: '优先级',
    key: 'sort',
    width: 88,
    render: (row) =>
      readOnly
        ? String(row.sort)
        : h(NInputNumber, {
            size: 'small',
            min: 0,
            max: 99,
            value: row.sort,
            onUpdateValue: (v: number | null) => {
              row.sort = v ?? 0;
            },
          }),
  },
  {
    title: '触发方式',
    key: 'trigger_type',
    width: 120,
    render: (row) =>
      readOnly
        ? TRIGGER_OPTIONS.find((o) => o.value === row.trigger_type)?.label ?? row.trigger_type
        : h(NSelect, {
            size: 'small',
            value: row.trigger_type,
            options: TRIGGER_OPTIONS,
            onUpdateValue: (v: StatusRuleTrigger) => {
              row.trigger_type = v;
              if (v === 'status_hold') {
                row.node_keys = [];
              }
            },
          }),
  },
  {
    title: '需求状态',
    key: 'status',
    width: 110,
    render: (row) =>
      readOnly
        ? String(statusOptions.value.find((o) => o.value === row.status)?.label ?? row.status)
        : h(NSelect, {
            size: 'small',
            value: row.status,
            options: statusOptions.value,
            onUpdateValue: (v: RequirementStatus) => {
              row.status = v;
            },
          }),
  },
  {
    title: '关联节点',
    key: 'node_keys',
    minWidth: 200,
    render: (row) =>
      readOnly
        ? row.trigger_type === 'status_hold'
          ? '—'
          : row.node_keys
              .map((k) => nodeOptions.value.find((o) => o.value === k)?.label ?? k)
              .join('、') || '—'
        : h(NSelect, {
            size: 'small',
            multiple: true,
            filterable: true,
            disabled: row.trigger_type === 'status_hold',
            value: row.node_keys,
            options: nodeOptions.value,
            placeholder: row.trigger_type === 'status_hold' ? '—' : '选择节点',
            onUpdateValue: (v: string[]) => {
              row.node_keys = v ?? [];
            },
          }),
  },
  ];
  if (!readOnly) {
    cols.push({
      title: '操作',
      key: 'a',
      width: 64,
      render: (row) =>
        h(NButton, { size: 'tiny', quaternary: true, type: 'error', onClick: () => removeRule(row) }, () => '删除'),
    });
  }
  return cols;
});

onMounted(load);
watch(() => props.projectId, load);
</script>

<style scoped>
.status-rules-settings {
  min-width: 0;
}
</style>
