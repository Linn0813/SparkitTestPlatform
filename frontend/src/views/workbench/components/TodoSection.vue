<template>
  <n-card size="small" class="todo-section">
    <template #header>
      <n-space align="center" justify="space-between" style="width: 100%">
        <n-space align="center" :size="8">
          <n-text strong>{{ title }}</n-text>
          <n-tag size="small" round :bordered="false">{{ count }}</n-tag>
        </n-space>
        <n-button
          v-if="viewAllTo"
          text
          type="primary"
          size="small"
          @click="router.push(viewAllTo)"
        >
          查看全部
        </n-button>
      </n-space>
    </template>
    <n-empty v-if="empty" description="暂无" size="small" />
    <n-list v-else bordered hoverable class="todo-list">
      <slot />
    </n-list>
  </n-card>
</template>

<script setup lang="ts">
import { NButton, NCard, NEmpty, NList, NSpace, NTag, NText } from 'naive-ui';
import { useRouter, type RouteLocationRaw } from 'vue-router';

defineProps<{
  title: string;
  count: number;
  empty: boolean;
  viewAllTo?: RouteLocationRaw;
}>();

const router = useRouter();
</script>

<style scoped>
.todo-section :deep(.n-card-header) {
  padding-bottom: 8px;
}
.todo-list {
  margin-top: 0;
}
.todo-list :deep(.n-list-item) {
  padding: 8px 12px;
}
.todo-list :deep(.n-list-item__main) {
  font-size: 13px;
}
</style>
