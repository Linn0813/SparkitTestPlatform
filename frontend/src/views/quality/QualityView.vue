<template>
  <n-space vertical size="large">
    <!-- 版本筛选 -->
    <n-card :bordered="false" content-style="padding: 12px 16px">
      <n-space align="center">
        <n-text>版本筛选：</n-text>
        <n-select
          v-model:value="selectedVersionIds"
          multiple
          :options="versionOptions"
          placeholder="全部版本"
          clearable
          style="min-width: 320px"
          :loading="versionsLoading"
          @update:value="loadAll"
        />
        <n-button @click="loadAll">刷新</n-button>
      </n-space>
    </n-card>

    <!-- ── 顶部三个核心指标 ── -->
    <n-grid :cols="3" :x-gap="16">
      <n-gi>
        <n-card title="漏测率" size="small">
          <template #header-extra>
            <n-text depth="3" style="font-size: 12px">线上 Bug / 总 Bug，目标 &lt; 10%</n-text>
          </template>
          <n-spin :show="leakageLoading">
            <div v-if="leakage" style="display: flex; align-items: baseline; gap: 8px">
              <n-text :style="{ fontSize: '32px', fontWeight: 700, color: leakageColor }">
                {{ leakage.leakage_rate }}%
              </n-text>
              <n-text depth="3">{{ leakage.online_bugs }} / {{ leakage.total_bugs }} 个</n-text>
            </div>
          </n-spin>
        </n-card>
      </n-gi>
      <n-gi>
        <n-card title="Bug 修复反弹率" size="small">
          <template #header-extra>
            <n-text depth="3" style="font-size: 12px">反弹 / 已修复，目标 &lt; 5%</n-text>
          </template>
          <n-spin :show="reflowLoading">
            <div v-if="reflow" style="display: flex; align-items: baseline; gap: 8px">
              <n-text :style="{ fontSize: '32px', fontWeight: 700, color: reflowColor }">
                {{ reflow.reflow_rate }}%
              </n-text>
              <n-text depth="3">{{ reflow.reflowed_bugs }} / {{ reflow.resolved_bugs }} 个</n-text>
            </div>
          </n-spin>
        </n-card>
      </n-gi>
      <n-gi>
        <n-card title="严重 Bug 平均响应时效" size="small">
          <template #header-extra>
            <n-text depth="3" style="font-size: 12px">目标 &lt; 4 小时</n-text>
          </template>
          <n-spin :show="responseLoading">
            <div v-if="responseTime">
              <div style="display: flex; align-items: baseline; gap: 8px">
                <n-text :style="{ fontSize: '32px', fontWeight: 700, color: responseColor }">
                  {{ responseTime.avg_response_hours != null ? responseTime.avg_response_hours + 'h' : '—' }}
                </n-text>
              </div>
              <n-text depth="3" style="font-size: 12px">
                未处理 {{ unhandledCount }} 个
                <n-text v-if="unhandledCount > 0" type="error">⚠️</n-text>
              </n-text>
            </div>
          </n-spin>
        </n-card>
      </n-gi>
    </n-grid>

    <!-- ── 高优需求停滞预警 ── -->
    <n-card size="small">
      <template #header>
        <n-space align="center" size="small">
          高优需求停滞预警
          <n-spin v-if="staleLoading" size="small" />
          <template v-else>
            <n-tag v-if="staleRequirements.length > 0" type="error" size="small">{{ staleRequirements.length }} 个</n-tag>
            <n-tag v-else type="success" size="small">无停滞</n-tag>
          </template>
        </n-space>
      </template>
      <n-empty v-if="!staleLoading && staleRequirements.length === 0" description="✓ 无高优停滞需求" />
      <n-data-table
        v-else-if="staleRequirements.length > 0"
        :columns="staleColumns"
        :data="staleRequirements"
        :row-key="(r: StaleRequirementItem) => r.requirement_id"
        size="small"
      />
    </n-card>

    <!-- ── Bug 来源趋势 + 需求交付健康度 ── -->
    <n-grid :cols="2" :x-gap="16">
      <n-gi>
        <n-card title="Bug 来源分布（按版本）" size="small">
          <n-spin :show="sourceTrendLoading">
            <n-empty v-if="!sourceTrendLoading && sourceTrend.length === 0" description="暂无数据" />
            <div v-else ref="sourceChartRef" style="height: 240px" />
          </n-spin>
        </n-card>
      </n-gi>
      <n-gi>
        <n-card title="需求交付健康度" size="small">
          <n-spin :show="deliveryLoading">
            <n-empty v-if="!deliveryLoading && deliveryHealth.length === 0" description="暂无数据" />
            <n-data-table
              v-else-if="deliveryHealth.length > 0"
              :columns="deliveryColumns"
              :data="deliveryHealth"
              :row-key="(r: VersionDeliveryHealth) => r.version_id"
              size="small"
            />
          </n-spin>
        </n-card>
      </n-gi>
    </n-grid>

    <!-- ── 需求 Bug 密度排行 ── -->
    <n-card title="需求 Bug 密度排行" size="small">
      <template #header-extra>
        <n-text depth="3" style="font-size: 12px">密度 = Bug 数 / Story Points，越高说明实现质量越差</n-text>
      </template>
      <n-spin :show="densityLoading">
        <n-empty v-if="!densityLoading && reqDensity.length === 0" description="暂无数据" />
        <n-data-table
          v-else-if="reqDensity.length > 0"
          :columns="densityColumns"
          :data="reqDensity"
          :row-key="(r: RequirementBugDensityItem) => r.requirement_id"
          size="small"
        />
      </n-spin>
    </n-card>

    <!-- ── 研发 Bug 引入率 + 严重 Bug 响应详情 ── -->
    <n-grid :cols="2" :x-gap="16">
      <n-gi>
        <n-card title="研发人员 Bug 引入率" size="small">
          <template #header-extra>
            <n-text depth="3" style="font-size: 12px">归一化到 Story Points</n-text>
          </template>
          <n-spin :show="devRateLoading">
            <n-empty v-if="!devRateLoading && devRate.length === 0" description="暂无数据" />
            <n-data-table
              v-else-if="devRate.length > 0"
              :columns="devRateColumns"
              :data="devRate"
              :row-key="(r: DeveloperBugRateItem) => r.user_id"
              size="small"
            />
          </n-spin>
        </n-card>
      </n-gi>
      <n-gi>
        <n-card title="严重 Bug 响应时效" size="small">
          <n-spin :show="responseLoading">
            <n-empty v-if="!responseLoading && responseTime?.items.length === 0" description="暂无严重 Bug" />
            <n-data-table
              v-else-if="responseTime && responseTime.items.length > 0"
              :columns="responseColumns"
              :data="responseTime.items"
              :row-key="(r: BugResponseTimeItem) => r.bug_id"
              size="small"
            />
          </n-spin>
        </n-card>
      </n-gi>
    </n-grid>

    <!-- ── Bug 修复反弹详情 ── -->
    <n-card v-if="reflow && reflow.reflow_bug_list.length > 0" title="Bug 修复反弹详情" size="small">
      <n-data-table
        :columns="reflowColumns"
        :data="reflow.reflow_bug_list"
        :row-key="(r: any) => r.bug_num"
        size="small"
      />
    </n-card>

  </n-space>
