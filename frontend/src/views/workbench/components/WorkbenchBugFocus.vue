<template>
  <n-card size="small">
    <template #header>
      <n-text strong>缺陷维度</n-text>
    </template>
    <n-grid :cols="24" :x-gap="12" responsive="screen">
      <n-gi :span="12">
        <WorkbenchBugOverviewChart
          ref="byVersionStatusRef"
          title="缺陷状态"
          :chart="focus?.by_version_status ?? emptyChart"
          :link-for="bugOverviewLink"
        />
      </n-gi>
      <n-gi :span="12">
        <WorkbenchBugFollowerChart
          ref="followerChartRef"
          :chart="focus?.follower_by_version ?? emptyFollowerChart"
          :link-for="followerLink"
        />
      </n-gi>
    </n-grid>
  </n-card>
</template>

<script setup lang="ts">
import { NCard, NGi, NGrid, NText } from 'naive-ui';
import { ref } from 'vue';
import type { RouteLocationRaw } from 'vue-router';
import {
  bugFollowerChartCellLink,
  bugOverviewChartCellLink,
} from '@/navigation/workbenchLinks';
import type { BugFocus, BugFollowerOverviewChart, BugOverviewChart } from '@/types/business';
import WorkbenchBugFollowerChart from './WorkbenchBugFollowerChart.vue';
import WorkbenchBugOverviewChart from './WorkbenchBugOverviewChart.vue';

defineProps<{
  focus: BugFocus | undefined;
}>();

const emptyChart: BugOverviewChart = {
  total: 0,
  by_status: [],
  versions: [],
  cells: [],
};

const emptyFollowerChart: BugFollowerOverviewChart = {
  followers: [],
  versions: [],
  cells: [],
};

const byVersionStatusRef = ref<{ resize?: () => void } | null>(null);
const followerChartRef = ref<{ resize?: () => void } | null>(null);

function bugOverviewLink(statusKey: string, versionId: string | null): RouteLocationRaw {
  return bugOverviewChartCellLink(statusKey, versionId);
}

function followerLink(followerId: string | null, versionId: string | null): RouteLocationRaw {
  return bugFollowerChartCellLink(followerId, versionId);
}

function resize() {
  byVersionStatusRef.value?.resize?.();
  followerChartRef.value?.resize?.();
}

defineExpose({ resize });
</script>
