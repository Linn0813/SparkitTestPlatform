<template>
  <div class="schedule-member-settings">
    <n-space :size="8" style="margin-bottom: 10px">
      <n-button size="tiny" quaternary @click="emit('select-all')">全选</n-button>
      <n-button size="tiny" quaternary @click="emit('select-none')">全不选</n-button>
    </n-space>
    <n-scrollbar style="max-height: 320px">
      <div v-if="!members.length" class="schedule-member-settings__empty">
        <n-text depth="3">暂无项目成员</n-text>
      </div>
      <ul v-else class="schedule-member-settings__list">
        <li
          v-for="(member, index) in members"
          :key="member.user_id"
          class="schedule-member-settings__item"
        >
          <n-checkbox
            :checked="isVisible(member.user_id)"
            @update:checked="(v) => emit('update-visible', member.user_id, v)"
          >
            <span class="schedule-member-settings__name">{{ member.name }}</span>
          </n-checkbox>
          <n-space :size="2" :wrap="false">
            <n-button
              size="tiny"
              quaternary
              :disabled="index === 0"
              title="上移"
              @click="emit('move', member.user_id, -1)"
            >
              ↑
            </n-button>
            <n-button
              size="tiny"
              quaternary
              :disabled="index === members.length - 1"
              title="下移"
              @click="emit('move', member.user_id, 1)"
            >
              ↓
            </n-button>
          </n-space>
        </li>
      </ul>
    </n-scrollbar>
  </div>
</template>

<script setup lang="ts">
import { NButton, NCheckbox, NScrollbar, NSpace, NText } from 'naive-ui';
import type { MemberScheduleRow } from '@/types/business';

defineProps<{
  members: MemberScheduleRow[];
  isVisible: (userId: string) => boolean;
}>();

const emit = defineEmits<{
  'update-visible': [userId: string, visible: boolean];
  move: [userId: string, delta: -1 | 1];
  'select-all': [];
  'select-none': [];
}>();
</script>

<style scoped>
.schedule-member-settings {
  width: 280px;
}
.schedule-member-settings__empty {
  padding: 16px 0;
  text-align: center;
}
.schedule-member-settings__list {
  list-style: none;
  margin: 0;
  padding: 0;
}
.schedule-member-settings__item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 6px 0;
  border-bottom: 1px solid var(--n-border-color);
}
.schedule-member-settings__item:last-child {
  border-bottom: none;
}
.schedule-member-settings__name {
  font-size: 13px;
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: inline-block;
  vertical-align: middle;
}
</style>
