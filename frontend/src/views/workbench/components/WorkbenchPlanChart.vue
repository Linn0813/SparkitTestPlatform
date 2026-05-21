<template>
  <n-card size="small" title="计划 · 用例执行">
    <div v-if="hasData" ref="chartRef" class="chart-box" :style="chartBoxStyle" />
    <div v-else class="chart-placeholder" :style="chartBoxStyle">
      <n-empty description="暂无未开始或进行中的计划" size="small" />
    </div>
  </n-card>
</template>

<script setup lang="ts">
import { NCard, NEmpty } from 'naive-ui';
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import {
  EXECUTE_RESULT_COLORS,
  WORKBENCH_OVERVIEW_CHART_HEIGHT,
  workbenchCategoryGridRight,
} from '@/constants/workbenchCharts';
import type { PlanExecutionChart } from '@/types/business';
import { echarts, type ECharts } from '@/utils/echarts';

const props = defineProps<{
  chart: PlanExecutionChart | undefined;
}>();

const router = useRouter();
const chartRef = ref<HTMLDivElement | null>(null);
let instance: ECharts | null = null;

const hasData = computed(() => (props.chart?.points?.length ?? 0) > 0);

const chartBoxStyle = { height: `${WORKBENCH_OVERVIEW_CHART_HEIGHT}px` };

const resultOrder = ['not_run', 'pass', 'fail', 'block', 'skip'];

function render() {
  if (!chartRef.value || !props.chart?.points.length) return;
  if (!instance) {
    instance = echarts.init(chartRef.value);
    instance.on('click', (p) => {
      const planId = (p.data as { planId?: string })?.planId;
      if (planId) router.push({ name: 'plan-detail', params: { id: planId } });
    });
  }

  const xData = props.chart.points.map((p) => p.plan_name);
  const gridRight = workbenchCategoryGridRight(xData.length);
  const labelByKey = new Map<string, string>();
  for (const p of props.chart.points) {
    for (const r of p.by_result) labelByKey.set(r.key, r.label);
  }

  const series = resultOrder
    .filter((key) => labelByKey.has(key))
    .map((key) => ({
      name: labelByKey.get(key) ?? key,
      type: 'bar' as const,
      stack: 'total',
      barMaxWidth: 28,
      itemStyle: { color: EXECUTE_RESULT_COLORS[key] ?? '#999' },
      data: props.chart!.points.map((p) => {
        const item = p.by_result.find((r) => r.key === key);
        return { value: item?.count ?? 0, planId: p.plan_id };
      }),
    }));

  instance.setOption(
    {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter(params: unknown) {
          const list = params as { axisValue: string; seriesName: string; value: number; dataIndex: number }[];
          if (!list?.length) return '';
          const idx = list[0].dataIndex;
          const point = props.chart!.points[idx];
          const lines = list.map((x) => `${x.seriesName}: ${x.value}`).join('<br/>');
          const rate = point.pass_rate != null ? `<br/>通过率: ${point.pass_rate}%` : '';
          return `${list[0].axisValue}<br/>${lines}${rate}`;
        },
      },
      legend: { type: 'scroll', top: 0 },
      grid: { left: 48, right: gridRight, top: 48, bottom: 8, containLabel: true },
      xAxis: { type: 'category', data: xData, axisLabel: { interval: 0, rotate: xData.length > 4 ? 20 : 0 } },
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
