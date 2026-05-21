<template>
  <div v-if="loading" class="inline-md">
    <n-spin size="small" />
  </div>
  <div v-else-if="html" class="inline-md" v-html="html" />
  <n-text v-else-if="text" depth="3">{{ text }}</n-text>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { NSpin, NText } from 'naive-ui';
import { getProjectFileUrl } from '@/api/projects';
import { extractSparkitObjectKeys, replaceSparkitImages, renderInlineImageHtml } from '@/utils/inlineImage';

const props = defineProps<{
  text?: string | null;
  projectId?: string | null;
}>();

const loading = ref(false);
const resolvedText = ref('');

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
</script>

<style scoped>
.inline-md {
  line-height: 1.6;
  word-break: break-word;
}
.inline-md :deep(.inline-md-img) {
  max-width: 100%;
  margin: 8px 0;
  border-radius: 6px;
  border: 1px solid var(--n-border-color);
  display: block;
}
</style>
