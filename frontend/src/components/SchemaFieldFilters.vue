<template>
  <div class="schema-field-filters">
    <n-form size="small" label-placement="top" @submit.prevent="emit('apply')">
      <div class="filter-row">
        <div v-if="visibleDefs.length" class="filter-grid">
          <template v-for="def in visibleDefs" :key="def.key">
            <n-form-item
              v-if="def.key === 'module' && scene === 'functional_case'"
              :label="def.label"
              class="filter-item filter-item--module"
            >
              <n-space align="center" :size="8" wrap item-style="flex: 1; min-width: 160px">
                <n-tree-select
                  v-model:value="caseModel.module_id"
                  :options="moduleTreeOptions"
                  key-field="key"
                  label-field="label"
                  clearable
                  filterable
                  placeholder="全部模块"
                  style="width: 100%; min-width: 160px"
                  @update:value="onModuleFilterChange"
                />
                <n-checkbox
                  v-model:checked="caseModel.include_submodules"
                  :disabled="!caseModel.module_id"
                  @update:checked="onModuleFilterChange"
                >
                  含子模块
                </n-checkbox>
              </n-space>
            </n-form-item>

            <n-form-item v-else-if="def.key === 'q'" :label="def.label" class="filter-item filter-item--wide">
              <n-input v-model:value="model.q" placeholder="关键字" clearable />
            </n-form-item>

            <n-form-item v-else-if="def.key === 'priority'" :label="def.label" class="filter-item">
              <n-select
                v-model:value="caseModel.priority"
                :options="priorityFilterOptions"
                clearable
                placeholder="全部"
              />
            </n-form-item>

            <n-form-item
              v-else-if="def.key === 'status' && scene === 'bug'"
              :label="def.label"
              class="filter-item"
            >
              <n-select
                v-model:value="bugModel.status_key"
                :options="statusOptions"
                clearable
                placeholder="全部"
              />
            </n-form-item>

            <n-form-item
              v-else-if="def.key === 'reporter' && scene === 'bug'"
              :label="def.label"
              class="filter-item"
            >
              <n-select
                v-model:value="bugModel.reporter_id"
                :options="memberOptions"
                clearable
                filterable
                placeholder="全部"
              />
            </n-form-item>

            <n-form-item
              v-else-if="def.key === 'follower' && scene === 'bug'"
              :label="def.label"
              class="filter-item"
            >
              <n-select
                v-model:value="bugModel.follower_id"
                :options="memberFilterOptions"
                clearable
                filterable
                placeholder="全部"
              />
            </n-form-item>

            <n-form-item
              v-else-if="def.key === 'plan_version' && scene === 'bug'"
              :label="def.label"
              class="filter-item"
            >
              <VersionSelect
                v-model="bugModel.plan_version_id"
                :project-id="projectId"
                allow-empty-filter
                placeholder="全部"
              />
            </n-form-item>

            <n-form-item
              v-else-if="def.key === 'found_version' && scene === 'bug'"
              :label="def.label"
              class="filter-item"
            >
              <VersionSelect
                v-model="bugModel.found_version_id"
                :project-id="projectId"
                allow-empty-filter
                placeholder="全部"
              />
            </n-form-item>

            <n-form-item v-else-if="def.key === 'requirement'" :label="def.label" class="filter-item">
              <n-select
                v-model:value="model.requirement_id"
                :options="requirementFilterOptions"
                clearable
                filterable
                placeholder="全部"
              />
            </n-form-item>

            <n-form-item v-else-if="def.key === 'plan' && scene === 'bug'" :label="def.label" class="filter-item">
              <n-select
                v-model:value="bugModel.plan_id"
                :options="planFilterOptions"
                clearable
                filterable
                placeholder="全部"
              />
            </n-form-item>

            <n-form-item
              v-else-if="def.kind === 'template' && def.field"
              :label="def.label"
              :class="[
                'filter-item',
                { 'filter-item--wide': isTextLikeTemplateFilter(def.field.type) },
              ]"
            >
              <n-select
                v-if="isOptionFieldType(def.field.type)"
                v-model:value="model.custom[def.field.id]"
                :options="templateFieldFilterOptions(def.field)"
                clearable
                :placeholder="templateFieldFilterPlaceholder(def.field)"
              />
              <n-select
                v-else-if="isMemberType(def.field.type)"
                v-model:value="model.custom[def.field.id]"
                :options="memberFilterOptions"
                clearable
                filterable
                placeholder="全部"
              />
              <n-select
                v-else-if="def.field.type === 'switch'"
                v-model:value="model.custom[def.field.id]"
                :options="templateFieldFilterOptions(def.field)"
                clearable
                placeholder="全部"
              />
              <n-date-picker
                v-else-if="def.field.type === 'date'"
                :formatted-value="customFilterText(def.field.id)"
                value-format="yyyy-MM-dd"
                type="date"
                clearable
                placeholder="选择日期"
                style="width: 100%"
                @update:formatted-value="setCustomFilterText(def.field.id, $event)"
              />
              <n-input
                v-else-if="isTextLikeTemplateFilter(def.field.type)"
                :value="customFilterText(def.field.id)"
                clearable
                :placeholder="textFilterPlaceholder(def.field.type)"
                @update:value="setCustomFilterText(def.field.id, $event)"
              />
            </n-form-item>
          </template>
        </div>

        <n-text v-else depth="3" class="filter-empty-hint">点击「筛选字段」添加筛选条件</n-text>

        <div class="filter-toolbar">
          <n-popover trigger="click" placement="bottom-start" :width="220">
            <template #trigger>
              <n-button size="small" quaternary>
                筛选字段
                <span v-if="visibleKeys.length" class="filter-count">({{ visibleKeys.length }})</span>
              </n-button>
            </template>
            <div class="filter-picker">
              <n-checkbox-group :value="visibleKeys" @update:value="onPickerChange">
                <n-space vertical :size="4">
                  <n-checkbox v-for="item in catalog" :key="item.key" :value="item.key" :label="item.label" />
                </n-space>
              </n-checkbox-group>
            </div>
          </n-popover>
          <n-space :size="8">
            <n-button type="primary" size="small" attr-type="submit">查询</n-button>
            <n-button size="small" @click="emit('reset')">重置</n-button>
          </n-space>
        </div>
      </div>
    </n-form>
  </div>
