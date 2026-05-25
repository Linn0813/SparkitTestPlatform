<template>
  <div v-if="!projectId" class="settings-empty">
    <n-text depth="3">请选择项目</n-text>
  </div>
  <div v-else class="req-field-settings">
    <div class="template-editor-layout">
      <TemplateFieldPanel
        class="template-editor-config"
        scene="requirement"
        :fields="reqFields"
        :saving="saving"
        :read-only="readOnly"
        :option-counts="optionCounts"
        @update:fields="reqFields = $event"
        @add="emit('add-field')"
        @edit="(i) => emit('edit-field', i)"
        @edit-options="openOptionsDrawer"
        @save="saveTemplate"
      />
      <TemplateEditPreview
        class="template-editor-preview"
        scene="requirement"
        :fields="reqFields"
        :project-id="projectId"
        :priority-options="priorities"
        :type-options="types"
      />
    </div>

    <n-drawer v-model:show="showOptionsDrawer" :width="480" placement="right">
      <n-drawer-content :title="optionsDrawerTitle" closable>
        <n-data-table
          :columns="drawerOptionColumns"
          :data="drawerOptions"
          :loading="loading"
          size="small"
        />
        <n-button v-if="!readOnly" size="small" style="margin-top: 8px" @click="openOptionModal()">添加选项</n-button>
      </n-drawer-content>
    </n-drawer>

    <n-modal
      v-model:show="showOptionModal"
      preset="dialog"
      :title="editingOption ? '编辑选项' : '添加选项'"
      positive-text="保存"
      @positive-click="onSaveOption"
    >
      <n-form label-width="100">
        <n-form-item label="选项标识">
          <n-input
            v-model:value="optionForm.option_key"
            :disabled="!!editingOption"
            placeholder="如 p2"
          />
        </n-form-item>
        <n-form-item label="显示名">
          <n-input v-model:value="optionForm.label" placeholder="如 P2" />
        </n-form-item>
      </n-form>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, h, onMounted, ref, watch } from 'vue';
import {
  NButton,
  NDataTable,
  NDrawer,
  NDrawerContent,
  NForm,
  NFormItem,
  NInput,
  NModal,
  NSpace,
  NText,
  useDialog,
  useMessage,
  type DataTableColumns,
} from 'naive-ui';
import {
  createRequirementOption,
  deleteRequirementOption,
  getTemplate,
  updateRequirementOption,
  updateTemplate,
  type RequirementOptionDef,
} from '@/api/templates';
import TemplateEditPreview from '@/components/TemplateEditPreview.vue';
import TemplateFieldPanel from '@/components/TemplateFieldPanel.vue';
import type { RequirementOptionCategory, SystemOptionCategory } from '@/constants/systemFields';
import { invalidateRequirementProjectConfig, loadRequirementOptions } from '@/composables/useRequirementProjectConfig';
import { invalidateProjectFieldSchemaCache } from '@/composables/useProjectFieldSchema';
import { normalizeFieldSort } from '@/constants/fieldTypes';
import { validateTemplateFieldNames } from '@/schemas/entityFieldSchema';
import { apiErrorMessage } from '@/utils/apiError';
import type { TemplateField } from '@/types/business';

const props = defineProps<{
  projectId: string | null;
  reqFields: TemplateField[];
  saving?: boolean;
  readOnly?: boolean;
}>();

const emit = defineEmits<{
  'update:reqFields': [TemplateField[]];
  'add-field': [];
  'edit-field': [index: number];
}>();

const message = useMessage();
const dialog = useDialog();
const loading = ref(false);
const priorities = ref<RequirementOptionDef[]>([]);
const types = ref<RequirementOptionDef[]>([]);
const showOptionsDrawer = ref(false);
const showOptionModal = ref(false);
const optionCategory = ref<RequirementOptionCategory>('priority');
const editingOption = ref<RequirementOptionDef | null>(null);
const optionForm = ref({ option_key: '', label: '' });

const reqFields = computed({
  get: () => props.reqFields,
  set: (v) => emit('update:reqFields', v),
});

const optionCounts = computed(() => ({
  priority: priorities.value.length,
  req_type: types.value.length,
}));

const drawerOptions = computed(() =>
  optionCategory.value === 'priority' ? priorities.value : types.value
);

const optionsDrawerTitle = computed(() =>
  optionCategory.value === 'priority' ? '编辑优先级选项' : '编辑需求类型选项'
);

