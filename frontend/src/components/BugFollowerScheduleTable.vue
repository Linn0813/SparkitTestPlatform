<template>
  <div v-if="rows.length" class="follower-schedule-section">
    <div class="follower-schedule-grid">
      <div class="follower-schedule-head">
        <span>跟进人</span>
        <span>修复估分</span>
        <span>排期</span>
      </div>
      <div
        v-for="row in rows"
        :key="row.user_id"
        class="follower-schedule-row"
        :class="{ 'follower-schedule-row--saving': savingUserId === row.user_id }"
      >
        <div class="follower-schedule-cell">{{ row.name }}</div>
        <div class="follower-schedule-cell follower-schedule-cell--estimate">
          <n-input-number
            v-if="canEditRow(row.user_id)"
            class="follower-schedule-field"
            :value="estimateDrafts[row.user_id] ?? row.fix_estimate_points"
            size="small"
            :min="0"
            :show-button="false"
            clearable
            placeholder="—"
            :disabled="savingUserId === row.user_id"
            @update:value="(v: number | null) => emit('estimate-input', row.user_id, v)"
            @blur="() => emit('estimate-blur', row)"
          />
          <span v-else class="follower-schedule-text">{{ formatEstimate(row.fix_estimate_points) }}</span>
        </div>
        <div class="follower-schedule-cell">
          <n-date-picker
            v-if="canEditRow(row.user_id)"
            class="follower-schedule-field"
            :formatted-value="scheduleRange(row)"
            type="daterange"
            size="small"
            value-format="yyyy-MM-dd"
            clearable
            :disabled="savingUserId === row.user_id"
            @update:formatted-value="(v: [string, string] | null) => emit('schedule-change', row, v)"
          />
          <span v-else class="follower-schedule-text">{{ scheduleLabel(row) }}</span>
        </div>
      </div>
    </div>
  </div>
  <n-text v-else depth="3">请先添加跟进人</n-text>
</template>

<script setup lang="ts">
import { NDatePicker, NInputNumber, NText } from 'naive-ui';

export interface FollowerScheduleRow {
  user_id: string;
  name: string;
  fix_estimate_points: number | null;
  scheduled_start: string | null;
  scheduled_end: string | null;
}

defineProps<{
  rows: FollowerScheduleRow[];
  canEditRow: (userId: string) => boolean;
  savingUserId: string | null;
  estimateDrafts: Record<string, number | null>;
}>();

const emit = defineEmits<{
  'estimate-input': [userId: string, value: number | null];
  'estimate-blur': [row: FollowerScheduleRow];
  'schedule-change': [row: FollowerScheduleRow, range: [string, string] | null];
}>();

function scheduleRange(row: FollowerScheduleRow): [string, string] | null {
  if (row.scheduled_start && row.scheduled_end) {
    return [row.scheduled_start.slice(0, 10), row.scheduled_end.slice(0, 10)];
  }
  return null;
}

function scheduleLabel(row: FollowerScheduleRow): string {
  const range = scheduleRange(row);
  if (!range) return '—';
  return `${range[0]} ~ ${range[1]}`;
}

function formatEstimate(value: number | null): string {
  if (value == null) return '—';
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}
</script>

<style scoped>
.follower-schedule-section {
  margin-bottom: 16px;
}
.follower-schedule-grid {
  border: 1px solid var(--n-border-color);
  border-radius: 8px;
  overflow: hidden;
}
.follower-schedule-head,
.follower-schedule-row {
  display: grid;
  grid-template-columns: minmax(100px, 1.2fr) minmax(80px, 0.8fr) minmax(180px, 1.4fr);
  gap: 8px;
  align-items: center;
  padding: 8px 12px;
}
.follower-schedule-head {
  background: var(--n-color-modal);
  font-size: 12px;
  color: var(--n-text-color-3);
  border-bottom: 1px solid var(--n-border-color);
}
.follower-schedule-row + .follower-schedule-row {
  border-top: 1px solid var(--n-border-color);
}
.follower-schedule-row--saving {
  opacity: 0.65;
}
.follower-schedule-cell--estimate {
  max-width: 120px;
}
.follower-schedule-field {
  width: 100%;
}
.follower-schedule-text {
  font-size: 13px;
}
</style>