</template>

<script setup lang="ts">
import { computed, withDefaults } from 'vue';
import {
  NButton,
  NCheckbox,
  NCheckboxGroup,
  NDatePicker,
  NForm,
  NFormItem,
  NInput,
  NPopover,
  NSelect,
  NSpace,
  NText,
  NTreeSelect,
} from 'naive-ui';
import type { TreeSelectOption } from 'naive-ui';
import VersionSelect from '@/components/VersionSelect.vue';
import {
  CASE_PRIORITY_FILTER_OPTIONS,
  templateFieldFilterOptions,
  templateFieldFilterPlaceholder,
  withEmptyFilterOption,
  type FieldCatalogItem,
} from '@/schemas/entityFieldSchema';
import { isMemberType, isOptionFieldType, isTextLikeType } from '@/constants/fieldTypes';
import type { BugListFilterState } from '@/composables/useBugListFilters';
import type { CaseListFilterState } from '@/composables/useCaseListFilters';
import type { EntityScene } from '@/schemas/entityFieldSchema';

const props = withDefaults(
  defineProps<{
    scene?: EntityScene;
    model: BugListFilterState | CaseListFilterState;
    catalog: FieldCatalogItem[];
    projectId: string | null;
    visibleKeys: string[];
    statusOptions?: { label: string; value: string }[];
    memberOptions?: { label: string; value: string }[];
    requirementOptions: { label: string; value: string }[];
    planOptions?: { label: string; value: string }[];
    moduleTreeOptions?: TreeSelectOption[];
  }>(),
  {
    scene: 'bug',
    statusOptions: () => [],
    memberOptions: () => [],
    planOptions: () => [],
    moduleTreeOptions: () => [],
  }
);

const bugModel = computed(() => props.model as BugListFilterState);
const caseModel = computed(() => props.model as CaseListFilterState);
const priorityFilterOptions = computed(() =>
  props.scene === 'functional_case'
    ? withEmptyFilterOption(CASE_PRIORITY_FILTER_OPTIONS)
    : []
);

const emit = defineEmits<{
  apply: [];
  reset: [];
  'update:visibleKeys': [keys: string[]];
  moduleChange: [];
}>();

function onModuleFilterChange() {
  if (!caseModel.value.module_id) {
    caseModel.value.include_submodules = false;
  }
  emit('moduleChange');
}

const catalogByKey = computed(() => {
  const m = new Map<string, FieldCatalogItem>();
  for (const d of props.catalog) m.set(d.key, d);
  return m;
});

const visibleDefs = computed(() =>
  props.visibleKeys
    .map((k) => catalogByKey.value.get(k))
    .filter((d): d is FieldCatalogItem => !!d)
);

const memberFilterOptions = computed(() => withEmptyFilterOption(props.memberOptions ?? []));
const requirementFilterOptions = computed(() => withEmptyFilterOption(props.requirementOptions));
const planFilterOptions = computed(() => withEmptyFilterOption(props.planOptions));

function onPickerChange(keys: Array<string | number>) {
  emit(
    'update:visibleKeys',
    keys.map((k) => String(k))
  );
}

function isTextLikeTemplateFilter(type: string): boolean {
  return isTextLikeType(type) || type === 'number';
}

function customFilterText(fieldId: string): string {
  const v = props.model.custom[fieldId];
  return v == null ? '' : String(v);
}

function setCustomFilterText(fieldId: string, value: string | null) {
  const trimmed = value?.trim() ?? '';
  props.model.custom[fieldId] = trimmed ? trimmed : null;
}

function textFilterPlaceholder(type: string): string {
  if (type === 'number') return '精确匹配数字';
  return '请输入关键字';
}
</script>

<style scoped>
.schema-field-filters {
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

.filter-item--module {
  width: min(100%, 360px);
  min-width: 280px;
}

.filter-item :deep(.n-form-item-label) {
  font-size: 12px;
  padding-bottom: 2px;
}

.filter-item :deep(.n-form-item-blank) {
  min-height: 28px;
}

.filter-empty-hint {
  font-size: 12px;
  padding-bottom: 6px;
}

.filter-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  margin-left: auto;
}

.filter-count {
  margin-left: 2px;
  opacity: 0.7;
}

.filter-picker {
  max-height: 320px;
  overflow-y: auto;
  padding: 4px 0;
}
</style>
