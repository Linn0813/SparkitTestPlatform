<template>
  <div v-if="!projectId" class="settings-empty">
    <n-text depth="3">请选择项目</n-text>
  </div>
  <div v-else class="bug-field-settings">
    <div class="template-editor-layout">
      <TemplateFieldPanel
        class="template-editor-config"
        scene="bug"
        :fields="bugFields"
        :saving="saving"
        :read-only="readOnly"
        :option-counts="optionCounts"
        @update:fields="bugFields = $event"
        @add="emit('add-field')"
        @edit="(i) => emit('edit-field', i)"
        @edit-options="openStatusDrawer"
        @save="saveTemplate"
      />
      <TemplateEditPreview
        class="template-editor-preview"
        scene="bug"
        :fields="bugFields"
        :project-id="projectId"
        :bug-statuses="statuses"
      />
    </div>

    <n-drawer v-model:show="showStatusDrawer" :width="520" placement="right">
      <n-drawer-content title="编辑状态选项" closable>
        <n-data-table :columns="statusColumns" :data="statuses" size="small" />
        <n-button v-if="!readOnly" size="small" style="margin-top: 8px" @click="openStatusModal()">添加状态</n-button>
      </n-drawer-content>
    </n-drawer>

    <n-modal
      v-model:show="showStatusModal"
      preset="dialog"
      :title="editingStatus ? '编辑状态' : '添加状态'"
      positive-text="保存"
      @positive-click="onSaveStatus"
    >
      <n-form label-width="100">
        <n-form-item label="状态标识">
          <n-input
            v-model:value="statusForm.key"
            :disabled="!!editingStatus"
            placeholder="英文标识，如 in_progress"
          />
        </n-form-item>
        <n-form-item label="名称">
          <n-input v-model:value="statusForm.label" placeholder="请输入状态名称" />
        </n-form-item>
        <n-form-item label="终态">
          <n-switch v-model:value="statusForm.is_terminal" />
        </n-form-item>
      </n-form>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, h, ref } from 'vue';
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
  NSwitch,
  NText,
  useDialog,
  useMessage,
  type DataTableColumns,
} from 'naive-ui';
import {
  createBugStatus,
  deleteBugStatus,
  updateBugStatus,
  updateTemplate,
} from '@/api/templates';
import TemplateEditPreview from '@/components/TemplateEditPreview.vue';
import TemplateFieldPanel from '@/components/TemplateFieldPanel.vue';
import type { SystemOptionCategory } from '@/constants/systemFields';
import { invalidateProjectFieldSchemaCache } from '@/composables/useProjectFieldSchema';
import { normalizeFieldSort } from '@/constants/fieldTypes';
import { validateTemplateFieldNames } from '@/schemas/entityFieldSchema';
import { apiErrorMessage } from '@/utils/apiError';
import type { BugStatusDef, TemplateField } from '@/types/business';

const props = defineProps<{
  projectId: string | null;
  bugFields: TemplateField[];
  statuses: BugStatusDef[];
  saving?: boolean;
  readOnly?: boolean;
}>();

const emit = defineEmits<{
  'update:bugFields': [TemplateField[]];
  'add-field': [];
  'edit-field': [index: number];
  refresh: [];
}>();

const message = useMessage();
const dialog = useDialog();
const showStatusDrawer = ref(false);
const showStatusModal = ref(false);
const editingStatus = ref<BugStatusDef | null>(null);
const statusForm = ref({
  key: '',
  label: '',
  is_terminal: false,
});

const bugFields = computed({
  get: () => props.bugFields,
  set: (v) => emit('update:bugFields', v),
});

const optionCounts = computed(() => ({
  bug_status: props.statuses.length,
}));

const statusColumns = computed<DataTableColumns<BugStatusDef>>(() => {
  const cols: DataTableColumns<BugStatusDef> = [
  { title: '标识', key: 'key', width: 120 },
  { title: '名称', key: 'label' },
  {
    title: '终态',
    key: 'is_terminal',
    width: 70,
    render: (r) => (r.is_terminal ? '是' : '否'),
  },
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
          { size: 'tiny', quaternary: true, disabled: index === 0, onClick: () => moveStatus(index, -1) },
          () => '上移'
        ),
        h(
          NButton,
          {
            size: 'tiny',
            quaternary: true,
            disabled: index === props.statuses.length - 1,
            onClick: () => moveStatus(index, 1),
          },
          () => '下移'
        ),
        h(NButton, { size: 'tiny', quaternary: true, type: 'primary', onClick: () => openStatusModal(row) }, () => '编辑'),
        h(NButton, { size: 'tiny', quaternary: true, type: 'error', onClick: () => removeStatus(row) }, () => '删除'),
      ]),
  });
  return cols;
});

function openStatusDrawer(category: SystemOptionCategory) {
  if (props.readOnly || category !== 'bug_status') return;
  showStatusDrawer.value = true;
}

function openStatusModal(row?: BugStatusDef) {
  editingStatus.value = row ?? null;
  statusForm.value = row
    ? {
        key: row.key,
        label: row.label,
        is_terminal: row.is_terminal,
      }
    : {
        key: '',
        label: '',
        is_terminal: false,
      };
  showStatusModal.value = true;
}

async function moveStatus(index: number, delta: number) {
  if (!props.projectId) return;
  const j = index + delta;
  if (j < 0 || j >= props.statuses.length) return;
  const list = [...props.statuses];
  [list[index], list[j]] = [list[j], list[index]];
  try {
    await Promise.all(list.map((s, i) => updateBugStatus(props.projectId!, s.id, { sort: i })));
    message.success('已更新排序');
    emit('refresh');
  } catch {
    message.error('排序失败');
  }
}

function removeStatus(row: BugStatusDef) {
  if (!props.projectId) return;
  dialog.warning({
    title: '确认删除',
    content: `删除状态「${row.label}」？已有缺陷若使用该状态需手动调整。`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await deleteBugStatus(props.projectId!, row.id);
        message.success('已删除');
        emit('refresh');
      } catch {
        message.error('删除失败');
      }
    },
  });
}

async function onSaveStatus() {
  if (!props.projectId) return false;
  if (!statusForm.value.key.trim() || !statusForm.value.label.trim()) {
    message.warning('请填写状态标识和名称');
    return false;
  }
  try {
    if (editingStatus.value) {
      await updateBugStatus(props.projectId, editingStatus.value.id, {
        label: statusForm.value.label,
        is_terminal: statusForm.value.is_terminal,
      });
    } else {
      await createBugStatus(props.projectId, {
        ...statusForm.value,
        sort: props.statuses.length,
      });
    }
    showStatusModal.value = false;
    message.success('已保存');
    emit('refresh');
    return true;
  } catch {
    message.error('保存失败');
    return false;
  }
}

async function saveTemplate() {
  if (!props.projectId) return;
  const nameErr = validateTemplateFieldNames('bug', bugFields.value);
  if (nameErr) {
    message.warning(nameErr);
    return;
  }
  try {
    await updateTemplate(props.projectId, 'bug', normalizeFieldSort(bugFields.value));
    invalidateProjectFieldSchemaCache(props.projectId, 'bug');
    message.success('已保存');
    emit('refresh');
  } catch (e) {
    message.error(apiErrorMessage(e, '保存失败'));
  }
}
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
