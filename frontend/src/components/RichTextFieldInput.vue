<template>
  <div class="richtext-field">
    <PasteImageTextarea
      :model-value="richValue.text"
      :project-id="projectId"
      :disabled="disabled"
      :placeholder="placeholder"
      :autosize="{ minRows: 3, maxRows: 10 }"
      @update:model-value="onTextChange"
    />
    <div v-if="!disabled && projectId" class="richtext-toolbar">
      <n-upload
        :show-file-list="false"
        accept="image/*,video/*"
        :custom-request="onUpload"
        multiple
      >
        <n-button size="small" :loading="uploading">上传图片/视频</n-button>
      </n-upload>
      <n-text depth="3" style="font-size: 12px">支持常见图片与视频格式，单文件最大 50MB</n-text>
    </div>
    <n-alert v-else-if="!disabled && !projectId" type="warning" :show-icon="false" style="margin-top: 8px">
      请先选择项目后再上传附件
    </n-alert>
    <div v-if="richValue.files.length" class="richtext-files">
      <div v-for="(file, index) in richValue.files" :key="file.object_key" class="richtext-file-item">
        <img
          v-if="file.kind === 'image' && fileUrl(file)"
          :src="fileUrl(file)"
          :alt="file.filename"
          class="richtext-thumb"
        />
        <video
          v-else-if="file.kind === 'video' && fileUrl(file)"
          :src="fileUrl(file)"
          controls
          class="richtext-video"
        />
        <n-text v-else depth="3">{{ file.filename }}</n-text>
        <n-button
          v-if="!disabled"
          size="tiny"
          quaternary
          type="error"
          class="richtext-remove"
          @click="removeFile(index)"
        >
          移除
        </n-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue';
import { NAlert, NButton, NText, NUpload, useMessage } from 'naive-ui';
import PasteImageTextarea from '@/components/PasteImageTextarea.vue';
import type { UploadCustomRequestOptions } from 'naive-ui';
import { getProjectFileUrl, uploadProjectFile } from '@/api/projects';
import { normalizeRichTextValue, type RichTextFieldValue, type RichTextFile } from '@/constants/fieldTypes';

const props = withDefaults(
  defineProps<{
    modelValue: unknown;
    projectId?: string | null;
    disabled?: boolean;
    placeholder?: string;
  }>(),
  { disabled: false }
);

const emit = defineEmits<{
  'update:modelValue': [value: RichTextFieldValue];
}>();

const message = useMessage();
const richValue = ref<RichTextFieldValue>({ text: '', files: [] });
const uploading = ref(false);
const urlCache = ref<Record<string, string>>({});

watch(
  () => props.modelValue,
  (v) => {
    richValue.value = normalizeRichTextValue(v);
    void refreshFileUrls();
  },
  { immediate: true, deep: true }
);

onMounted(() => void refreshFileUrls());

async function refreshFileUrls() {
  if (!props.projectId) return;
  for (const file of richValue.value.files) {
    try {
      const { data } = await getProjectFileUrl(props.projectId, file.object_key);
      urlCache.value[file.object_key] = data.url;
    } catch {
      /* ignore */
    }
  }
}

function fileUrl(file: RichTextFile): string {
  return urlCache.value[file.object_key] || file.url || '';
}

function emitValue() {
  emit('update:modelValue', {
    text: richValue.value.text,
    files: richValue.value.files.map(({ object_key, filename, kind, url }) => ({
      object_key,
      filename,
      kind,
      ...(url ? { url } : {}),
    })),
  });
}

function onTextChange(text: string) {
  richValue.value = { ...richValue.value, text };
  emitValue();
}

function removeFile(index: number) {
  const files = [...richValue.value.files];
  files.splice(index, 1);
  richValue.value = { ...richValue.value, files };
  emitValue();
}

async function onUpload({ file, onFinish, onError }: UploadCustomRequestOptions) {
  if (!props.projectId || !file.file) {
    onError?.();
    return;
  }
  uploading.value = true;
  try {
    const { data } = await uploadProjectFile(props.projectId, file.file as File);
    const entry: RichTextFile = {
      object_key: data.object_key,
      filename: data.filename,
      kind: data.kind as RichTextFile['kind'],
      url: data.url,
    };
    urlCache.value[data.object_key] = data.url;
    richValue.value = {
      ...richValue.value,
      files: [...richValue.value.files, entry],
    };
    emitValue();
    onFinish?.();
  } catch {
    message.error('上传失败');
    onError?.();
  } finally {
    uploading.value = false;
  }
}
</script>

<style scoped>
.richtext-field {
  width: 100%;
}
.richtext-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 8px;
  flex-wrap: wrap;
}
.richtext-files {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 12px;
}
.richtext-file-item {
  position: relative;
  max-width: 100%;
}
.richtext-thumb {
  max-width: 200px;
  max-height: 160px;
  border-radius: 6px;
  border: 1px solid var(--n-border-color);
  display: block;
}
.richtext-video {
  max-width: 280px;
  max-height: 200px;
  border-radius: 6px;
  display: block;
}
.richtext-remove {
  margin-top: 4px;
}
</style>
