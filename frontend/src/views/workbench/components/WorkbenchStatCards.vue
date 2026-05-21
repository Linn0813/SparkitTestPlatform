<template>
  <n-grid :cols="4" :x-gap="12" :y-gap="12" responsive="screen">
    <n-gi v-for="card in cards" :key="card.key">
      <n-card size="small" hoverable class="stat-card" @click="router.push(card.to)">
        <n-statistic :label="card.label" :value="card.value" />
      </n-card>
    </n-gi>
  </n-grid>
</template>

<script setup lang="ts">
import { NCard, NGi, NGrid, NStatistic } from 'naive-ui';
import { computed } from 'vue';
import { useRouter, type RouteLocationRaw } from 'vue-router';
import type { DashboardSummary } from '@/types/business';

const props = defineProps<{
  summary: DashboardSummary | null | undefined;
}>();

const router = useRouter();

const cards = computed(() => {
  const s = props.summary;
  return [
    {
      key: 'versions',
      label: '版本',
      value: s?.version_count ?? 0,
      to: { name: 'versions' } as RouteLocationRaw,
    },
    {
      key: 'requirements',
      label: '需求',
      value: s?.requirement_count ?? 0,
      to: { name: 'requirements' } as RouteLocationRaw,
    },
    {
      key: 'cases',
      label: '用例',
      value: s?.case_count ?? 0,
      to: { name: 'cases' } as RouteLocationRaw,
    },
    {
      key: 'bugs',
      label: '缺陷',
      value: s?.bug_count ?? 0,
      to: { name: 'bugs' } as RouteLocationRaw,
    },
  ];
});
</script>

<style scoped>
.stat-card {
  cursor: pointer;
}
.stat-card :deep(.n-statistic-value) {
  font-size: 22px;
}
</style>
