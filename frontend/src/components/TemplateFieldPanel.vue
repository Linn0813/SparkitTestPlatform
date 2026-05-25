<template>
  <n-card title="字段配置" size="small" :bordered="false" class="field-config-card">
    <template #header-extra>
      <n-space :size="8">
        <n-button size="small" @click="$emit('add')">添加可配置字段</n-button>
        <n-button type="primary" size="small" :loading="saving" @click="$emit('save')">保存模板</n-button>
      </n-space>
    </template>
    <n-text depth="3" style="font-size: 12px; display: block; margin-bottom: 10px">
      <template v-if="scene === 'requirement'">
        下表包含编辑页<strong>全部字段</strong>。优先级、需求类型可点击「编辑选项」配置 Tag 选项；其余系统字段不可改。「可配置」为自定义扩展字段。
      </template>
      <template v-else>
        下表包含编辑页<strong>全部字段</strong>。「系统固定」不可在此修改；「可配置」字段可编辑、排序并保存到模板。
      </template>
    </n-text>
    <n-data-table :columns="columns" :data="displayRows" size="small" :bordered="true" />
  </n-card>
</template>

<script setup lang="ts">
import { computed, h } from 'vue';
import { NButton, NCard, NDataTable, NSpace, NTag, NText, useDialog, type DataTableColumns } from 'naive-ui';
import {
  buildFieldConfigRows,
  isSystemFieldRow,
  type FieldConfigRow,
  type RequirementOptionCategory,
} from '@/constants/systemFields';
import { isBuiltinField, normalizeFieldSort, sortTemplateFields } from '@/constants/fieldTypes';
import type { TemplateField } from '@/types/business';

const props = withDefaults(
  defineProps<{
    scene: 'case' | 'bug' | 'requirement';
    fields: TemplateField[];
    saving?: boolean;
    optionCounts?: Partial<Record<RequirementOptionCategory, number>>;
  }>(),
  {
    optionCounts: () => ({}),
  }
);

const emit = defineEmits<{
  'update:fields': [fields: TemplateField[]];
  add: [];
  edit: [index: number];
  save: [];
  'edit-options': [category: RequirementOptionCategory];
}>();

const dialog = useDialog();

const displayRows = computed(() => buildFieldConfigRows(props.scene, props.fields));

function typeCellLabel(row: FieldConfigRow): string {
  if (row.optionCategory && props.scene === 'requirement') {
    const count = props.optionCounts[row.optionCategory];
    if (count != null && count > 0) {
      return `${row.typeLabel} · ${count} 项`;
    }
  }
  return row.typeLabel;
}

const columns = computed<DataTableColumns<FieldConfigRow>>(() => [
  {
    title: '来源',
    key: 'source',
    width: 88,
    render: (r) =>
      h(
        NTag,
        { size: 'small', bordered: false, type: r.source === 'system' ? 'default' : 'success' },
        () => (r.source === 'system' ? '系统固定' : '可配置')
      ),
  },
  { title: '名称', key: 'name', ellipsis: { tooltip: true } },
  { title: '类型', key: 'typeLabel', width: 120, render: (r) => typeCellLabel(r) },
  { title: '必填', key: 'required', width: 56, render: (r) => (r.required ? '是' : '否') },
  {
    title: '操作',
    key: 'actions',
    width: 140,
    render: (row) => {
      if (isSystemFieldRow(row) && row.optionCategory && props.scene === 'requirement') {
        return h(
          NButton,
          {
            size: 'tiny',
            quaternary: true,
            type: 'primary',
            onClick: () => emit('edit-options', row.optionCategory!),
          },
          () => '编辑选项'
        );
      }
      if (isSystemFieldRow(row)) {
        return h(NText, { depth: 3, style: { fontSize: '12px' } }, () => '—');
      }
      const realIndex = props.fields.findIndex((f) => f.id === row.id);
      const sorted = sortTemplateFields(props.fields);
      const posInSorted = sorted.findIndex((f) => f.id === row.id);
      return h(NSpace, { size: 4, wrap: false }, () => [
        h(
          NButton,
          {
            size: 'tiny',
            quaternary: true,
            disabled: posInSorted <= 0,
            onClick: () => move(row.id, -1),
          },
          () => '↑'
        ),
        h(
          NButton,
          {
            size: 'tiny',
            quaternary: true,
            disabled: posInSorted >= sorted.length - 1,
            onClick: () => move(row.id, 1),
          },
          () => '↓'
        ),
        h(NButton, { size: 'tiny', type: 'primary', secondary: true, onClick: () => emit('edit', realIndex) }, () => '编辑'),
        h(NButton, { size: 'tiny', type: 'error', secondary: true, onClick: () => remove(realIndex) }, () => '删'),
      ]);
    },
  },
]);

function move(fieldId: string, delta: number) {
  const sorted = sortTemplateFields(props.fields);
  const pos = sorted.findIndex((f) => f.id === fieldId);
  if (pos < 0) return;
  const j = pos + delta;
  if (j < 0 || j >= sorted.length) return;
  const list = [...sorted];
  [list[pos], list[j]] = [list[j], list[pos]];
  emit('update:fields', normalizeFieldSort(list));
}

function remove(index: number) {
  const field = props.fields[index];
  if (!field) return;
  dialog.warning({
    title: '确认删除',
    content: isBuiltinField(field.id)
      ? `「${field.name}」为常用内置字段，删除后历史数据中的值可能仍保留但不再展示。确定删除？`
      : `删除字段「${field.name}」？已有数据中的历史值可能残留。`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: () => {
      emit(
        'update:fields',
        normalizeFieldSort(props.fields.filter((_, i) => i !== index))
      );
    },
  });
}
</script>

<style scoped>
.field-config-card {
  background: var(--n-color);
}
</style>
