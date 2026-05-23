<template>
  <n-card size="small" :title="title">
    <div v-if="!hasCategories" class="chart-placeholder" :style="chartBoxStyle">
      <n-text depth="3">暂无数据</n-text>
    </div>
    <div v-else ref="chartRef" class="chart-box" :style="chartBoxStyle" />
  </n-card>
</template>

<script setup lang="ts">
import { NCard, NText } from 'naive-ui';
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useRouter, type RouteLocationRaw } from 'vue-router';
import {
  VERSION_STACK_COLORS,
  WORKBENCH_OVERVIEW_CHART_HEIGHT,
  workbenchCategoryGridRight,
} from '@/constants/workbenchCharts';
import type { BugFollowerOverviewChart } from '@/types/business';
import { formatVersionDisplay } from '@/utils/versionLabel';
import { echarts, type ECharts } from '@/utils/echarts';

const UNASSIGNED_SERIES = '__unassigned__';

const props = withDefaults(
  defineProps<{
    chart: BugFollowerOverviewChart;
    title?: string;
    linkFor?: (followerId: string | null, versionId: string | null) => RouteLocationRaw | null;
  }>(),
  {
    title: '跟进人',
  }
);

const router = useRouter();
const chartRef = ref<HTMLDivElement | null>(null);
let instance: ECharts | null = null;

const hasCategories = computed(() => (props.chart.followers?.length ?? 0) > 0);

const chartBoxStyle = { height: `${WORKBENCH_OVERVIEW_CHART_HEIGHT}px` };

function cellCount(followerId: string | null, versionId: string | null): number {
  const cell = props.chart.cells.find(
    (c) => (c.follower_id ?? null) === followerId && (c.version_id ?? null) === versionId
  );
  return cell?.count ?? 0;
}

function render() {
  if (!chartRef.value || !hasCategories.value) return;
  const followers = props.chart.followers;
  const xData = followers.map((f) => f.label);

  if (!instance) {
    instance = echarts.init(chartRef.value);
    instance.on('click', (p) => {
      const d = p.data as { followerId?: string | null; versionId?: string | null };
      const to = props.linkFor?.(d.followerId ?? null, d.versionId ?? null);
      if (to) router.push(to);
    });
  }

  const gridRight = workbenchCategoryGridRight(xData.length);
  const hasUnassigned = props.chart.cells.some((c) => !c.version_id && c.count > 0);

  type SeriesSlice = { id: string; name: string; colorIndex: number };
  const slices: SeriesSlice[] = props.chart.versions.map((v, i) => ({
    id: v.id,
    name: formatVersionDisplay(v),
    colorIndex: i,
  }));
  if (hasUnassigned) {
    slices.push({ id: UNASSIGNED_SERIES, name: '未关联版本', colorIndex: slices.length });
  }

  const series = slices.map((slice) => ({
    name: slice.name,
    type: 'bar' as const,
    stack: 'follower',
    barMaxWidth: 28,
    itemStyle: { color: VERSION_STACK_COLORS[slice.colorIndex % VERSION_STACK_COLORS.length] },
    data: followers.map((f) => {
      const versionId = slice.id === UNASSIGNED_SERIES ? null : slice.id;
      return {
        value: cellCount(f.id, versionId),
        followerId: f.id,
        versionId,
      };
    }),
  }));

  instance.setOption(
    {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter(params: unknown) {
          const list = params as { axisValue: string; seriesName: string; value: number }[];
          if (!list?.length) return '';
          const lines = list.filter((x) => x.value > 0).map((x) => `${x.seriesName}: ${x.value}`);
          if (!lines.length) return list[0].axisValue;
          return `${list[0].axisValue}<br/>${lines.join('<br/>')}`;
        },
      },
      legend: { type: 'scroll', top: 0 },
      grid: { left: 8, right: gridRight, top: 48, bottom: 20, containLabel: true },
      xAxis: {
        type: 'category',
        data: xData,
        axisLabel: {
          interval: 0,
          rotate: 0,
          fontSize: 11,
          hideOverlap: true,
          overflow: 'truncate',
          width: 72,
        },
      },
      yAxis: { type: 'value', minInterval: 1 },
      series,
    },
    true
  );
  instance.resize();
}

function resize() {
  instance?.resize();
}

defineExpose({ resize });

onMounted(async () => {
  await nextTick();
  render();
  window.addEventListener('resize', resize);
});
onBeforeUnmount(() => {
  window.removeEventListener('resize', resize);
  instance?.dispose();
  instance = null;
});
watch(
  () => props.chart,
  async () => {
    await nextTick();
    render();
  },
  { deep: true }
);
</script>

<style scoped>
.chart-box,
.chart-placeholder {
  width: 100%;
}
.chart-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
