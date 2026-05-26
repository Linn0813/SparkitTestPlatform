<template>
  <div class="requirement-list-filters">
    <n-form size="small" label-placement="top" @submit.prevent="emit('apply')">
      <div class="filter-row">
        <div class="filter-grid">
          <n-form-item label="标题" class="filter-item filter-item--wide">
            <n-input v-model:value="model.q" placeholder="关键字" clearable />
          </n-form-item>
          <n-form-item label="状态" class="filter-item filter-item--wide">
            <n-select
              v-model:value="model.status_keys"
              :options="statusOptions"
              clearable
              multiple
              max-tag-count="responsive"
              placeholder="全部"
            />
          </n-form-item>
          <n-form-item label="优先级" class="filter-item filter-item--wide">
            <n-select
              v-model:value="model.priorities"
              :options="priorityOptions"
              clearable
              multiple
              max-tag-count="responsive"
              placeholder="全部"
            />
          </n-form-item>
          <n-form-item label="类型" class="filter-item filter-item--wide">
            <n-select
              v-model:value="model.req_types"
              :options="typeOptions"
              clearable
              multiple
              max-tag-count="responsive"
              placeholder="全部"
            />
          </n-form-item>
          <n-form-item label="关联版本" class="filter-item filter-item--version">
            <VersionSelect v-model="model.version_id" :project-id="projectId" />
          </n-form-item>
        </div>
        <div class="filter-toolbar">
          <n-button type="primary" size="small" attr-type="submit">查询</n-button>
          <n-button size="small" @click="emit('reset')">重置</n-button>
        </div>
      </div>
    </n-form>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { NButton, NForm, NFormItem, NInput, NSelect } from 'naive-ui';
import VersionSelect from '@/components/VersionSelect.vue';
import { REQUIREMENT_STATUS_OPTIONS } from '@/constants/requirementStatus';
import { useRequirementProjectConfig } from '@/composables/useRequirementProjectConfig';
import type { RequirementListFilterState } from '@/composables/useRequirementListFilters';

const props = defineProps<{
  model: RequirementListFilterState;
  projectId: string | null;
}>();

const emit = defineEmits<{
  apply: [];
  reset: [];
}>();
const statusOptions = [...REQUIREMENT_STATUS_OPTIONS];

const projectConfig = useRequirementProjectConfig(() => props.projectId);

const priorityOptions = computed(() =>
  projectConfig.priorityOptions.value.map((o) => ({ label: o.label, value: o.option_key }))
);
const typeOptions = computed(() =>
  projectConfig.typeOptions.value.map((o) => ({ label: o.label, value: o.option_key }))
);
</script>

<style scoped>
.requirement-list-filters {
  margin-top: 8px;
}

.filter-row {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 8px 12px;
}

.filter-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 10px;
  align-items: flex-end;
  flex: 1;
  min-width: 0;
}

.filter-item {
  width: 132px;
  margin-bottom: 0;
}

.filter-item--wide {
  width: 200px;
}

.filter-item--version {
  width: min(100%, 220px);
  min-width: 180px;
}

.filter-item :deep(.n-form-item-label) {
  font-size: 12px;
  padding-bottom: 2px;
}

.filter-item :deep(.n-form-item-blank) {
  min-height: 28px;
}

.filter-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  margin-left: auto;
}
</style>
