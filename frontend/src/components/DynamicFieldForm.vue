<template>
  <div v-if="sortedFields.length" :class="{ 'dynamic-field-form--compact': compact }">
    <n-divider v-if="showDivider">{{ title }}</n-divider>
    <n-grid v-if="columns > 1" :cols="columns" :x-gap="compact ? 12 : 16" :y-gap="compact ? 2 : 4">
      <n-gi v-for="field in sortedFields" :key="field.id" :span="fieldSpan(field)">
        <n-form-item
          :label="field.name"
          :required="field.required"
          :label-placement="compact ? undefined : 'top'"
        >
          <TemplateFieldInput
            :field="field"
            :model-value="modelValue[field.id]"
            :project-id="effectiveProjectId"
            :size="compact ? 'small' : undefined"
            :placeholder="linkFieldPlaceholder(field)"
            @update:model-value="(v) => setValue(field.id, v)"
          />
        </n-form-item>
      </n-gi>
    </n-grid>
    <template v-else>
        <n-form-item
          v-for="field in sortedFields"
          :key="field.id"
          :label="field.name"
          :required="field.required"
          :label-placement="compact ? undefined : 'top'"
        >
          <TemplateFieldInput
            :field="field"
            :model-value="modelValue[field.id]"
            :project-id="effectiveProjectId"
            :size="compact ? 'small' : undefined"
            :placeholder="linkFieldPlaceholder(field)"
            @update:model-value="(v) => setValue(field.id, v)"
          />
        </n-form-item>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { NDivider, NFormItem, NGi, NGrid } from 'naive-ui';
import TemplateFieldInput from '@/components/TemplateFieldInput.vue';
import {
  isDescriptionLikeTemplateField,
  isLinkLikeTemplateField,
  isRichtextType,
  sortTemplateFields,
} from '@/constants/fieldTypes';
import { useContextStore } from '@/stores/context';
import type { TemplateField } from '@/types/business';

const props = withDefaults(
  defineProps<{
    fields: TemplateField[];
    modelValue: Record<string, unknown>;
    projectId?: string | null;
    title?: string;
    showDivider?: boolean;
    columns?: number;
    compact?: boolean;
  }>(),
  {
    title: '自定义字段',
    showDivider: false,
    columns: 1,
    compact: false,
  }
);

const emit = defineEmits<{
  'update:modelValue': [value: Record<string, unknown>];
}>();

const ctx = useContextStore();
const effectiveProjectId = computed(() => props.projectId ?? ctx.projectId);
const sortedFields = computed(() => sortTemplateFields(props.fields));

function fieldSpan(field: TemplateField): number {
  if (props.columns <= 1) return 1;
  if (isRichtextType(field.type) || field.type === 'textarea') return props.columns;
  if (isLinkLikeTemplateField(field)) return props.columns;
  if (isDescriptionLikeTemplateField(field)) return props.columns;
  return 1;
}

function linkFieldPlaceholder(field: TemplateField): string | undefined {
  if (!props.compact || !isLinkLikeTemplateField(field)) return undefined;
  return '多个链接可用空格或换行分隔';
}

function setValue(id: string, value: unknown) {
  emit('update:modelValue', { ...props.modelValue, [id]: value });
}
</script>

<style scoped>
.dynamic-field-form--compact :deep(.n-form-item) {
  margin-bottom: 4px;
}

.dynamic-field-form--compact :deep(.n-form-item-label) {
  padding-bottom: 2px;
  min-height: auto;
}
</style>
