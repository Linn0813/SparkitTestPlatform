<template>
  <n-card size="small" :title="title">
    <n-text v-if="!hasCategories" depth="3">暂无数据</n-text>
    <div v-else ref="chartRef" class="chart-box" :style="chartBoxStyle" />
  </n-card>
</template>

<script setup lang="ts">
import { NCard, NText } from 'naive-ui';
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useRouter, type RouteLocationRaw } from 'vue-router';
import {
  WORKBENCH_VERSION_FOCUS_CHART_HEIGHT,
  workbenchCategoryGridRight,
} from '@/constants/workbenchCharts';
import type { StatusBreakdown, StatusCountItem } from '@/types/business';
import { echarts, type ECharts } from '@/utils/echarts';

const props = defineProps<{
  title: string;
  breakdown: StatusBreakdown;
  colorFor?: (key: string, index: number) => string | undefined;
  linkFor?: (item: StatusCountItem) => RouteLocationRaw | null;
  /** 横轴标签旋转角度；不传则状态较多时自动倾斜 */
  axisLabelRotate?: number;
}>();

const router = useRouter();
const chartRef = ref<HTMLDivElement | null>(null);
let instance: ECharts | null = null;

const hasCategories = computed(() => (props.breakdown.by_status?.length ?? 0) > 0);

const chartBoxStyle = { height: `${WORKBENCH_VERSION_FOCUS_CHART_HEIGHT}px` };

function render() {
  if (!chartRef.value || !hasCategories.value) return;
  const items = props.breakdown.by_status;
  if (!instance) {
    instance = echarts.init(chartRef.value);
    instance.on('click', (p) => {
      const d = p.data as { statusKey?: string };
      if (!d.statusKey) return;
      const item = items.find((s) => s.key === d.statusKey);
      if (!item) return;
      const to = props.linkFor?.(item);
      if (to) router.push(to);
    });
  }

  const xData = items.map((s) => s.label);
  const gridRight = workbenchCategoryGridRight(xData.length);
  const labelRotate =
    props.axisLabelRotate !== undefined ? props.axisLabelRotate : xData.length > 5 ? 24 : 0;
  const labelHorizontal = labelRotate === 0;

  instance.setOption(
    {
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: {
        left: 8,
        right: gridRight,
        top: 16,
        bottom: labelHorizontal ? 20 : 8,
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: xData,
        axisLabel: {
          interval: 0,
          rotate: labelRotate,
          fontSize: 11,
          ...(labelHorizontal
            ? { hideOverlap: true, overflow: 'truncate' as const, width: 72 }
            : {}),
        },
      },
      yAxis: { type: 'value', minInterval: 1 },
      series: [
        {
          type: 'bar',
          barMaxWidth: xData.length > 6 ? 20 : 32,
          data: items.map((s, i) => ({
            value: s.count,
            statusKey: s.key,
            itemStyle: {
              color: props.colorFor?.(s.key, i) ?? '#3370FF',
              borderRadius: [4, 4, 0, 0],
            },
          })),
        },
      ],
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
  () => props.breakdown,
  async () => {
    await nextTick();
    render();
  },
  { deep: true }
);
</script>

<style scoped>
.chart-box {
  width: 100%;
}
</style>
