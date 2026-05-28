<template>
  <n-card v-if="node" size="small" class="version-node-action-panel">
    <n-space vertical :size="12">
      <n-space justify="space-between" align="center">
        <div>
          <n-text strong>{{ label }}</n-text>
          <n-tag
            :type="node.state === 'completed' ? 'success' : 'default'"
            size="small"
            :bordered="false"
            style="margin-left: 8px"
          >
            {{ node.state === 'completed' ? '已完成' : '待完成' }}
          </n-tag>
        </div>
        <n-space v-if="canEdit" :size="8">
          <n-button
            v-if="node.state !== 'completed' && canComplete"
            size="small"
            type="primary"
            :loading="acting"
            @click="emit('complete')"
          >
            完成
          </n-button>
          <n-button
            v-if="node.state === 'completed'"
            size="small"
            quaternary
            :loading="acting"
            @click="emit('reopen')"
          >
            重开
          </n-button>
        </n-space>
      </n-space>

      <n-form v-if="canEdit" label-placement="top" size="small">
        <n-grid :cols="2" :x-gap="12">
          <n-gi>
            <n-form-item label="负责人">
              <n-select
                v-model:value="form.assignee_id"
                :options="memberOptions"
                clearable
                filterable
                placeholder="可选"
              />
            </n-form-item>
          </n-gi>
          <n-gi>
            <n-form-item label="排期（可选）">
              <n-date-picker
                v-model:formatted-value="scheduleRange"
                type="daterange"
                value-format="yyyy-MM-dd"
                clearable
                style="width: 100%"
              />
            </n-form-item>
          </n-gi>
        </n-grid>
        <n-space justify="end">
          <n-button size="small" :loading="saving" @click="saveMeta">保存</n-button>
        </n-space>
      </n-form>
      <n-descriptions v-else :column="2" size="small" label-placement="left">
        <n-descriptions-item label="负责人">
          {{ assigneeLabel(form.assignee_id) || '—' }}
        </n-descriptions-item>
        <n-descriptions-item label="排期">
          {{ scheduleText || '—' }}
        </n-descriptions-item>
      </n-descriptions>
    </n-space>
  </n-card>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import {
  NButton,
  NCard,
  NDatePicker,
  NDescriptions,
  NDescriptionsItem,
  NForm,
  NFormItem,
  NGi,
  NGrid,
  NSelect,
  NSpace,
  NTag,
  NText,
  useMessage,
} from 'naive-ui';
import { updateVersionNode } from '@/api/versions';
import type { VersionNodeProgress, VersionWorkflowNodeDef } from '@/types/business';
import { canCompleteVersionNode, formatVersionNodeSchedule } from '@/utils/versionWorkflowLayout';

const props = defineProps<{
  versionId: string;
  nodeKey: string | null;
  nodes: VersionNodeProgress[];
  defs: VersionWorkflowNodeDef[];
  canEdit: boolean;
  acting?: boolean;
  memberOptions: { label: string; value: string }[];
  assigneeLabel: (userId: string | null | undefined) => string;
}>();

const emit = defineEmits<{
  complete: [];
  reopen: [];
  updated: [];
}>();

const message = useMessage();
const saving = ref(false);
const form = ref({
  assignee_id: null as string | null,
  scheduled_start: null as string | null,
  scheduled_end: null as string | null,
});

const node = computed(() =>
  props.nodeKey ? props.nodes.find((n) => n.node_key === props.nodeKey) ?? null : null
);

const label = computed(() => {
  if (!props.nodeKey) return '';
  return props.defs.find((d) => d.node_key === props.nodeKey)?.label ?? props.nodeKey;
});

const canComplete = computed(() =>
  props.nodeKey ? canCompleteVersionNode(props.nodeKey, props.nodes, props.defs) : false
);

const scheduleRange = computed({
  get: () => {
    if (form.value.scheduled_start && form.value.scheduled_end) {
      return [form.value.scheduled_start, form.value.scheduled_end] as [string, string];
    }
    return null;
  },
  set: (val: [string, string] | null) => {
    form.value.scheduled_start = val?.[0] ?? null;
    form.value.scheduled_end = val?.[1] ?? null;
  },
});

const scheduleText = computed(() =>
  formatVersionNodeSchedule({
    node_key: props.nodeKey ?? '',
    state: node.value?.state ?? 'pending',
    scheduled_start: form.value.scheduled_start,
    scheduled_end: form.value.scheduled_end,
  })
);

function syncFormFromNode() {
  if (!node.value) return;
  form.value = {
    assignee_id: node.value.assignee_id ?? null,
    scheduled_start: node.value.scheduled_start?.slice(0, 10) ?? null,
    scheduled_end: node.value.scheduled_end?.slice(0, 10) ?? null,
  };
}

async function saveMeta() {
  if (!props.nodeKey) return;
  saving.value = true;
  try {
    await updateVersionNode(props.versionId, props.nodeKey, {
      assignee_id: form.value.assignee_id,
      scheduled_start: form.value.scheduled_start,
      scheduled_end: form.value.scheduled_end,
    });
    message.success('已保存');
    emit('updated');
  } catch (e: unknown) {
    const detail =
      (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? '保存失败';
    message.error(typeof detail === 'string' ? detail : '保存失败');
  } finally {
    saving.value = false;
  }
}

watch(() => props.nodeKey, syncFormFromNode, { immediate: true });
watch(node, syncFormFromNode);
</script>

<style scoped>
.version-node-action-panel {
  margin-bottom: 12px;
}
</style>