</template>

<script setup lang="ts">
import { computed, h, nextTick, onMounted, ref, watch } from 'vue';
import * as echarts from 'echarts/core';
import { BarChart } from 'echarts/charts';
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import {
  NButton, NCard, NDataTable, NEmpty, NGi, NGrid, NSelect, NSpace, NSpin, NTag, NText,
  type DataTableColumns,
} from 'naive-ui';
import { qualityApi } from '@/api/quality';
import type {
  BugResponseTimeItem,
  BugReflowRateOut,
  BugResponseTimeOut,
  BugSourceTrendItem,
  DeveloperBugRateItem,
  LeakageRateOut,
  RequirementBugDensityItem,
  StaleRequirementItem,
  VersionBrief,
  VersionDeliveryHealth,
} from '@/api/quality';
import { useContextStore } from '@/stores/context';

echarts.use([BarChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer]);

const ctx = useContextStore();

const selectedVersionIds = ref<string[]>([]);
const versions = ref<VersionBrief[]>([]);
const versionsLoading = ref(false);

const leakage = ref<LeakageRateOut | null>(null);
const leakageLoading = ref(false);

const reflow = ref<BugReflowRateOut | null>(null);
const reflowLoading = ref(false);

const responseTime = ref<BugResponseTimeOut | null>(null);
const responseLoading = ref(false);

const staleRequirements = ref<StaleRequirementItem[]>([]);
const staleLoading = ref(false);

const sourceTrend = ref<BugSourceTrendItem[]>([]);
const sourceTrendLoading = ref(false);

const deliveryHealth = ref<VersionDeliveryHealth[]>([]);
const deliveryLoading = ref(false);

const reqDensity = ref<RequirementBugDensityItem[]>([]);
const densityLoading = ref(false);

