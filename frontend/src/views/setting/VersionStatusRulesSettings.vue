<template>
  <div class="status-rules-settings">
    <n-space justify="space-between" align="center" style="margin-bottom: 8px">
      <div>
        <n-text strong>状态与节点映射</n-text>
        <n-text depth="3" style="display: block; margin-top: 4px; font-size: 12px; max-width: 720px">
          按优先级从小到大匹配。当前阶段节点：阶段含关联节点且仍有未完成项时命中。
          节点已完成：关联节点全部完成后命中。关联节点仅来自当前版本类型的工作流。
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
  listVersionStatusRules,
  saveVersionStatusRules,
  syncProjectVersionStatuses,
} from '@/api/versionStatusRules';
import { VERSION_STATUS_OPTIONS } from '@/constants/versionStatus';
import type { VersionStatus, VersionStatusRule, VersionType, VersionWorkflowNodeDef } from '@/types/business';

const props = withDefaults(
  defineProps<{
    projectId: string | null;
    versionType: VersionType;
    workflowNodes: VersionWorkflowNodeDef[];
    readOnly?: boolean;
  }>(),
  {
    versionType: 'app_release',
  }
);

const message = useMessage();
const loading = ref(false);
const saving = ref(false);

type StatusRuleTrigger = 'lane' | 'node_completed' | 'status_hold';

type DraftRule = {
  _key: string;
  status: VersionStatus;
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
  VERSION_STATUS_OPTIONS.map((o) => ({ label: o.label, value: o.value }))
);

const nodeOptions = computed<SelectOption[]>(() =>
  props.workflowNodes.map((n) => ({ label: n.label, value: n.node_key }))
);

function rowKey(row: DraftRule) {
  return row._key;
}

function toDraft(rules: VersionStatusRule[]): DraftRule[] {
  return rules.map((r, i) => ({
    _key: r.id || `new-${i}`,
    status: r.status,
    node_keys: [...r.node_keys],
    sort: r.sort,
    trigger_type: (r.trigger_type as StatusRuleTrigger) || 'lane',
  }));
}

async function load() {
  if (!props.projectId || !props.versionType) {
    draft.value = [];
    return;
  }
  loading.value = true;
  try {
    const { data } = await listVersionStatusRules(props.projectId, props.versionType);
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
      status: 'planning',
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
    const { data } = await saveVersionStatusRules(
      props.projectId,
      props.versionType,
      draft.value.map((r) => ({
        status: r.status,
        node_keys: r.node_keys,
        sort: r.sort,
        trigger_type: r.trigger_type,
      }))
    );
    draft.value = toDraft(data);
    const { data: syncResult } = await syncProjectVersionStatuses(props.projectId);
    message.success(
      syncResult.updated_count > 0
        ? `状态映射已保存，已按最新规则更新 ${syncResult.updated_count} 个版本状态`
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
      title: '版本状态',
      key: 'status',
      width: 110,
      render: (row) =>
        readOnly
          ? String(statusOptions.value.find((o) => o.value === row.status)?.label ?? row.status)
          : h(NSelect, {
              size: 'small',
              value: row.status,
              options: statusOptions.value,
              onUpdateValue: (v: VersionStatus) => {
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
watch(() => props.versionType, load);
</script>

<style scoped>
.status-rules-settings {
  min-width: 0;
}
</style>
