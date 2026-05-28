<template>
  <n-card
    size="small"
    :bordered="true"
    :style="{
      minWidth: '140px',
      opacity: state === 'completed' ? 0.85 : 1,
      borderColor: state === 'completed' ? 'var(--n-color-success)' : undefined,
    }"
  >
    <n-space vertical :size="6">
      <n-text strong style="font-size: 13px">{{ VERSION_NODE_LABELS[nodeKey] }}</n-text>
      <n-tag :type="state === 'completed' ? 'success' : 'default'" size="small" :bordered="false">
        {{ state === 'completed' ? '已完成' : '待完成' }}
      </n-tag>
      <n-space v-if="canEdit" :size="4">
        <n-button
          v-if="state !== 'completed' && canComplete"
          size="tiny"
          type="primary"
          :loading="acting"
          @click="emit('complete')"
        >
          完成
        </n-button>
        <n-button
          v-if="state === 'completed'"
          size="tiny"
          quaternary
          :loading="acting"
          @click="emit('reopen')"
        >
          重开
        </n-button>
      </n-space>
    </n-space>
  </n-card>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { NButton, NCard, NSpace, NTag, NText } from 'naive-ui';
import { VERSION_NODE_LABELS, canCompleteVersionNode } from '@/constants/versionStatus';
import type { VersionNodeKey, VersionNodeProgress } from '@/types/business';

const props = defineProps<{
  nodeKey: VersionNodeKey;
  nodes: VersionNodeProgress[];
  canEdit: boolean;
  acting?: boolean;
}>();

const emit = defineEmits<{
  complete: [];
  reopen: [];
}>();

const state = computed(() => props.nodes.find((n) => n.node_key === props.nodeKey)?.state ?? 'pending');

const canComplete = computed(() => canCompleteVersionNode(props.nodeKey, props.nodes));
</script>
