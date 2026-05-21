<template>
  <template v-if="sortedFields.length">
    <n-divider v-if="showDivider">{{ title }}</n-divider>
    <n-form-item
      v-for="field in sortedFields"
      :key="field.id"
      :label="field.name"
      :required="field.required"
    >
      <TemplateFieldInput
        :field="field"
        :model-value="modelValue[field.id]"
        :project-id="effectiveProjectId"
        @update:model-value="(v) => setValue(field.id, v)"
      />
    </n-form-item>
  </template>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { NDivider, NFormItem } from 'naive-ui';
import TemplateFieldInput from '@/components/TemplateFieldInput.vue';
import { sortTemplateFields } from '@/constants/fieldTypes';
import { useContextStore } from '@/stores/context';
import type { TemplateField } from '@/types/business';

const props = withDefaults(
  defineProps<{
    fields: TemplateField[];
    modelValue: Record<string, unknown>;
    projectId?: string | null;
    title?: string;
    showDivider?: boolean;
  }>(),
  {
    title: '自定义字段',
    showDivider: false,
  }
);

const emit = defineEmits<{
  'update:modelValue': [value: Record<string, unknown>];
}>();

const ctx = useContextStore();
const effectiveProjectId = computed(() => props.projectId ?? ctx.projectId);
const sortedFields = computed(() => sortTemplateFields(props.fields));

function setValue(id: string, value: unknown) {
  emit('update:modelValue', { ...props.modelValue, [id]: value });
}
</script>
