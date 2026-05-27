<template>
  <RichTextFieldInput
    v-if="isRichtextType(field.type)"
    :model-value="modelValue"
    :project-id="projectId"
    :disabled="disabled"
    :placeholder="placeholder"
    :autosize="textareaAutosize"
    @update:model-value="emitValue"
  />
  <n-input
    v-else-if="isLinkLikeTemplateField(field)"
    :value="textValue"
    type="textarea"
    :autosize="linkTextareaAutosize"
    :disabled="disabled"
    :size="inputSize"
    :placeholder="linkPlaceholder"
    @update:value="(v) => emitValue(v)"
  />
  <PasteImageTextarea
    v-else-if="isTextLikeType(field.type)"
    :model-value="textValue"
    :project-id="projectId"
    :disabled="disabled"
    :placeholder="placeholder"
    :autosize="textareaAutosize"
    :compact="inputSize === 'small'"
    @update:model-value="(v) => emitValue(v)"
  />
  <n-input-number
    v-else-if="field.type === 'number'"
    :value="numberValue"
    :disabled="disabled"
    clearable
    style="width: 100%"
    :placeholder="placeholder"
    @update:value="(v) => emitValue(v)"
  />
  <n-date-picker
    v-else-if="field.type === 'date'"
    :value="dateValue"
    type="date"
    :disabled="disabled"
    clearable
    style="width: 100%"
    :placeholder="placeholder"
    @update:value="(v) => emitValue(v)"
  />
  <n-switch
    v-else-if="field.type === 'switch'"
    :value="switchValue"
    :disabled="disabled"
    @update:value="(v) => emitValue(v)"
  />
  <n-select
    v-else-if="field.type === 'member'"
    :value="selectValue"
    :options="memberOptions"
    :disabled="disabled"
    :loading="memberLoading"
    filterable
    clearable
    :placeholder="memberPlaceholder"
    style="width: 100%"
    @update:value="(v) => emitValue(v)"
  />
  <SelectRadioField
    v-else-if="field.type === 'select' && useRadioSelect"
    :model-value="selectValue"
    :options="field.options ?? []"
    :name="`field-${field.id}`"
    @update:model-value="(v) => emitValue(v)"
  />
  <n-select
    v-else-if="field.type === 'select'"
    :value="selectValue"
    :options="selectOptions"
    :disabled="disabled"
    clearable
    :placeholder="placeholder"
    style="width: 100%"
    @update:value="(v) => emitValue(v)"
  />
  <n-select
    v-else-if="field.type === 'multi_select'"
    :value="multiSelectValue"
    :options="selectOptions"
    :disabled="disabled"
    multiple
    clearable
    :placeholder="placeholder"
    style="width: 100%"
    @update:value="(v) => emitValue(v)"
  />
  <n-input
    v-else
    :value="textValue"
    :disabled="disabled"
    :size="inputSize"
    :placeholder="placeholder"
    @update:value="(v) => emitValue(v)"
  />
</template>

<script setup lang="ts">
import { computed, toRef } from 'vue';
import { NDatePicker, NInput, NInputNumber, NSelect, NSwitch } from 'naive-ui';
import PasteImageTextarea from '@/components/PasteImageTextarea.vue';
import RichTextFieldInput from '@/components/RichTextFieldInput.vue';
import SelectRadioField from '@/components/SelectRadioField.vue';
import { useProjectMemberOptions } from '@/composables/useProjectMemberOptions';
import {
  isDescriptionLikeTemplateField,
  isLinkLikeTemplateField,
  isRichtextType,
  isTextLikeType,
} from '@/constants/fieldTypes';
import { isPromotedRadioSelectField } from '@/schemas/entityFieldSchema';
import type { TemplateField } from '@/types/business';

const props = withDefaults(
  defineProps<{
    field: TemplateField;
    modelValue: unknown;
    projectId?: string | null;
    disabled?: boolean;
    placeholder?: string;
    size?: 'small' | 'medium' | 'large';
  }>(),
  { disabled: false }
);

const inputSize = computed(() => props.size);

const emit = defineEmits<{
  'update:modelValue': [value: unknown];
}>();

const projectIdRef = toRef(props, 'projectId');
const { options: memberOptions, loading: memberLoading } = useProjectMemberOptions(projectIdRef);

const placeholder = computed(() => {
  if (props.placeholder) return props.placeholder;
  if (props.field.type === 'select' || props.field.type === 'multi_select') {
    return `请选择${props.field.name}`;
  }
  if (props.field.type === 'member') return `请选择${props.field.name}`;
  return `请输入${props.field.name}`;
});

const linkTextareaAutosize = { minRows: 2, maxRows: 8 };

const textareaAutosize = computed(() =>
  isDescriptionLikeTemplateField(props.field)
    ? { minRows: 8, maxRows: 20 }
    : { minRows: 4, maxRows: 12 }
);

const linkPlaceholder = computed(() => {
  if (props.placeholder) return props.placeholder;
  return '多个链接请用空格或换行分隔，需以 http:// 或 https:// 开头';
});

const memberPlaceholder = computed(() =>
  props.projectId ? `请选择${props.field.name}` : '请先选择项目'
);

const useRadioSelect = computed(() => isPromotedRadioSelectField(props.field));

const selectOptions = computed(() => (props.field.options ?? []).map((o) => ({ label: o, value: o })));

const textValue = computed(() => {
  const v = props.modelValue;
  return v === undefined || v === null ? '' : String(v);
});

const numberValue = computed(() => {
  const v = props.modelValue;
  if (v === undefined || v === null || v === '') return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
});

const dateValue = computed(() => {
  const v = props.modelValue;
  if (v === undefined || v === null || v === '') return null;
  const n = typeof v === 'number' ? v : Date.parse(String(v));
  return Number.isFinite(n) ? n : null;
});

const switchValue = computed(() => Boolean(props.modelValue));

const selectValue = computed(() => {
  const v = props.modelValue;
  if (v === undefined || v === null || v === '') return null;
  return String(v);
});

const multiSelectValue = computed(() => {
  const v = props.modelValue;
  if (!Array.isArray(v)) return [];
  return v.map(String);
});

function emitValue(value: unknown) {
  emit('update:modelValue', value);
}
</script>