const devRate = ref<DeveloperBugRateItem[]>([]);
const devRateLoading = ref(false);

const sourceChartRef = ref<HTMLElement | null>(null);
let sourceChart: echarts.ECharts | null = null;

const versionOptions = computed(() =>
  versions.value.map((v) => ({ label: v.name, value: v.id }))
);
const vids = computed(() => selectedVersionIds.value.length > 0 ? selectedVersionIds.value : undefined);

const leakageColor = computed(() => {
  const r = leakage.value?.leakage_rate ?? 0;
  return r >= 20 ? '#d03050' : r >= 10 ? '#f0a020' : '#18a058';
});
const reflowColor = computed(() => {
  const r = reflow.value?.reflow_rate ?? 0;
  return r >= 10 ? '#d03050' : r >= 5 ? '#f0a020' : '#18a058';
});
const responseColor = computed(() => {
  const h = responseTime.value?.avg_response_hours;
  if (h == null) return '#333';
  return h > 24 ? '#d03050' : h > 4 ? '#f0a020' : '#18a058';
});
const unhandledCount = computed(() =>
  responseTime.value?.items.filter((i) => i.warning_level === 'unhandled').length ?? 0
);

const priorityLabel: Record<string, string> = { p00: 'P00', p0: 'P0', p1: 'P1' };
const statusLabel: Record<string, string> = {
  designing: '设计中', developing: '开发中', testing: '测试中', pending_release: '待上线',
};

const staleColumns: DataTableColumns<StaleRequirementItem> = [
  {
    title: '优先级', key: 'priority', width: 72,
    render: (r) => h(NTag, { size: 'small', type: r.priority === 'p00' ? 'error' : 'warning' }, () => priorityLabel[r.priority] ?? r.priority),
  },
  { title: '需求', key: 'title', ellipsis: { tooltip: true }, render: (r) => `#${r.requirement_num} ${r.title}` },
  { title: '当前状态', key: 'status', width: 90, render: (r) => statusLabel[r.status] ?? r.status },
  {
    title: '停滞天数', key: 'stale_days', width: 90,
    render: (r) => h(NText, { type: r.warning_level === 'danger' ? 'error' : 'warning' }, () => `${r.stale_days} 天`),
  },
  {
    title: '负责人', key: 'owner', width: 180,
    render: (r) => [r.frontend_rd_name, r.backend_rd_name, r.qa_name].filter(Boolean).join(' / ') || '—',
  },
];

const deliveryColumns: DataTableColumns<VersionDeliveryHealth> = [
  { title: '版本', key: 'version_name', ellipsis: { tooltip: true } },
  { title: '需求总数', key: 'total_requirements', width: 80 },
  { title: '已完成', key: 'completed_requirements', width: 72 },
  {
    title: '未完成', key: 'incomplete_requirements', width: 72,
    render: (r) => h(NText, { type: r.at_risk ? 'error' : 'default' }, () => String(r.incomplete_requirements)),
  },
  {
    title: '完成率', key: 'completion_rate', width: 80,
    render: (r) => h(NText, { type: r.completion_rate >= 100 ? 'success' : r.at_risk ? 'error' : 'default' }, () => `${r.completion_rate}%`),
  },
  {
    title: '风险', key: 'at_risk', width: 90,
    render: (r) => r.at_risk ? h(NTag, { size: 'small', type: 'error' }, () => '⚠️ 带病上线') : '—',
  },
];

const densityColumns: DataTableColumns<RequirementBugDensityItem> = [
  { title: '需求', key: 'title', ellipsis: { tooltip: true }, render: (r) => `#${r.requirement_num} ${r.title}` },
  {
    title: '优先级', key: 'priority', width: 72,
    render: (r) => h(NTag, { size: 'small' }, () => priorityLabel[r.priority] ?? r.priority),
  },
  { title: 'Bug 数', key: 'bug_count', width: 72 },
  { title: 'Story Points', key: 'estimate_points', width: 110, render: (r) => r.estimate_points || '—' },
  {
    title: 'Bug 密度', key: 'density', width: 90,
    render: (r) => r.density != null
      ? h(NText, { type: r.density >= 1 ? 'error' : r.density >= 0.5 ? 'warning' : 'default' }, () => String(r.density))
      : h(NText, { depth: 3 }, () => '未填 SP'),
  },
];

