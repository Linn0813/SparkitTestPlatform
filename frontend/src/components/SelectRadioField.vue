<template>
  <n-radio-group
    :value="modelValue ?? null"
    :name="name"
    size="small"
    :disabled="disabled"
    @update:value="onUpdate"
  >
    <n-space wrap :size="[4, 4]">
      <n-radio-button v-for="opt in options" :key="opt" :value="opt">
        {{ opt }}
      </n-radio-button>
    </n-space>
  </n-radio-group>
</template>

<script setup lang="ts">
import { NRadioButton, NRadioGroup, NSpace } from 'naive-ui';

defineProps<{
  modelValue: string | null | undefined;
  options: string[];
  name: string;
  disabled?: boolean;
}>();

const emit = defineEmits<{
  'update:modelValue': [value: string | null];
}>();

function onUpdate(value: string | null) {
  emit('update:modelValue', value);
}
</script>
