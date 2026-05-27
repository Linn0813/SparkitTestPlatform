<template>
  <div v-if="urls.length" class="external-url-links">
    <a
      v-for="(url, i) in urls"
      :key="`${i}-${url}`"
      :href="url"
      target="_blank"
      rel="noopener noreferrer"
      class="external-url-links__item"
    >
      {{ linkLabel(url, labelMaxLen) }}
    </a>
  </div>
  <span v-else-if="fallbackText" class="external-url-links__fallback">{{ fallbackText }}</span>
  <span v-else>—</span>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { linkLabel, parseUrlsFromText } from '@/utils/parseUrls';

const props = withDefaults(
  defineProps<{
    value: string | null | undefined;
    labelMaxLen?: number;
    dedupe?: boolean;
  }>(),
  { labelMaxLen: 80, dedupe: false }
);

const raw = computed(() => props.value?.trim() ?? '');
const urls = computed(() => parseUrlsFromText(raw.value, { dedupe: props.dedupe }));
const fallbackText = computed(() => {
  if (!raw.value) return '';
  if (urls.value.length > 0) return '';
  return raw.value;
});
</script>

<style scoped>
.external-url-links {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}
.external-url-links__item {
  color: var(--n-primary-color, #18a058);
  text-decoration: none;
  word-break: break-all;
  line-height: 1.5;
}
.external-url-links__item:hover {
  text-decoration: underline;
}
.external-url-links__fallback {
  word-break: break-all;
}
</style>
