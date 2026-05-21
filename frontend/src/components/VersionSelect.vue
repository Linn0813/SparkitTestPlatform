<template>
  <n-select
    :value="modelValue"
    :options="options"
    :disabled="disabled || !projectId"
    :loading="loading"
    filterable
    clearable
    :placeholder="placeholder"
    style="width: 100%"
    @update:value="(v) => emit('update:modelValue', v ?? null)"
  >
    <template #action>
      <n-button
        quaternary
        block
        size="small"
        :disabled="!projectId"
        @click.stop="openCreateModal"
      >
        + 新建版本
      </n-button>
    </template>
  </n-select>
  <n-modal
    v-model:show="showCreate"
    preset="dialog"
    title="新建版本"
    positive-text="创建"
    @positive-click="onCreate"
  >
    <n-input v-model:value="newName" placeholder="如 v1.2.0、Sprint-2025-W20" @keydown.enter.prevent="onCreate" />
  </n-modal>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { NButton, NInput, NModal, NSelect, useMessage } from 'naive-ui';
import { createVersion, listVersions } from '@/api/versions';
import { FILTER_EMPTY_OPTION } from '@/constants/bugFilters';
import type { ProjectVersion } from '@/types/business';

const props = withDefaults(
  defineProps<{
    modelValue: string | null;
    projectId?: string | null;
    disabled?: boolean;
    placeholder?: string;
    /** 筛选场景：增加「（空）」选项 */
    allowEmptyFilter?: boolean;
  }>(),
  { disabled: false, placeholder: '请选择版本', allowEmptyFilter: false }
);

const emit = defineEmits<{
  'update:modelValue': [value: string | null];
}>();

const message = useMessage();
const versions = ref<ProjectVersion[]>([]);
const loading = ref(false);
const showCreate = ref(false);
const newName = ref('');

const options = computed(() => {
  const versionOpts = versions.value.map((v) => ({ label: v.name, value: v.id }));
  return props.allowEmptyFilter ? [FILTER_EMPTY_OPTION, ...versionOpts] : versionOpts;
});

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

function openCreateModal() {
  newName.value = '';
  showCreate.value = true;
}

async function onCreate() {
  const name = newName.value.trim();
  if (!name) {
    message.warning('请输入版本名称');
    return false;
  }
  if (!props.projectId) {
    message.warning('请先选择项目');
    return false;
  }
  try {
    const { data } = await createVersion({ name });
    versions.value = [data, ...versions.value.filter((v) => v.id !== data.id)];
    emit('update:modelValue', data.id);
    showCreate.value = false;
    message.success('版本已创建');
    return true;
  } catch (e: unknown) {
    const detail =
      (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
      '创建失败';
    message.error(typeof detail === 'string' ? detail : '创建失败');
    return false;
  }
}

onMounted(load);
watch(() => props.projectId, load);

defineExpose({ reload: load });
</script>
