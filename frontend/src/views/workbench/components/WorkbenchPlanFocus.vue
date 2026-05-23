<template>
  <n-card size="small">
    <template #header>
      <n-text strong>计划维度</n-text>
    </template>
    <n-grid :cols="24" :x-gap="12" responsive="screen">
      <n-gi :span="8" class="plan-focus-col">
        <n-card size="small" title="未完计划" class="plan-focus-inner-card">
          <div class="plan-focus-body" :class="{ 'plan-focus-body--empty': !plans.length }">
            <n-empty v-if="!plans.length" description="暂无未开始或进行中的计划" size="small" />
            <n-list v-else bordered size="small">
            <n-list-item v-for="p in plans" :key="p.id">
              <n-space align="center" justify="space-between" style="width: 100%" wrap :size="8">
                <n-space align="center" :size="8" wrap>
                  <router-link class="plan-link" :to="{ name: 'plan-detail', params: { id: p.id } }">
                    {{ p.name }}
                  </router-link>
                  <n-tag size="small" :bordered="false" :type="planStatusTagType(p.status)">
                    {{ planStatusLabel(p.status) }}
                  </n-tag>
                  <n-text v-if="p.version" depth="3" style="font-size: 13px">
                    {{ formatVersionDisplay(p.version) }}
                  </n-text>
                  <n-text v-else depth="3" style="font-size: 13px">未关联版本</n-text>
                </n-space>
                <n-text depth="3" style="font-size: 13px">{{ planProgressText(p) }}</n-text>
              </n-space>
            </n-list-item>
          </n-list>
          </div>
        </n-card>
      </n-gi>
      <n-gi :span="16" class="plan-focus-col">
        <WorkbenchPlanChart
          ref="planChartRef"
          class="plan-focus-inner-card"
          title="用例执行"
          :chart="focus?.execution_chart"
        />
      </n-gi>
    </n-grid>
  </n-card>
</template>

<script setup lang="ts">
import { NCard, NEmpty, NGi, NGrid, NList, NListItem, NSpace, NTag, NText } from 'naive-ui';
import { computed, defineAsyncComponent, ref } from 'vue';
import { planStatusLabel, planStatusTagType } from '@/constants/planStatus';
import { WORKBENCH_OVERVIEW_CHART_HEIGHT } from '@/constants/workbenchCharts';
import type { ActivePlanBrief, PlanFocus } from '@/types/business';
import { formatVersionDisplay } from '@/utils/versionLabel';

const WorkbenchPlanChart = defineAsyncComponent(() => import('./WorkbenchPlanChart.vue'));

const props = defineProps<{
  focus: PlanFocus | undefined;
}>();

const planChartRef = ref<{ resize?: () => void } | null>(null);

const plans = computed(() => props.focus?.unfinished_plans ?? []);

const chartContentHeight = `${WORKBENCH_OVERVIEW_CHART_HEIGHT}px`;

function planProgressText(p: ActivePlanBrief) {
  const executed = p.case_total - p.not_run;
  const rate = executed && p.pass_rate != null ? `，通过率 ${p.pass_rate}%` : '';
  return `用例 ${p.case_total}，未执行 ${p.not_run}${rate}`;
}

function resize() {
  planChartRef.value?.resize?.();
}

defineExpose({ resize });
</script>

<style scoped>
.plan-focus-col {
  display: flex;
}
.plan-focus-inner-card {
  flex: 1;
  width: 100%;
  min-width: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
}
.plan-focus-inner-card :deep(.n-card__content) {
  min-height: v-bind(chartContentHeight);
  display: flex;
  flex-direction: column;
}
.plan-focus-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: v-bind(chartContentHeight);
}
.plan-focus-body--empty {
  align-items: center;
  justify-content: center;
}
.plan-focus-col :deep(.chart-box),
.plan-focus-col :deep(.chart-placeholder) {
  flex: 1;
  min-height: v-bind(chartContentHeight);
}
.plan-link {
  color: var(--n-primary-color);
  text-decoration: none;
}
.plan-link:hover {
  text-decoration: underline;
}
</style>
