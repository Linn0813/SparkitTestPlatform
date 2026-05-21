<template>
  <n-card size="small">
    <template #header>
      <n-space align="center" justify="space-between" style="width: 100%">
        <n-space align="center" :size="12" wrap>
          <n-text strong>版本维度</n-text>
          <n-text v-if="focus?.version" depth="3" style="font-size: 13px">
            当前版本：<n-text strong>{{ currentVersionLabel }}</n-text>
          </n-text>
        </n-space>
        <n-select
          v-if="focus?.version"
          :value="selectedVersionId"
          :options="versionOptions"
          size="small"
          style="width: 200px"
          placeholder="选择版本"
          @update:value="onVersionChange"
        />
      </n-space>
    </template>
    <n-empty v-if="!focus?.version" description="暂无版本，请先在版本管理创建" size="small" />
    <n-grid v-else :cols="24" :x-gap="12" responsive="screen">
      <n-gi :span="8">
        <WorkbenchFocusBarChart
          ref="reqChartRef"
          title="需求"
          :breakdown="focus.requirements"
          :link-for="reqLink"
          :color-for="reqColor"
        />
      </n-gi>
      <n-gi :span="16">
        <WorkbenchFocusBarChart
          ref="bugChartRef"
          title="缺陷（规划版本）"
          :breakdown="focus.bugs"
          :axis-label-rotate="0"
          :link-for="bugLink"
          :color-for="bugColor"
        />
      </n-gi>
    </n-grid>
  </n-card>
</template>

<script setup lang="ts">
import { NCard, NEmpty, NGi, NGrid, NSelect, NSpace, NText } from 'naive-ui';
import { computed, ref } from 'vue';
import type { RouteLocationRaw } from 'vue-router';
import { BUG_STATUS_COLORS, REQUIREMENT_STATUS_COLORS } from '@/constants/workbenchCharts';
import type { StatusCountItem, VersionFocus } from '@/types/business';
import { formatVersionDisplay } from '@/utils/versionLabel';
import WorkbenchFocusBarChart from './WorkbenchFocusBarChart.vue';

const props = defineProps<{
  focus: VersionFocus | undefined;
  selectedVersionId: string | null;
}>();

const emit = defineEmits<{
  'update:selectedVersionId': [id: string | null];
}>();

const reqChartRef = ref<{ resize?: () => void } | null>(null);
const bugChartRef = ref<{ resize?: () => void } | null>(null);

const currentVersionLabel = computed(() =>
  props.focus?.version ? formatVersionDisplay(props.focus.version) : ''
);

const versionOptions = computed(() =>
  (props.focus?.versions ?? []).map((v) => ({
    label: formatVersionDisplay(v),
    value: v.id,
  }))
);

function onVersionChange(id: string | null) {
  emit('update:selectedVersionId', id);
}

function resize() {
  reqChartRef.value?.resize?.();
  bugChartRef.value?.resize?.();
}

defineExpose({ resize });

function reqLink(item: StatusCountItem): RouteLocationRaw | null {
  const vid = props.focus?.version?.id;
  if (!vid) return null;
  return { name: 'requirements', query: { version_id: vid, status: item.key } };
}

function bugLink(item: StatusCountItem): RouteLocationRaw | null {
  const vid = props.focus?.version?.id;
  if (!vid) return null;
  return { name: 'bugs', query: { plan_version_id: vid, status_key: item.key } };
}

function reqColor(key: string) {
  return REQUIREMENT_STATUS_COLORS[key];
}

function bugColor(key: string) {
  const idx = props.focus?.bugs.by_status.findIndex((s) => s.key === key) ?? 0;
  return BUG_STATUS_COLORS[idx % BUG_STATUS_COLORS.length];
}
</script>
