<template>
  <template v-if="fields.length">
    <n-descriptions-item
      v-for="field in fields"
      :key="field.id"
      :label="field.name"
      :span="isRichtextType(field.type) ? 2 : 1"
    >
      <InlineMarkdownContent
        v-if="isRichtextType(field.type) && richTextHasContent(values[field.id])"
        :text="richTextPlain(values[field.id])"
        :project-id="projectId"
      />
      <template v-else>{{ formatTemplateFieldValue(field, values[field.id], formatCtx) }}</template>
    </n-descriptions-item>
  </template>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { NDescriptionsItem } from 'naive-ui';
import InlineMarkdownContent from '@/components/InlineMarkdownContent.vue';
import {
  formatTemplateFieldValue,
  isRichtextType,
  richTextHasContent,
  richTextPlain,
  type TemplateFieldFormatContext,
} from '@/schemas/entityFieldSchema';
import type { TemplateField } from '@/types/business';

const props = defineProps<{
  fields: TemplateField[];
  values: Record<string, unknown>;
  projectId?: string | null;
  memberLabel?: (userId: string) => string;
}>();

const formatCtx = computed<TemplateFieldFormatContext>(() => ({
  memberLabel: props.memberLabel,
}));
</script>
