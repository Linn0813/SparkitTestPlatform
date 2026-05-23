<template>
  <n-card size="small" class="todo-section" :class="{ 'todo-section--stretch': stretch }">
    <template #header>
      <n-space align="center" justify="space-between" style="width: 100%" :wrap="false">
        <n-space align="center" :size="8" :wrap="false" style="min-width: 0">
          <n-text strong>{{ title }}</n-text>
          <n-tag size="small" round :bordered="false">{{ count }}</n-tag>
          <slot name="header-extra" />
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

    <div v-if="empty" class="todo-empty">
      <n-empty description="暂无" size="small" />
    </div>
    <div v-else class="todo-list">
      <slot />
    </div>

    <template v-if="$slots.footer" #footer>
      <div class="todo-footer">
        <slot name="footer" />
      </div>
    </template>
  </n-card>
</template>

<script setup lang="ts">
import { NButton, NCard, NEmpty, NSpace, NTag, NText } from 'naive-ui';
import { useRouter, type RouteLocationRaw } from 'vue-router';

defineProps<{
  title: string;
  count: number;
  empty: boolean;
  viewAllTo?: RouteLocationRaw;
  stretch?: boolean;
}>();

const router = useRouter();
</script>

<style scoped>
.todo-section :deep(.n-card-header) {
  padding-bottom: 8px;
}
.todo-section--stretch {
  height: 100%;
  display: flex;
  flex-direction: column;
}
.todo-section--stretch :deep(.n-card__content) {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.todo-empty {
  min-height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.todo-section--stretch .todo-empty,
.todo-section--stretch .todo-list {
  flex: 1;
  min-height: 0;
}
.todo-list {
  margin-top: 0;
  border: 1px solid var(--n-border-color);
  border-radius: var(--n-border-radius);
  overflow: hidden;
}
.todo-list :deep(.todo-item) {
  padding: 8px 12px;
  min-width: 0;
}
.todo-list :deep(.todo-item + .todo-item) {
  border-top: 1px solid var(--n-border-color);
}
.todo-list :deep(.todo-item:hover) {
  background-color: var(--n-action-color);
}
.todo-footer {
  display: flex;
  justify-content: flex-end;
}
</style>
