<template>
  <n-drawer :show="show" :width="420" placement="right" @update:show="(v) => emit('update:show', v)">
    <n-drawer-content :title="drawerTitle" closable>
      <n-empty v-if="!items.length" description="暂无未排期任务" />
      <div v-else class="unsched-list">
        <div v-for="item in items" :key="item.id" class="unsched-card">
          <div class="unsched-card__title">{{ cardTitle(item) }}</div>
          <div class="unsched-card__meta">
            <span class="unsched-card__phase">{{ cardPhase(item) }}</span>
            <span v-if="cardTask(item)" class="unsched-card__task">{{ cardTask(item) }}</span>
          </div>
          <n-button text type="primary" size="small" @click="emit('open-item', item)">
            {{ openButtonLabel(item) }}
          </n-button>
        </div>
      </div>
    </n-drawer-content>
  </n-drawer>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { NButton, NDrawer, NDrawerContent, NEmpty } from 'naive-ui';
import type { MemberScheduleItem, MemberScheduleRow } from '@/types/business';

const props = defineProps<{
  show: boolean;
  member: MemberScheduleRow | null;
}>();

const emit = defineEmits<{
  'update:show': [value: boolean];
  'open-item': [item: MemberScheduleItem];
}>();

const items = computed(() => props.member?.unscheduled_items ?? []);

const drawerTitle = computed(() =>
  props.member ? `${props.member.name} · 未排期 (${items.value.length})` : '未排期'
);

function isBugItem(item: MemberScheduleItem): boolean {
  return item.item_type === 'bug';
}

function cardTitle(item: MemberScheduleItem): string {
  if (isBugItem(item)) {
    return item.bug_title ?? item.title;
  }
  return item.requirement_title ?? item.title;
}

function cardPhase(item: MemberScheduleItem): string {
  return isBugItem(item) ? '缺陷' : (item.node_label ?? '—');
}

function cardTask(item: MemberScheduleItem): string | null {
  if (isBugItem(item)) return null;
  return item.title;
}

function openButtonLabel(item: MemberScheduleItem): string {
  return isBugItem(item) ? '打开缺陷' : '打开需求';
}
</script>

<style scoped>
.unsched-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.unsched-card {
  padding: 12px 14px;
  border: 1px solid var(--schedule-border, #e5e6eb);
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.unsched-card__title {
  font-weight: 600;
  font-size: 14px;
  line-height: 1.4;
}
.unsched-card__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 10px;
  font-size: 12px;
  color: var(--n-text-color-3);
}
.unsched-card__phase {
  padding: 2px 6px;
  border-radius: 4px;
  background: #f5f6f8;
  color: var(--n-text-color-2);
}
.unsched-card__task {
  flex: 1;
  min-width: 0;
}
</style>
