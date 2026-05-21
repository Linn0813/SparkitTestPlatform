<template>
  <div class="paste-image-textarea">
    <n-input
      ref="inputRef"
      :value="modelValue"
      type="textarea"
      :autosize="autosize"
      :rows="rows"
      :disabled="disabled"
      :placeholder="placeholder"
      @update:value="(v) => emit('update:modelValue', v)"
      @paste="onPaste"
    />
    <n-text v-if="!disabled && projectId" depth="3" class="paste-hint">
      支持 Ctrl+V / ⌘V 在光标处粘贴截图或图片
    </n-text>
    <n-alert v-else-if="!disabled && !projectId" type="warning" :show-icon="false" style="margin-top: 6px">
      请先选择项目后再粘贴图片
    </n-alert>
  </div>
</template>

<script setup lang="ts">
import { nextTick, ref } from 'vue';
import { NAlert, NInput, NText, useMessage } from 'naive-ui';
import type { InputInst } from 'naive-ui';
import { uploadProjectFile } from '@/api/projects';
import { imageMarkdown, insertTextAtCursor } from '@/utils/inlineImage';

const props = withDefaults(
  defineProps<{
    modelValue: string;
    projectId?: string | null;
    disabled?: boolean;
    placeholder?: string;
    rows?: number;
    autosize?: boolean | { minRows?: number; maxRows?: number };
  }>(),
  {
    disabled: false,
    rows: 4,
    autosize: () => ({ minRows: 3, maxRows: 12 }),
  }
);

const emit = defineEmits<{
  'update:modelValue': [value: string];
}>();

const message = useMessage();
const inputRef = ref<InputInst | null>(null);
const uploading = ref(false);

function getTextareaEl(): HTMLTextAreaElement | null {
  return inputRef.value?.textareaElRef ?? null;
}

function clipboardImageFile(event: ClipboardEvent): File | null {
  const items = event.clipboardData?.items;
  if (!items) return null;
  for (const item of items) {
    if (item.type.startsWith('image/')) {
      const blob = item.getAsFile();
      if (blob) {
        const ext = item.type.split('/')[1]?.replace('jpeg', 'jpg') || 'png';
        return new File([blob], `paste-${Date.now()}.${ext}`, { type: item.type });
      }
    }
  }
  return null;
}

async function onPaste(event: ClipboardEvent) {
  if (props.disabled || uploading.value) return;
  const file = clipboardImageFile(event);
  if (!file) return;

  if (!props.projectId) {
    message.warning('请先选择项目');
    return;
  }

  event.preventDefault();
  const el = getTextareaEl();
  const start = el?.selectionStart ?? props.modelValue.length;
  const end = el?.selectionEnd ?? start;

  uploading.value = true;
  try {
    const { data } = await uploadProjectFile(props.projectId, file);
    const snippet = imageMarkdown(data.object_key, data.filename);
    const wrapped = `\n${snippet}\n`;
    const { text, cursor } = insertTextAtCursor(props.modelValue, wrapped, start, end);
    emit('update:modelValue', text);
    await nextTick();
    if (el) {
      el.focus();
      el.setSelectionRange(cursor, cursor);
    }
    message.success('图片已插入');
  } catch {
    message.error('图片上传失败');
  } finally {
    uploading.value = false;
  }
}
</script>

<style scoped>
.paste-image-textarea {
  width: 100%;
}
.paste-hint {
  display: block;
  font-size: 12px;
  margin-top: 6px;
}
</style>
