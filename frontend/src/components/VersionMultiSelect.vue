<template>
  <n-select
    :value="modelValue"
    :options="options"
    :disabled="disabled || !projectId"
    :loading="loading"
    filterable
    clearable
    multiple
    max-tag-count="responsive"
    :placeholder="placeholder"
    style="width: 100%"
    @update:value="onUpdate"
  />
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { NSelect } from 'naive-ui';
import { listVersions } from '@/api/versions';
import { FILTER_EMPTY_OPTION } from '@/constants/bugFilters';
import type { ProjectVersion } from '@/types/business';

const props = withDefaults(
  defineProps<{
    modelValue: string[];
    projectId?: string | null;
    disabled?: boolean;
    placeholder?: string;
  }>(),
  {
    disabled: false,
    placeholder: '全部',
  }
);

const emit = defineEmits<{
  'update:modelValue': [value: string[]];
}>();

const versions = ref<ProjectVersion[]>([]);
const loading = ref(false);

const options = computed(() => {
  const versionOpts = versions.value.map((v) => ({ label: v.name, value: v.id }));
  return [FILTER_EMPTY_OPTION, ...versionOpts];
});

function onUpdate(value: string[] | null) {
  emit('update:modelValue', value ?? []);
}

async function load() {
  if (!props.projectId) {
    versions.value = [];
    return;
  }
  loading.value = true;
  try {
    const { data } = await listVersions();
    versions.value = data;
  } finally {
    loading.value = false;
  }
}

onMounted(load);
watch(() => props.projectId, load);
</script>
