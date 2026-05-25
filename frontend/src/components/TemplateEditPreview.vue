<template>
  <div class="preview-shell">
    <div class="preview-drawer-bar">
      <span class="preview-drawer-title">{{ drawerTitle }}</span>
      <n-tag size="small" :bordered="false">只读预览</n-tag>
    </div>
    <div class="preview-drawer-body">
      <n-form label-placement="top" class="preview-form">
        <div class="field-section">
          <div class="section-head">
            <n-tag size="small" :bordered="false" type="default">系统固定</n-tag>
            <span class="section-desc">编辑页始终存在，不可在本页配置</span>
          </div>
          <template v-if="scene === 'case'">
            <n-form-item label="用例标题">
              <n-input disabled placeholder="示例用例标题" />
            </n-form-item>
            <n-form-item label="模块">
              <n-select disabled value="module" :options="[{ label: '示例模块', value: 'module' }]" style="width: 100%" />
            </n-form-item>
            <n-form-item label="优先级">
              <n-select disabled value="P2" :options="casePriorityOptions" style="width: 100%" />
            </n-form-item>
            <n-form-item label="前置条件">
              <n-input disabled type="textarea" placeholder="示例前置条件" :rows="2" />
            </n-form-item>
            <n-form-item label="步骤">
              <n-input disabled type="textarea" placeholder="示例步骤" :rows="2" />
            </n-form-item>
            <n-form-item label="预期结果">
              <n-input disabled type="textarea" placeholder="示例预期结果" :rows="2" />
            </n-form-item>
            <n-form-item label="关联需求">
              <n-select disabled placeholder="可选，多选" style="width: 100%" />
            </n-form-item>
          </template>
          <template v-else-if="scene === 'bug'">
            <n-form-item label="缺陷标题">
              <n-input disabled placeholder="示例缺陷标题" />
            </n-form-item>
            <n-form-item label="状态">
              <n-select
                disabled
                :value="statusOptions[0]?.value"
                :options="statusOptions"
                style="width: 100%"
              />
            </n-form-item>
            <n-form-item label="提出人">
              <n-select disabled placeholder="项目成员" style="width: 100%" />
            </n-form-item>
            <n-form-item label="跟进人">
              <n-select disabled placeholder="可多选项目成员" style="width: 100%" />
            </n-form-item>
            <n-form-item label="描述">
              <PasteImageTextarea
                disabled
                model-value=""
                :project-id="projectId"
                placeholder="示例：可输入文字并粘贴截图"
              />
            </n-form-item>
            <n-form-item label="附件">
              <n-button disabled>上传</n-button>
            </n-form-item>
            <n-form-item label="关联需求">
              <n-select disabled placeholder="可选，多选" style="width: 100%" />
            </n-form-item>
            <n-form-item label="关联测试计划">
              <n-select disabled placeholder="可选，多选" style="width: 100%" />
            </n-form-item>
            <n-form-item label="规划迭代">
              <n-select disabled placeholder="可选" style="width: 100%" />
            </n-form-item>
            <n-form-item label="发现版本">
              <n-select disabled placeholder="可选" style="width: 100%" />
            </n-form-item>
          </template>
          <template v-else>
            <n-form-item label="需求标题">
              <n-input disabled placeholder="示例需求标题" />
            </n-form-item>
            <n-form-item label="优先级">
              <n-space :size="6" wrap>
                <n-tag
                  v-for="opt in reqPriorityOptions"
                  :key="opt.value"
                  size="small"
                  :bordered="false"
                >
                  {{ opt.label }}
                </n-tag>
              </n-space>
            </n-form-item>
            <n-form-item label="需求类型">
              <n-space :size="6" wrap>
                <n-tag
                  v-for="opt in reqTypeOptions"
                  :key="opt.value"
                  size="small"
                  :bordered="false"
                >
                  {{ opt.label }}
                </n-tag>
              </n-space>
            </n-form-item>
            <n-form-item label="PRD / 外部链接">
              <n-input disabled placeholder="可选" />
            </n-form-item>
            <n-form-item label="关联版本">
              <n-select disabled placeholder="可选" style="width: 100%" />
            </n-form-item>
            <n-form-item label="版本上线时间">
              <n-input disabled placeholder="随关联版本自动带出" />
            </n-form-item>
          </template>
        </div>

        <div class="field-section field-section--template">
          <div class="section-head">
            <n-tag size="small" :bordered="false" type="success">模板可配置</n-tag>
            <span class="section-desc">与左侧字段表同步，保存模板后生效</span>
          </div>
          <template v-if="sortedFields.length">
            <n-form-item
              v-for="field in sortedFields"
              :key="field.id"
              :label="field.name"
              :required="field.required"
            >
              <TemplateFieldInput
                :field="field"
                :model-value="previewControlValue(field)"
                :project-id="projectId"
                disabled
                :placeholder="previewPlaceholder(field)"
              />
            </n-form-item>
          </template>
          <n-empty v-else size="small" description="暂无自定义字段，点击「添加字段」后此处会显示" />
        </div>
      </n-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { NButton, NEmpty, NForm, NFormItem, NInput, NSelect, NTag } from 'naive-ui';
