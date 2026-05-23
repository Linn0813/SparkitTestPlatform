<template>
  <n-form label-placement="top" size="small" class="bug-form-fields">
    <n-grid :cols="2" :x-gap="12" :y-gap="2">
      <n-gi :span="2">
        <n-form-item label="缺陷标题" required>
          <n-input v-model:value="form.title" placeholder="请输入缺陷标题" size="small" />
        </n-form-item>
      </n-gi>
      <n-gi :span="2">
        <n-form-item label="描述">
          <PasteImageTextarea
            v-model="form.description"
            :project-id="projectId"
            compact
            placeholder="描述（支持 Ctrl+V / ⌘V 粘贴截图）"
            :autosize="{ minRows: 2, maxRows: 8 }"
          />
        </n-form-item>
      </n-gi>
      <n-gi :span="2">
        <n-form-item label="状态">
          <n-radio-group v-model:value="form.status_key" name="bug-status" size="small">
            <n-space wrap :size="[4, 4]">
              <n-radio-button v-for="opt in statusOptions" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </n-radio-button>
            </n-space>
          </n-radio-group>
        </n-form-item>
      </n-gi>
      <n-gi v-for="field in promotedFields" :key="field.id">
        <n-form-item :label="field.name" :required="field.required">
          <SelectRadioField
            :model-value="customFieldString(field.id)"
            :options="field.options ?? []"
            :name="`promoted-${field.id}`"
            @update:model-value="(v) => setCustomField(field.id, v)"
          />
        </n-form-item>
      </n-gi>
      <n-gi>
        <n-form-item label="提出人">
          <n-select v-model:value="form.reporter_id" :options="reporterFollowerOptions" filterable size="small" />
        </n-form-item>
      </n-gi>
      <n-gi>
        <n-form-item label="跟进人">
          <n-select
            v-model:value="form.follower_ids"
            :options="reporterFollowerOptions"
            multiple
            filterable
            clearable
            size="small"
          />
        </n-form-item>
      </n-gi>
      <n-gi>
        <n-form-item label="规划迭代">
          <VersionSelect v-model="form.plan_version_id" :project-id="projectId" />
        </n-form-item>
      </n-gi>
      <n-gi>
        <n-form-item label="发现版本">
          <VersionSelect v-model="form.found_version_id" :project-id="projectId" />
        </n-form-item>
      </n-gi>
      <n-gi>
        <n-form-item label="关联需求">
          <n-select
            v-model:value="form.requirement_ids"
            :options="requirementOptions"
            multiple
            filterable
            clearable
            size="small"
          />
        </n-form-item>
      </n-gi>
      <n-gi>
        <n-form-item label="关联测试计划">
          <n-select
            v-model:value="form.plan_ids"
            :options="planOptions"
            multiple
            filterable
            clearable
            size="small"
          />
        </n-form-item>
      </n-gi>
      <n-gi v-if="restFields.length" :span="2">
        <DynamicFieldForm
          v-model="customFieldsModel"
          :fields="restFields"
          :project-id="projectId"
          :columns="2"
          compact
        />
      </n-gi>
      <n-gi v-if="mode === 'edit'" :span="2">
        <n-form-item label="附件">
          <slot name="attachments" />
        </n-form-item>
      </n-gi>
    </n-grid>
  </n-form>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import {
  NForm,
  NFormItem,
  NGi,
  NGrid,
  NInput,
  NRadioButton,
  NRadioGroup,
  NSelect,
  NSpace,
} from 'naive-ui';
import DynamicFieldForm from '@/components/DynamicFieldForm.vue';
import PasteImageTextarea from '@/components/PasteImageTextarea.vue';
import SelectRadioField from '@/components/SelectRadioField.vue';
import VersionSelect from '@/components/VersionSelect.vue';
import { splitPromotedTemplateFields } from '@/schemas/entityFieldSchema';
import type { TemplateField } from '@/types/business';

export interface BugFormModel {
  title: string;
  status_key: string;
  reporter_id: string | null;
  follower_ids: string[];
  description: string;
  requirement_ids: string[];
  plan_ids: string[];
  plan_version_id: string | null;
  found_version_id: string | null;
}

const form = defineModel<BugFormModel>({ required: true });
const customFieldsModel = defineModel<Record<string, unknown>>('customFields', { required: true });

const props = withDefaults(
  defineProps<{
    projectId: string;
    templateFields: TemplateField[];
    statusOptions: { label: string; value: string }[];
    memberOptions: { label: string; value: string }[];
    memberNameOptions?: { label: string; value: string }[];
    requirementOptions: { label: string; value: string }[];
    planOptions: { label: string; value: string }[];
    mode?: 'create' | 'edit';
  }>(),
  { mode: 'create' }
);

const reporterFollowerOptions = computed(
  () => props.memberNameOptions ?? props.memberOptions
);

const promotedFields = computed(() => splitPromotedTemplateFields(props.templateFields).promoted);
const restFields = computed(() => splitPromotedTemplateFields(props.templateFields).rest);

function customFieldString(fieldId: string): string | null {
  const v = customFieldsModel.value[fieldId];
  if (v === undefined || v === null || v === '') return null;
  return String(v);
}

function setCustomField(fieldId: string, value: string | null) {
  customFieldsModel.value = { ...customFieldsModel.value, [fieldId]: value };
}
</script>

<style scoped>
.bug-form-fields :deep(.n-form-item) {
  margin-bottom: 4px;
}

.bug-form-fields :deep(.n-form-item-label) {
  padding-bottom: 2px;
  min-height: auto;
}

.bug-form-fields :deep(.n-input),
.bug-form-fields :deep(.n-select),
.bug-form-fields :deep(.n-tree-select) {
  width: 100%;
}
</style>