const drawerOptionColumns = computed<DataTableColumns<RequirementOptionDef>>(() => {
  const cols: DataTableColumns<RequirementOptionDef> = [
  { title: '标识', key: 'option_key', width: 120 },
  { title: '名称', key: 'label' },
  ];
  if (props.readOnly) return cols;
  cols.push({
    title: '操作',
    key: 'actions',
    width: 200,
    render: (row, index) =>
      h(NSpace, { size: 4 }, () => [
        h(
          NButton,
          {
            size: 'tiny',
            quaternary: true,
            disabled: index === 0,
            onClick: () => moveOption(index, -1),
          },
          () => '上移'
        ),
        h(
          NButton,
          {
            size: 'tiny',
            quaternary: true,
            disabled: index === drawerOptions.value.length - 1,
            onClick: () => moveOption(index, 1),
          },
          () => '下移'
        ),
        h(NButton, { size: 'tiny', quaternary: true, type: 'primary', onClick: () => openOptionModal(row) }, () => '编辑'),
        h(NButton, { size: 'tiny', quaternary: true, type: 'error', onClick: () => removeOption(row) }, () => '删除'),
      ]),
  });
  return cols;
});

function openOptionsDrawer(category: SystemOptionCategory) {
  if (props.readOnly || category === 'bug_status') return;
  optionCategory.value = category;
  showOptionsDrawer.value = true;
}

async function load() {
  if (!props.projectId) {
    priorities.value = [];
    types.value = [];
    return;
  }
  loading.value = true;
  try {
    const [p, t, tpl] = await Promise.all([
      loadRequirementOptions(props.projectId, 'priority', true),
      loadRequirementOptions(props.projectId, 'req_type', true),
      getTemplate(props.projectId, 'requirement'),
    ]);
    priorities.value = p;
    types.value = t;
    emit('update:reqFields', (tpl.data.fields ?? []) as TemplateField[]);
  } catch {
    message.error('加载需求字段配置失败');
  } finally {
    loading.value = false;
  }
}

function openOptionModal(row?: RequirementOptionDef) {
  editingOption.value = row ?? null;
  optionForm.value = row
    ? { option_key: row.option_key, label: row.label }
    : { option_key: '', label: '' };
  showOptionModal.value = true;
}

async function moveOption(index: number, delta: number) {
  if (!props.projectId) return;
  const list = [...drawerOptions.value];
  const j = index + delta;
  if (j < 0 || j >= list.length) return;
  [list[index], list[j]] = [list[j], list[index]];
  try {
    await Promise.all(list.map((o, i) => updateRequirementOption(props.projectId!, o.id, { sort: i })));
    invalidateRequirementProjectConfig(props.projectId);
    await load();
  } catch {
    message.error('排序失败');
  }
}

function removeOption(row: RequirementOptionDef) {
  if (!props.projectId) return;
  dialog.warning({
    title: '确认删除',
    content: `删除选项「${row.label}」？若有需求使用该选项将无法删除。`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      const projectId = props.projectId;
      if (!projectId) return;
      try {
        await deleteRequirementOption(projectId, row.id);
        invalidateRequirementProjectConfig(projectId);
        message.success('已删除');
        await load();
      } catch (e) {
        message.error(apiErrorMessage(e, '删除失败'));
      }
    },
  });
}

async function onSaveOption() {
  if (!props.projectId) return false;
  const optionKey = optionForm.value.option_key.trim();
  const label = optionForm.value.label.trim();
  if (!optionKey || !label) {
    message.warning('请填写选项标识和名称');
    return false;
  }
  try {
    if (editingOption.value) {
      await updateRequirementOption(props.projectId, editingOption.value.id, { label });
    } else {
      await createRequirementOption(props.projectId, {
        category: optionCategory.value,
        option_key: optionKey,
        label,
        sort: drawerOptions.value.length,
      });
    }
    invalidateRequirementProjectConfig(props.projectId);
    showOptionModal.value = false;
    message.success('已保存');
    await load();
    return true;
  } catch (e) {
    message.error(apiErrorMessage(e, '保存失败'));
    return false;
  }
}

async function saveTemplate() {
  if (!props.projectId) return;
  const nameErr = validateTemplateFieldNames('requirement', reqFields.value);
  if (nameErr) {
    message.warning(nameErr);
    return;
  }
  try {
    await updateTemplate(props.projectId, 'requirement', normalizeFieldSort(reqFields.value));
    invalidateProjectFieldSchemaCache(props.projectId, 'requirement');
    message.success('自定义字段已保存');
    await load();
  } catch (e) {
    message.error(apiErrorMessage(e, '保存失败'));
  }
}

onMounted(load);
watch(() => props.projectId, load);
</script>

<style scoped>
.settings-empty {
  padding: 24px;
}
.template-editor-layout {
  display: grid;
  grid-template-columns: 1fr 400px;
  gap: 20px;
  align-items: start;
}
@media (max-width: 1100px) {
  .template-editor-layout {
    grid-template-columns: 1fr;
  }
  .template-editor-preview {
    order: -1;
  }
}
</style>