const devRateColumns: DataTableColumns<DeveloperBugRateItem> = [
  { title: '研发', key: 'user_name', width: 100 },
  { title: '负责需求', key: 'requirement_count', width: 80 },
  { title: 'Bug 数', key: 'bug_count', width: 72 },
  { title: 'Story Points', key: 'estimate_points', width: 110, render: (r) => r.estimate_points || '—' },
  {
    title: '引入率', key: 'bug_rate', width: 80,
    render: (r) => r.bug_rate != null
      ? h(NText, { type: r.bug_rate >= 1 ? 'error' : r.bug_rate >= 0.5 ? 'warning' : 'default' }, () => String(r.bug_rate))
      : h(NText, { depth: 3 }, () => '未填 SP'),
  },
];

const responseColumns: DataTableColumns<BugResponseTimeItem> = [
  { title: 'Bug', key: 'title', ellipsis: { tooltip: true }, render: (r) => `#${r.bug_num} ${r.title}` },
  { title: '处理人', key: 'assignee_name', width: 90, render: (r) => r.assignee_name ?? '未分配' },
  {
    title: '响应时效', key: 'first_response_hours', width: 100,
    render: (r) => {
      if (r.warning_level === 'unhandled') return h(NTag, { size: 'small', type: 'error' }, () => '未处理');
      const type = r.warning_level === 'danger' ? 'error' : r.warning_level === 'warning' ? 'warning' : 'success';
      return h(NText, { type }, () => `${r.first_response_hours}h`);
    },
  },
];

const reflowColumns = [
  { title: 'Bug', key: 'title', ellipsis: { tooltip: true }, render: (r: any) => `#${r.bug_num} ${r.title}` },
  { title: '处理人', key: 'assignee_name', width: 100, render: (r: any) => r.assignee_name ?? '—' },
  { title: '反弹次数', key: 'reflow_count', width: 80 },
];

function renderSourceChart() {
  if (!sourceChartRef.value || sourceTrend.value.length === 0) return;
  if (!sourceChart) sourceChart = echarts.init(sourceChartRef.value);
  const trend = sourceTrend.value;
  sourceChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { data: ['线上反馈', '内部体验', '需求测试', '其他'], bottom: 0 },
    grid: { left: 40, right: 10, top: 10, bottom: 40 },
    xAxis: { type: 'category', data: trend.map((t) => t.label) },
    yAxis: { type: 'value', minInterval: 1 },
    series: [
      { name: '线上反馈', type: 'bar', stack: 'total', data: trend.map((t) => t.online), color: '#d03050' },
      { name: '内部体验', type: 'bar', stack: 'total', data: trend.map((t) => t.internal), color: '#f0a020' },
      { name: '需求测试', type: 'bar', stack: 'total', data: trend.map((t) => t.testing), color: '#18a058' },
      { name: '其他', type: 'bar', stack: 'total', data: trend.map((t) => t.other), color: '#aaa' },
    ],
  });
}

async function fetch<T>(
  loadingRef: { value: boolean },
  dataRef: { value: T },
  fn: () => Promise<{ data: T }>
) {
  loadingRef.value = true;
  try {
    const { data } = await fn();
    dataRef.value = data;
  } catch {
    // 单个指标失败不影响其他
  } finally {
    loadingRef.value = false;
  }
}

async function loadVersions() {
  versionsLoading.value = true;
  try {
    const { data } = await qualityApi.getVersions();
    versions.value = data;
  } finally {
    versionsLoading.value = false;
  }
}

async function loadAll() {
  if (!ctx.projectId) return;
  const v = vids.value;

  // 并发请求所有指标，各自独立 loading
  await Promise.allSettled([
    fetch(leakageLoading, leakage, () => qualityApi.getLeakageRate(v)),
    fetch(reflowLoading, reflow, () => qualityApi.getReflowRate(v)),
    fetch(responseLoading, responseTime, () => qualityApi.getBugResponseTime(v)),
    fetch(staleLoading, staleRequirements, () => qualityApi.getStaleRequirements()),
    fetch(sourceTrendLoading, sourceTrend, async () => {
      const res = await qualityApi.getBugSourceTrend(v);
      await nextTick();
      renderSourceChart();
      return res;
    }),
    fetch(deliveryLoading, deliveryHealth, () => qualityApi.getVersionDeliveryHealth(v)),
    fetch(densityLoading, reqDensity, () => qualityApi.getRequirementBugDensity(v)),
    fetch(devRateLoading, devRate, () => qualityApi.getDeveloperBugRate(v)),
  ]);
}

onMounted(async () => {
  await loadVersions();
  await loadAll();
});

watch(() => ctx.projectId, async () => {
  selectedVersionIds.value = [];
  await loadVersions();
  await loadAll();
});
</script>
