<template>
  <n-space align="center" justify="space-between" :size="8" class="workbench-todo-row">
    <div class="workbench-todo-row__main">
      <router-link v-if="mode === 'link'" class="workbench-todo-row__label" :to="to!">
        <n-tooltip trigger="hover" :disabled="!label">
          <template #trigger>
            <span class="workbench-todo-row__text">{{ label }}</span>
          </template>
          {{ label }}
        </n-tooltip>
      </router-link>
      <button
        v-else
        type="button"
        class="workbench-todo-row__label workbench-todo-row__label--action"
        @click="emit('click')"
      >
        <n-tooltip trigger="hover" :disabled="!label">
          <template #trigger>
            <span class="workbench-todo-row__text">{{ label }}</span>
          </template>
          {{ label }}
        </n-tooltip>
      </button>
    </div>
    <n-space
      v-if="columns?.length || meta || tag"
      align="center"
      :size="8"
      class="workbench-todo-row__extra"
      :wrap="true"
    >
      <n-tag
        v-for="col in columns"
        :key="col.label"
        :type="col.type ?? 'default'"
        size="small"
        round
        :bordered="false"
        class="workbench-todo-row__chip"
      >
        {{ col.value }}
      </n-tag>
      <n-text v-if="meta" depth="3" class="workbench-todo-row__meta">{{ meta }}</n-text>
      <n-tag
        v-if="tag"
        :type="tagType ?? 'default'"
        size="small"
        round
        :bordered="false"
        class="workbench-todo-row__chip"
      >
        {{ tag }}
      </n-tag>
    </n-space>
  </n-space>
</template>

<script setup lang="ts">
import type { TagProps } from 'naive-ui';
import { NSpace, NTag, NText, NTooltip } from 'naive-ui';
import type { RouteLocationRaw } from 'vue-router';

withDefaults(
  defineProps<{
    label: string;
    mode?: 'link' | 'action';
    to?: RouteLocationRaw;
    tag?: string;
    tagType?: TagProps['type'];
    meta?: string;
    columns?: { label: string; value: string; type?: TagProps['type'] }[];
  }>(),
  { mode: 'link' }
);

const emit = defineEmits<{
  click: [];
}>();
</script>

<style scoped>
.workbench-todo-row {
  width: 100%;
  min-width: 0;
}
.workbench-todo-row__main {
  flex: 1;
  min-width: 0;
}
.workbench-todo-row__extra {
  flex-shrink: 0;
}
.workbench-todo-row__label {
  display: block;
  max-width: 100%;
  color: var(--n-primary-color);
  text-decoration: none;
  font-size: 13px;
  line-height: 1.5;
  text-align: left;
}
.workbench-todo-row__label--action {
  border: none;
  background: transparent;
  padding: 0;
  cursor: pointer;
}
.workbench-todo-row__label:hover,
.workbench-todo-row__label--action:hover {
  text-decoration: underline;
}
.workbench-todo-row__text {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.workbench-todo-row__meta {
  font-size: 12px;
  white-space: nowrap;
}
.workbench-todo-row__chip {
  font-size: 12px;
}
</style>