import PasteImageTextarea from '@/components/PasteImageTextarea.vue';
import TemplateFieldInput from '@/components/TemplateFieldInput.vue';
import {
  fieldDefaultValue,
  isMemberType,
  isOptionFieldType,
  isRichtextType,
  mergeCustomFields,
  normalizeRichTextValue,
  sortTemplateFields,
} from '@/constants/fieldTypes';
import type { BugStatusDef, RequirementOptionDef, TemplateField } from '@/types/business';

const props = withDefaults(
  defineProps<{
    scene: 'case' | 'bug' | 'requirement';
    fields: TemplateField[];
    projectId?: string | null;
    bugStatuses?: BugStatusDef[];
    priorityOptions?: RequirementOptionDef[];
    typeOptions?: RequirementOptionDef[];
  }>(),
  {
    bugStatuses: () => [],
    priorityOptions: () => [] as RequirementOptionDef[],
    typeOptions: () => [] as RequirementOptionDef[],
  }
);

const sortedFields = computed(() => sortTemplateFields(props.fields));

const drawerTitle = computed(() => {
  if (props.scene === 'case') return '新建用例';
  if (props.scene === 'bug') return '新建缺陷';
  return '新建需求';
});

const casePriorityOptions = ['P0', 'P1', 'P2', 'P3'].map((v) => ({ label: v, value: v }));

const reqPriorityOptions = computed(() =>
  props.priorityOptions.length
    ? props.priorityOptions.map((o) => ({ label: o.label, value: o.option_key }))
    : [
        { label: 'P00', value: 'p00' },
        { label: 'P0', value: 'p0' },
        { label: 'P1', value: 'p1' },
      ]
);

const reqTypeOptions = computed(() =>
  props.typeOptions.length
    ? props.typeOptions.map((o) => ({ label: o.label, value: o.option_key }))
    : [
        { label: '需求开发', value: 'feature' },
        { label: '技术优化', value: 'tech_optimization' },
      ]
);

const statusOptions = ref<{ label: string; value: string }[]>([]);

const previewValues = ref<Record<string, unknown>>({});

watch(
  () => props.bugStatuses,
  (list) => {
    statusOptions.value = list.length
      ? list.map((s) => ({ label: s.label, value: s.key }))
      : [
          { label: '待确认', value: 'pending_confirm' },
          { label: '处理中', value: 'in_progress' },
          { label: '已修复', value: 'fixed' },
          { label: '已验收', value: 'accepted' },
          { label: '已拒绝', value: 'rejected' },
          { label: '挂起', value: 'suspended' },
          { label: '转需求', value: 'to_requirement' },
        ];
  },
  { immediate: true, deep: true }
);

watch(
  () => props.fields,
  (fields) => {
    previewValues.value = mergeCustomFields(fields, previewValues.value);
  },
  { immediate: true, deep: true }
);

function previewPlaceholder(field: TemplateField) {
  return `示例：${field.name}`;
}

function previewControlValue(field: TemplateField): unknown {
  const v = previewValues.value[field.id];
  if (v !== undefined && v !== null && v !== '' && !(Array.isArray(v) && !v.length)) {
    return v;
  }
  if (isRichtextType(field.type)) {
    return normalizeRichTextValue(v);
  }
  if (isOptionFieldType(field.type)) {
    const opts = field.options ?? [];
    if (field.type === 'multi_select') return opts.length ? [opts[0]] : [];
    return opts[0] ?? null;
  }
  if (isMemberType(field.type)) {
    return null;
  }
  return fieldDefaultValue(field.type);
}
</script>

<style scoped>
.preview-shell {
  border: 1px solid var(--n-border-color);
  border-radius: 8px;
  overflow: hidden;
  background: var(--n-color);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  position: sticky;
  top: 12px;
}

.preview-drawer-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--n-border-color);
  background: var(--n-color-modal);
}

.preview-drawer-title {
  font-weight: 600;
  font-size: 15px;
}

.preview-drawer-body {
  padding: 16px;
  max-height: min(720px, calc(100vh - 200px));
  overflow-y: auto;
  background: #fafafa;
}

.preview-form :deep(.n-form-item) {
  margin-bottom: 18px;
}

.field-section {
  margin-bottom: 8px;
}

.field-section--template {
  padding-top: 4px;
  border-top: 1px dashed var(--n-border-color);
  margin-top: 8px;
}

.section-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}

.section-desc {
  font-size: 12px;
  color: var(--n-text-color-3);
}

.preview-form :deep(.n-input--disabled),
.preview-form :deep(.n-base-selection--disabled) {
  opacity: 1;
}
</style>
