<template>
  <div class="schedule-toolbar">
    <div class="schedule-toolbar__left">
      <span class="schedule-toolbar__page-title">{{ pageTitle }}</span>
      <span class="schedule-toolbar__divider" aria-hidden="true" />
      <n-button-group size="small">
        <n-button quaternary :disabled="loading" @click="emit('prev')">上一段</n-button>
        <n-button quaternary :disabled="loading" @click="emit('next')">下一段</n-button>
      </n-button-group>
    </div>
    <div class="schedule-toolbar__right">
      <div v-if="title || subtitle" class="schedule-toolbar__range">
        <span v-if="title" class="schedule-toolbar__range-title">{{ title }}</span>
        <span v-if="title && subtitle" class="schedule-toolbar__range-dot">·</span>
        <span v-if="subtitle" class="schedule-toolbar__range-sub">{{ subtitle }}</span>
      </div>
      <slot name="extra" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { NButton, NButtonGroup } from 'naive-ui';

defineProps<{
  pageTitle: string;
  title: string;
  subtitle?: string;
  loading?: boolean;
}>();

const emit = defineEmits<{
  prev: [];
  next: [];
}>();
</script>

<style scoped>
.schedule-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  width: 100%;
  min-height: 36px;
}
.schedule-toolbar__left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}
.schedule-toolbar__page-title {
  font-size: 16px;
  font-weight: 600;
  line-height: 1.4;
  color: var(--n-text-color-1);
  letter-spacing: 0.02em;
}
.schedule-toolbar__divider {
  width: 1px;
  height: 18px;
  background: var(--schedule-border, #e5e6eb);
  flex-shrink: 0;
}
.schedule-toolbar__right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}
.schedule-toolbar__range {
  display: inline-flex;
  align-items: center;
  flex-wrap: nowrap;
  gap: 8px;
  padding: 6px 12px;
  border-radius: 8px;
  background: var(--schedule-header-bg, #f5f6f8);
  border: 1px solid var(--schedule-border, #e5e6eb);
  font-size: 13px;
  line-height: 1.4;
  color: var(--n-text-color-2);
  flex-shrink: 0;
}
.schedule-toolbar__range-title {
  font-weight: 600;
  color: var(--n-text-color-1);
}
.schedule-toolbar__range-dot {
  color: var(--n-text-color-3);
  user-select: none;
}
.schedule-toolbar__range-sub {
  color: var(--n-text-color-2);
  font-variant-numeric: tabular-nums;
}
</style>
