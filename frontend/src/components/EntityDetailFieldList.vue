<template>
  <div class="entity-detail-field-list">
    <template v-for="(group, index) in layoutGroups" :key="index">
      <div v-if="group.type === 'full'" class="field-full">
        <div class="field-cell">
          <div class="field-label">{{ group.row.name }}</div>
          <div class="field-value">
            <InlineMarkdownContent
              v-if="fieldEntries[group.row.id]?.display.kind === 'richtext'"
              :text="fieldEntries[group.row.id]!.display.text"
              :project-id="projectId"
            />
            <ExternalUrlLinks
              v-else-if="isUrlFieldDisplay(fieldEntries[group.row.id]?.display)"
              :value="urlFieldRawValue(fieldEntries[group.row.id]!.display)"
            />
            <span v-else>{{ fieldEntries[group.row.id]?.display.text ?? '—' }}</span>
          </div>
        </div>
      </div>
      <div v-else class="field-pair">
        <div v-for="row in group.rows" :key="row.id" class="field-cell">
          <div class="field-label">{{ row.name }}</div>
          <div class="field-value">
            <InlineMarkdownContent
              v-if="fieldEntries[row.id]?.display.kind === 'richtext'"
              :text="fieldEntries[row.id]!.display.text"
              :project-id="projectId"
            />
            <ExternalUrlLinks
              v-else-if="isUrlFieldDisplay(fieldEntries[row.id]?.display)"
              :value="urlFieldRawValue(fieldEntries[row.id]!.display)"
            />
            <span v-else>{{ fieldEntries[row.id]?.display.text ?? '—' }}</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import ExternalUrlLinks from '@/components/ExternalUrlLinks.vue';
import InlineMarkdownContent from '@/components/InlineMarkdownContent.vue';
import type { FieldConfigRow } from '@/constants/systemFields';
import {
  buildRequirementDetailLayout,
  resolveRequirementDetailField,
  requirementDetailFieldSpan,
  type RequirementDetailFieldContext,
  type RequirementDetailFieldDisplay,
} from '@/schemas/entityFieldSchema';

const props = defineProps<{
  rows: FieldConfigRow[];
  context: RequirementDetailFieldContext;
  projectId: string;
}>();

interface FieldEntry {
  display: RequirementDetailFieldDisplay;
  span: 1 | 2;
}

const fieldEntries = computed<Record<string, FieldEntry>>(() => {
  const map: Record<string, FieldEntry> = {};
  for (const row of props.rows) {
    map[row.id] = {
      display: resolveRequirementDetailField(row, props.context),
      span: requirementDetailFieldSpan(row, props.context),
    };
  }
  return map;
});

const layoutGroups = computed(() => buildRequirementDetailLayout(props.rows, props.context));

function isUrlFieldDisplay(
  display: RequirementDetailFieldDisplay | undefined
): display is RequirementDetailFieldDisplay {
  return display?.kind === 'link' || display?.kind === 'links';
}

function urlFieldRawValue(display: RequirementDetailFieldDisplay): string {
  return display.urlRaw ?? display.href ?? display.text ?? '';
}
</script>

<style scoped>
.entity-detail-field-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.field-pair {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px 24px;
}
.field-full {
  min-width: 0;
}
.field-cell {
  display: grid;
  grid-template-columns: 100px minmax(0, 1fr);
  gap: 8px 12px;
  align-items: start;
  min-width: 0;
}
.field-label {
  font-size: 13px;
  color: var(--n-text-color-3);
  line-height: 1.5;
}
.field-value {
  font-size: 14px;
  line-height: 1.5;
  word-break: break-word;
  min-width: 0;
}
</style>
