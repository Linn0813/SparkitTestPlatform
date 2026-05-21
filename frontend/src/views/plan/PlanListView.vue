<template>
  <n-card title="测试计划">
    <template #header-extra>
      <n-button v-if="canPlans" type="primary" @click="showModal = true">新建计划</n-button>
    </template>
    <n-space v-if="statusFilter || versionFilter" align="center" style="margin-bottom: 12px">
      <n-text depth="3">筛选：</n-text>
      <n-tag v-if="statusFilter" closable @close="clearStatusFilter">
        状态 {{ planStatusLabel(statusFilter) }}
      </n-tag>
      <n-tag v-if="versionFilter" closable @close="clearVersionFilter">关联版本已筛选</n-tag>
    </n-space>
    <n-data-table
      :columns="columns"
      :data="filteredPlans"
      :loading="loading"
      :row-key="(row: TestPlan) => row.id"
      :row-props="rowProps"
    />
    <n-modal v-model:show="showModal" preset="dialog" title="新建计划" positive-text="创建" @positive-click="onCreate">
      <n-form label-placement="top">
        <n-form-item label="名称"><n-input v-model:value="form.name" placeholder="计划名称" /></n-form-item>
        <n-form-item label="状态">
          <n-select v-model:value="form.status" :options="PLAN_STATUS_OPTIONS" style="width: 100%" />
        </n-form-item>
        <n-form-item label="关联版本">
          <VersionSelect v-model="form.version_id" :project-id="ctx.projectId" />
        </n-form-item>
        <n-form-item label="描述">
          <n-input v-model:value="form.description" type="textarea" :rows="3" placeholder="可选" />
        </n-form-item>
      </n-form>
    </n-modal>
  </n-card>
</template>

<script setup lang="ts">
import { computed, h, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  NButton,
  NCard,
  NDataTable,
  NForm,
  NFormItem,
  NInput,
  NModal,
  NSelect,
  NSpace,
  NTag,
  NText,
  useMessage,
  type DataTableColumns,
} from 'naive-ui';
import { createPlan, listPlans } from '@/api/plans';
import VersionSelect from '@/components/VersionSelect.vue';
import {
  PLAN_STATUS_OPTIONS,
  formatPlanPassRate,
  formatPlanProgress,
  planStatusLabel,
  planStatusTagType,
} from '@/constants/planStatus';
import { usePermissions } from '@/composables/usePermissions';
import { useContextStore } from '@/stores/context';
import type { TestPlan } from '@/types/business';

const router = useRouter();
const route = useRoute();
const ctx = useContextStore();
const statusFilter = ref<string | null>(null);
const versionFilter = ref<string | null>(null);
const { canManagePlans } = usePermissions();
const canPlans = computed(() => canManagePlans(ctx.projectId));
const message = useMessage();
const plans = ref<TestPlan[]>([]);
const loading = ref(false);
const showModal = ref(false);
const form = ref({
  name: '',
  status: 'draft' as string,
  description: '',
  version_id: null as string | null,
});

const filteredPlans = computed(() => plans.value);

function applyRouteQuery() {
  const raw = route.query.status;
  statusFilter.value = typeof raw === 'string' && raw ? raw : null;
  const vid = route.query.version_id;
  versionFilter.value = typeof vid === 'string' && vid ? vid : null;
}

function clearStatusFilter() {
  statusFilter.value = null;
  const q = { ...route.query };
  delete q.status;
  router.replace({ name: 'plans', query: q });
}

function clearVersionFilter() {
  versionFilter.value = null;
  const q = { ...route.query };
  delete q.version_id;
  router.replace({ name: 'plans', query: q });
}

function formatDate(iso: string) {
  try {
    return new Date(iso).toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return iso;
  }
}

function goDetail(id: string) {
  router.push({ name: 'plan-detail', params: { id } });
}

function rowProps(row: TestPlan) {
  return {
    style: 'cursor: pointer',
    onClick: () => goDetail(row.id),
  };
}

const columns: DataTableColumns<TestPlan> = [
  {
    title: '名称',
    key: 'name',
    width: 200,
    maxWidth: 240,
    ellipsis: { tooltip: true },
    render: (row) =>
      h(
        NButton,
        {
          text: true,
          type: 'primary',
          onClick: (e: MouseEvent) => {
            e.stopPropagation();
            goDetail(row.id);
          },
        },
        () => row.name
      ),
  },
  {
    title: '状态',
    key: 'status',
    width: 96,
    render: (row) =>
      h(NTag, { size: 'small', bordered: false, type: planStatusTagType(row.status) }, () =>
        planStatusLabel(row.status)
      ),
  },
  {
    title: '用例数',
    key: 'case_total',
    width: 80,
    render: (row) => row.case_total ?? 0,
  },
  {
    title: '通过率',
    key: 'pass_rate',
    width: 88,
    render: (row) => formatPlanPassRate(row),
  },
  {
    title: '通过/总数',
    key: 'progress',
    width: 96,
    render: (row) => formatPlanProgress(row),
  },
  {
    title: '更新时间',
    key: 'updated_at',
    width: 150,
    render: (row) => formatDate(row.updated_at),
  },
];

async function load() {
  if (!ctx.projectId) {
    plans.value = [];
    return;
  }
  loading.value = true;
  try {
    const params: { version_id?: string } = {};
    if (versionFilter.value) params.version_id = versionFilter.value;
    const { data } = await listPlans(params);
    plans.value = statusFilter.value
      ? data.filter((p) => p.status === statusFilter.value)
      : data;
  } finally {
    loading.value = false;
  }
}

async function onCreate() {
  if (!form.value.name.trim()) {
    message.warning('请填写计划名称');
    return false;
  }
  await createPlan({
    name: form.value.name.trim(),
    status: form.value.status,
    description: form.value.description.trim() || undefined,
    version_id: form.value.version_id,
  });
  message.success('已创建');
  showModal.value = false;
  form.value = { name: '', status: 'draft', description: '', version_id: null };
  await load();
  return true;
}

onMounted(() => {
  applyRouteQuery();
  load();
});
watch(() => ctx.projectId, load);
watch(
  () => route.query,
  () => {
    applyRouteQuery();
    load();
  }
);
</script>
