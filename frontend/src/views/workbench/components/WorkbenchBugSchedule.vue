<template>
  <n-spin :show="loading">
    <n-space vertical size="large">
      <TodoSection
        title="每日新增缺陷"
        :count="dailyTotal"
        :empty="!dailyBugs.length && !loading"
      >
        <template #header-extra>
          <n-date-picker
            v-model:formatted-value="selectedDate"
            type="date"
            size="small"
            value-format="yyyy-MM-dd"
            :clearable="false"
            style="width: 140px"
            @update:formatted-value="onDateChange"
          />
        </template>

        <div v-for="b in dailyBugs" :key="b.id" class="todo-item">
          <WorkbenchTodoRow
            mode="action"
            :label="b.title"
            :columns="bugScheduleColumns(b)"
            :tag="bugStatusLabel(b.status_key)"
            :tag-type="bugStatusTagType(b.status_key)"
            @click="openDailyBug(b.id)"
          />
        </div>

      </TodoSection>

      <TodoSection
        title="无规划迭代缺陷"
        :count="unplannedTotal"
        :empty="!unplannedBugs.length && !loading"
      >
        <div v-for="b in unplannedBugs" :key="b.id" class="todo-item">
          <WorkbenchTodoRow
            mode="action"
            :label="b.title"
            :columns="bugScheduleColumns(b)"
            :tag="bugStatusLabel(b.status_key)"
            :tag-type="bugStatusTagType(b.status_key)"
            @click="openUnplannedBug(b.id)"
          />
        </div>
      </TodoSection>
    </n-space>
  </n-spin>
</template>

<script setup lang="ts">
import { inject, onBeforeUnmount, ref } from 'vue';
import {
  NDatePicker,
  NSpace,
  NSpin,
  type TagProps,
} from 'naive-ui';
import { listBugs } from '@/api/bugs';
import { FILTER_EMPTY_VALUE } from '@/constants/bugFilters';
import { UNPLANNED_BUG_EXCLUDED_STATUS_QUERY } from '@/constants/dashboardTodo';
import { WORKBENCH_BUG_DRAWER_KEY } from '@/composables/useWorkbenchBugDrawer';
import type { BugItem } from '@/types/business';
import { bugScheduleColumns } from '@/utils/bugListLabels';
import { todayInUtcPlus8 } from '@/utils/timezone';
import TodoSection from './TodoSection.vue';
import WorkbenchTodoRow from './WorkbenchTodoRow.vue';

const props = defineProps<{
  projectId: string | null;
  bugStatusLabel: (key: string) => string;
  bugStatusTagType: (key: string) => TagProps['type'];
}>();

const bugDrawer = inject(WORKBENCH_BUG_DRAWER_KEY);

const fetchPageSize = 100;
const loading = ref(false);
const selectedDate = ref(todayInUtcPlus8());

const dailyBugs = ref<BugItem[]>([]);
const dailyTotal = ref(0);

const unplannedBugs = ref<BugItem[]>([]);
const unplannedTotal = ref(0);

let loadDailySeq = 0;
let loadUnplannedSeq = 0;

function openDailyBug(id: string) {
  bugDrawer?.open(id, dailyBugs.value, 'daily');
}

function openUnplannedBug(id: string) {
  bugDrawer?.open(id, unplannedBugs.value, 'unplanned');
}

function onDateChange() {
  void loadDaily(true);
}

async function loadDaily(withLoading = false) {
  if (!props.projectId || !selectedDate.value) {
    dailyBugs.value = [];
    dailyTotal.value = 0;
    return;
  }
  const seq = ++loadDailySeq;
  if (withLoading) loading.value = true;
  try {
    const all: BugItem[] = [];
    let page = 1;
    let total = 0;
    do {
      const { data } = await listBugs({
        created_date: selectedDate.value,
        plan_version_id: FILTER_EMPTY_VALUE,
        page,
        page_size: fetchPageSize,
      });
      if (seq !== loadDailySeq) return;
      all.push(...data.items);
      total = data.total;
      page++;
    } while (all.length < total);
    if (seq !== loadDailySeq) return;
    dailyBugs.value = all;
    dailyTotal.value = total;
  } finally {
    if (withLoading && seq === loadDailySeq) loading.value = false;
  }
}

async function loadUnplanned(withLoading = false) {
  if (!props.projectId) {
    unplannedBugs.value = [];
    unplannedTotal.value = 0;
    return;
  }
  const seq = ++loadUnplannedSeq;
  if (withLoading) loading.value = true;
  try {
    const all: BugItem[] = [];
    let page = 1;
    let total = 0;
    do {
      const { data } = await listBugs({
        plan_version_id: FILTER_EMPTY_VALUE,
        exclude_status_key: UNPLANNED_BUG_EXCLUDED_STATUS_QUERY,
        sort_by: 'severity',
        page,
        page_size: fetchPageSize,
      });
      if (seq !== loadUnplannedSeq) return;
      all.push(...data.items);
      total = data.total;
      page++;
    } while (all.length < total);
    if (seq !== loadUnplannedSeq) return;
    unplannedBugs.value = all;
    unplannedTotal.value = total;
  } finally {
    if (withLoading && seq === loadUnplannedSeq) loading.value = false;
  }
}

async function load() {
  if (!props.projectId) return;
  loading.value = true;
  try {
    await Promise.all([loadDaily(), loadUnplanned()]);
  } finally {
    loading.value = false;
  }
}

defineExpose({ load, dailyBugs, unplannedBugs });

onBeforeUnmount(() => {
  loadDailySeq += 1;
  loadUnplannedSeq += 1;
});
</script>
