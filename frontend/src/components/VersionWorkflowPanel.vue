<template>
  <n-card size="small" title="发版工作流" style="margin-bottom: 16px">
    <template #header-extra>
      <n-tag :type="versionStatusTagType(version.status)" size="small" :bordered="false">
        {{ versionStatusLabel(version.status) }}
      </n-tag>
    </template>

    <n-space vertical :size="16">
      <n-space :size="12" wrap align="center">
        <template v-for="(key, idx) in serialNodes" :key="key">
          <VersionNodeChip
            :node-key="key"
            :nodes="version.nodes"
            :can-edit="canEdit"
            :acting="actingKey === key"
            @complete="onComplete(key)"
            @reopen="onReopen(key)"
          />
          <n-text v-if="idx < serialNodes.length - 1" depth="3">→</n-text>
        </template>
      </n-space>

      <div>
        <n-text depth="3" style="font-size: 12px; display: block; margin-bottom: 8px">提审（可并行）</n-text>
        <n-space :size="12" wrap>
          <VersionNodeChip
            v-for="key in reviewNodes"
            :key="key"
            :node-key="key"
            :nodes="version.nodes"
            :can-edit="canEdit"
            :acting="actingKey === key"
            @complete="onComplete(key)"
            @reopen="onReopen(key)"
          />
        </n-space>
      </div>

      <n-space align="center" :size="12">
        <n-text depth="3">→</n-text>
        <VersionNodeChip
          node-key="live"
          :nodes="version.nodes"
          :can-edit="canEdit"
          :acting="actingKey === 'live'"
          @complete="onComplete('live')"
          @reopen="onReopen('live')"
        />
      </n-space>
    </n-space>
  </n-card>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { NCard, NSpace, NTag, NText, useMessage } from 'naive-ui';
import { completeVersionNode, reopenVersionNode } from '@/api/versions';
import VersionNodeChip from '@/components/VersionNodeChip.vue';
import {
  REVIEW_VERSION_NODES,
  SERIAL_VERSION_NODES,
  versionStatusLabel,
  versionStatusTagType,
} from '@/constants/versionStatus';
import type { ProjectVersion, VersionNodeKey } from '@/types/business';

const props = defineProps<{
  version: ProjectVersion;
  canEdit: boolean;
}>();

const emit = defineEmits<{
  updated: [version: ProjectVersion];
}>();

const message = useMessage();
const actingKey = ref<VersionNodeKey | null>(null);

const serialNodes = SERIAL_VERSION_NODES;
const reviewNodes = REVIEW_VERSION_NODES;

async function onComplete(nodeKey: VersionNodeKey) {
  actingKey.value = nodeKey;
  try {
    const { data } = await completeVersionNode(props.version.id, nodeKey);
    emit('updated', data.version);
    if (data.wecom_mention_count != null && data.wecom_mention_count > 0) {
      message.success(`节点已完成，已发送企微通知（@${data.wecom_mention_count} 人）`);
    } else {
      message.success('节点已完成');
    }
  } catch (e: unknown) {
    const detail =
      (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? '操作失败';
    message.error(typeof detail === 'string' ? detail : '操作失败');
  } finally {
    actingKey.value = null;
  }
}

async function onReopen(nodeKey: VersionNodeKey) {
  actingKey.value = nodeKey;
  try {
    const { data } = await reopenVersionNode(props.version.id, nodeKey);
    emit('updated', data);
    message.success('节点已重开');
  } catch (e: unknown) {
    const detail =
      (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? '操作失败';
    message.error(typeof detail === 'string' ? detail : '操作失败');
  } finally {
    actingKey.value = null;
  }
}
</script>
