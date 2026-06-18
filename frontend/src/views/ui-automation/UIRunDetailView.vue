<template>
  <n-space vertical size="large">
    <n-page-header :title="run ? `执行记录 · ${runStatusLabel(run.status)}` : '执行记录'" @back="router.back()">
      <template #extra>
        <n-space>
          <n-tag :type="run ? runStatusTagType(run.status) : 'default'" size="medium">
            {{ run ? runStatusLabel(run.status) : '—' }}
          </n-tag>
          <n-button v-if="run && isActive" size="small" @click="poll">刷新</n-button>
        </n-space>
      </template>
    </n-page-header>

    <n-spin :show="loading">
      <n-card v-if="run" title="执行信息" size="small">
        <n-descriptions :column="3" label-placement="left" bordered size="small">
          <n-descriptions-item label="用例 ID">{{ run.case_id }}</n-descriptions-item>
          <n-descriptions-item label="App 包 ID">{{ run.app_id }}</n-descriptions-item>
          <n-descriptions-item label="Runner">{{ run.runner_id ?? '未分配' }}</n-descriptions-item>
          <n-descriptions-item label="开始时间">{{ run.started_at ? formatDate(run.started_at) : '—' }}</n-descriptions-item>
          <n-descriptions-item label="结束时间">{{ run.finished_at ? formatDate(run.finished_at) : '—' }}</n-descriptions-item>
          <n-descriptions-item label="创建时间">{{ formatDate(run.created_at) }}</n-descriptions-item>
          <n-descriptions-item v-if="run.error_message" label="错误信息" :span="3">
            <n-text type="error">{{ firstLine(run.error_message) }}</n-text>
          </n-descriptions-item>
        </n-descriptions>
      </n-card>

      <n-card title="执行录屏" size="small" style="margin-top: 12px" v-if="run?.video_url">
        <video :src="run.video_url" controls style="width: 100%; max-width: 480px; border-radius: 4px" />
      </n-card>

      <n-card title="步骤结果" size="small" style="margin-top: 12px">
        <n-empty v-if="!run || run.step_results.length === 0" description="暂无步骤数据" />
        <n-timeline v-else>
          <n-timeline-item
            v-for="(step, i) in run.step_results"
            :key="step.id"
            :type="stepTimelineType(step.status)"
          >
            <template #header>
              <n-space align="center" size="small">
                <n-text strong>{{ installStepLabel(i) }}</n-text>
                <n-tag :type="stepTagType(step.status)" size="small" :bordered="false">
                  {{ stepStatusLabel(step.status) }}
                </n-tag>
                <n-text v-if="step.duration_ms != null" depth="3" style="font-size: 12px">
                  {{ step.duration_ms }} ms
                </n-text>
              </n-space>
            </template>
            <n-text v-if="step.error_message" type="error" style="font-size: 13px">
              {{ firstLine(step.error_message) }}
            </n-text>
            <div v-if="step.screenshot_url" style="margin-top: 8px">
              <n-image :src="step.screenshot_url" width="240" lazy />
            </div>
          </n-timeline-item>
        </n-timeline>
      </n-card>
    </n-spin>
  </n-space>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  NButton,
  NCard,
  NDescriptions,
  NDescriptionsItem,
  NEmpty,
  NImage,
  NPageHeader,
  NSpace,
  NSpin,
  NTag,
  NText,
  NTimeline,
  NTimelineItem,
} from 'naive-ui';
import { getRun } from '@/api/uiAutomation';
import type { UITestRun, UIRunStatus, UIStepStatus } from '@/types/business';

const route = useRoute();
const router = useRouter();
const run = ref<UITestRun | null>(null);
const loading = ref(false);

function firstLine(msg: string) {
  // 取第一行，去掉 "Message: " 前缀和堆栈
  const line = msg.split('\n')[0].replace(/^Message:\s*/i, '').trim();
  // NoSuchElementError: An element could not be located... 只取冒号前的描述
  const match = line.match(/^([A-Za-z]+Error):\s*(.+)/);
  return match ? match[2] : line;
}

const INSTALL_STEP_LABELS: Record<number, string> = {
  0: '下载 App',
  1: '安装 App',
  2: '启动 App',
};

function installStepLabel(index: number): string {
  return INSTALL_STEP_LABELS[index] ?? `步骤 ${index - 2}`;
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  });
}

function runStatusLabel(s: UIRunStatus) {
  return { pending: '等待中', running: '执行中', passed: '通过', failed: '失败', error: '异常' }[s] ?? s;
}

function runStatusTagType(s: UIRunStatus): 'default' | 'info' | 'success' | 'error' | 'warning' {
  return { pending: 'default', running: 'info', passed: 'success', failed: 'error', error: 'warning' }[s] as 'default' | 'info' | 'success' | 'error' | 'warning' ?? 'default';
}

function stepStatusLabel(s: UIStepStatus) {
  return { pending: '等待', passed: '通过', failed: '失败', skipped: '跳过' }[s] ?? s;
}

function stepTagType(s: UIStepStatus): 'default' | 'success' | 'error' | 'warning' {
  return { pending: 'default', passed: 'success', failed: 'error', skipped: 'warning' }[s] as 'default' | 'success' | 'error' | 'warning' ?? 'default';
}

function stepTimelineType(s: UIStepStatus): 'default' | 'success' | 'error' | 'warning' {
  return stepTagType(s);
}

const isActive = computed(() =>
  run.value?.status === 'pending' || run.value?.status === 'running'
);

async function poll() {
  const id = route.params.id as string;
  if (!id) return;
  loading.value = !run.value;
  try {
    const { data } = await getRun(id);
    run.value = data;
  } finally {
    loading.value = false;
  }
}

let timer: ReturnType<typeof setInterval> | null = null;

function startPolling() {
  timer = setInterval(() => {
    if (isActive.value) poll();
    else stopPolling();
  }, 3000);
}

function stopPolling() {
  if (timer) { clearInterval(timer); timer = null; }
}

onMounted(async () => {
  await poll();
  if (isActive.value) startPolling();
});

onUnmounted(stopPolling);
</script>
