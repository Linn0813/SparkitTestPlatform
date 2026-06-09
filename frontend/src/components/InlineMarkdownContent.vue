<template>
  <div v-if="loading" class="inline-md">
    <n-spin size="small" />
  </div>
  <div
    v-else-if="html"
    class="inline-md"
    v-html="html"
    @click="onContentClick"
  />
  <n-text v-else-if="text" depth="3">{{ text }}</n-text>

  <n-modal
    v-model:show="previewVisible"
    preset="card"
    :title="previewAlt || '图片预览'"
    class="inline-md-preview-modal"
    style="width: auto; max-width: min(960px, 92vw)"
    @after-leave="clearPreview"
  >
    <img
      v-if="previewSrc"
      :src="previewSrc"
      :alt="previewAlt"
      class="inline-md-preview-img"
    />
  </n-modal>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { NModal, NSpin, NText } from 'naive-ui';
import { getProjectFileUrl } from '@/api/projects';
import { extractSparkitObjectKeys, replaceSparkitImages, renderInlineImageHtml } from '@/utils/inlineImage';

const props = defineProps<{
  text?: string | null;
  projectId?: string | null;
}>();

const loading = ref(false);
const resolvedText = ref('');
const previewVisible = ref(false);
const previewSrc = ref('');
const previewAlt = ref('');

watch(
  () => [props.text, props.projectId] as const,
  async () => {
    const raw = props.text ?? '';
    if (!raw) {
      resolvedText.value = '';
      return;
    }
    const keys = extractSparkitObjectKeys(raw);
    if (!keys.length || !props.projectId) {
      resolvedText.value = raw;
      return;
    }
    loading.value = true;
    try {
      const urlByKey: Record<string, string> = {};
      await Promise.all(
        keys.map(async (key) => {
          try {
            const { data } = await getProjectFileUrl(props.projectId!, key);
            urlByKey[key] = data.url;
          } catch {
            /* skip */
          }
        })
      );
      resolvedText.value = replaceSparkitImages(raw, urlByKey);
    } finally {
      loading.value = false;
    }
  },
  { immediate: true }
);

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

const html = computed(() => {
  const t = resolvedText.value;
  if (!t) return '';
  const escaped = escapeHtml(t);
  const withImages = renderInlineImageHtml(escaped);
  return withImages.replace(/\n/g, '<br />');
});

function onContentClick(event: MouseEvent) {
  const target = event.target;
  if (!(target instanceof HTMLImageElement)) return;
  if (!target.classList.contains('inline-md-img')) return;
  previewSrc.value = target.currentSrc || target.src;
  previewAlt.value = target.alt || '图片预览';
  previewVisible.value = true;
}

function clearPreview() {
  previewSrc.value = '';
  previewAlt.value = '';
}
</script>

<style scoped>
.inline-md {
  line-height: 1.6;
  word-break: break-word;
}
.inline-md :deep(.inline-md-img) {
  max-width: min(100%, 320px);
  max-height: 240px;
  width: auto;
  height: auto;
  object-fit: contain;
  margin: 8px 0;
  border-radius: 6px;
  border: 1px solid var(--n-border-color);
  display: block;
  cursor: zoom-in;
  background: var(--n-color-modal);
}
.inline-md-preview-img {
  display: block;
  max-width: min(920px, 88vw);
  max-height: 78vh;
  width: auto;
  height: auto;
  margin: 0 auto;
  object-fit: contain;
}
</style>
