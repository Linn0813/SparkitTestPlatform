<template>
  <n-card size="small" :title="cardTitle">
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
import type { BugOverviewChart } from '@/types/business';
import { formatVersionDisplay } from '@/utils/versionLabel';
import { echarts, type ECharts } from '@/utils/echarts';

const UNASSIGNED_SERIES = '__unassigned__';

const props = withDefaults(
  defineProps<{
    chart: BugOverviewChart;
    title?: string;
    linkFor?: (statusKey: string, versionId: string | null) => RouteLocationRaw | null;
  }>(),
  {
    title: '缺陷',
  }
);

const router = useRouter();
const chartRef = ref<HTMLDivElement | null>(null);
let instance: ECharts | null = null;

const hasCategories = computed(() => (props.chart.by_status?.length ?? 0) > 0);

const cardTitle = computed(() => props.title);

const chartBoxStyle = { height: `${WORKBENCH_OVERVIEW_CHART_HEIGHT}px` };

function cellCount(statusKey: string, versionId: string | null): number {
  const cell = props.chart.cells.find(
    (c) => c.status_key === statusKey && (c.version_id ?? null) === versionId
  );
  return cell?.count ?? 0;
}

function render() {
  if (!chartRef.value || !hasCategories.value) return;
  const statuses = props.chart.by_status;
  const xData = statuses.map((s) => s.label);

  if (!instance) {
    instance = echarts.init(chartRef.value);
    instance.on('click', (p) => {
      const d = p.data as { statusKey?: string; versionId?: string | null };
      if (!d.statusKey) return;
      const to = props.linkFor?.(d.statusKey, d.versionId ?? null);
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
    stack: 'bug',
    barMaxWidth: 28,
    itemStyle: { color: VERSION_STACK_COLORS[slice.colorIndex % VERSION_STACK_COLORS.length] },
    data: statuses.map((st) => {
      const versionId = slice.id === UNASSIGNED_SERIES ? null : slice.id;
      return {
        value: cellCount(st.key, versionId),
        statusKey: st.key,
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
      grid: { left: 8, right: gridRight, top: 48, bottom: 8 },
      xAxis: {
        type: 'category',
        data: xData,
        axisLabel: { interval: 0, rotate: xData.length > 4 ? 20 : 0 },
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
