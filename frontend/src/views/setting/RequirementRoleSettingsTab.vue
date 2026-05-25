<template>
  <div v-if="!projectId" class="settings-empty">
    <n-text depth="3">请选择项目</n-text>
  </div>
  <div v-else>
    <n-alert type="info" :bordered="false" style="margin-bottom: 12px">
      工作流节点「关联角色」、需求「编辑需求」中的人员选项均来自此列表。
    </n-alert>
    <n-data-table :columns="columns" :data="roles" :loading="loading" size="small" />
    <n-button size="small" style="margin-top: 8px" @click="openModal()">添加角色</n-button>

    <n-modal
      v-model:show="showModal"
      preset="dialog"
      :title="editing ? '编辑角色' : '添加角色'"
      positive-text="保存"
      @positive-click="onSave"
    >
      <n-form label-width="100">
        <n-form-item label="角色标识">
          <n-input
            v-model:value="form.role_key"
            :disabled="!!editing"
            placeholder="小写字母开头，如 qa_lead"
          />
        </n-form-item>
        <n-form-item label="显示名">
          <n-input v-model:value="form.label" placeholder="如 测试负责人" />
        </n-form-item>
      </n-form>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, h, onMounted, ref, watch } from 'vue';
import {
  NAlert,
  NButton,
  NDataTable,
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
  createRequirementRole,
  deleteRequirementRole,
  updateRequirementRole,
  type RequirementRoleDef,
} from '@/api/templates';
import { invalidateRequirementProjectConfig } from '@/composables/useRequirementProjectConfig';
import { loadRequirementRoles } from '@/composables/useRequirementProjectConfig';
import { apiErrorMessage } from '@/utils/apiError';

const props = defineProps<{ projectId: string | null }>();

const message = useMessage();
const dialog = useDialog();
const loading = ref(false);
const roles = ref<RequirementRoleDef[]>([]);
const showModal = ref(false);
const editing = ref<RequirementRoleDef | null>(null);
const form = ref({ role_key: '', label: '' });

const columns = computed<DataTableColumns<RequirementRoleDef>>(() => [
  { title: '标识', key: 'role_key', width: 140 },
  { title: '显示名', key: 'label' },
  {
    title: '操作',
    key: 'actions',
    width: 200,
    render: (row, index) =>
      h(NSpace, { size: 4 }, () => [
        h(
          NButton,
          { size: 'tiny', quaternary: true, disabled: index === 0, onClick: () => moveRole(index, -1) },
          () => '上移'
        ),
        h(
          NButton,
          {
            size: 'tiny',
            quaternary: true,
            disabled: index === roles.value.length - 1,
            onClick: () => moveRole(index, 1),
          },
          () => '下移'
        ),
        h(NButton, { size: 'tiny', quaternary: true, type: 'primary', onClick: () => openModal(row) }, () => '编辑'),
        h(NButton, { size: 'tiny', quaternary: true, type: 'error', onClick: () => removeRole(row) }, () => '删除'),
      ]),
  },
]);

async function load() {
  if (!props.projectId) {
    roles.value = [];
    return;
  }
  loading.value = true;
  try {
    roles.value = await loadRequirementRoles(props.projectId, true);
  } catch {
    message.error('加载角色失败');
  } finally {
    loading.value = false;
  }
}

function openModal(row?: RequirementRoleDef) {
  editing.value = row ?? null;
  form.value = row
    ? { role_key: row.role_key, label: row.label }
    : { role_key: '', label: '' };
  showModal.value = true;
}

async function moveRole(index: number, delta: number) {
  if (!props.projectId) return;
  const j = index + delta;
  if (j < 0 || j >= roles.value.length) return;
  const list = [...roles.value];
  [list[index], list[j]] = [list[j], list[index]];
  try {
    await Promise.all(list.map((r, i) => updateRequirementRole(props.projectId!, r.id, { sort: i })));
    invalidateRequirementProjectConfig(props.projectId);
    await load();
  } catch {
    message.error('排序失败');
  }
}

function removeRole(row: RequirementRoleDef) {
  if (!props.projectId) return;
  dialog.warning({
    title: '确认删除',
    content: `删除角色「${row.label}」？若被工作流或需求引用将无法删除。`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      const projectId = props.projectId;
      if (!projectId) return;
      try {
        await deleteRequirementRole(projectId, row.id);
        invalidateRequirementProjectConfig(projectId);
        message.success('已删除');
        await load();
      } catch (e) {
        message.error(apiErrorMessage(e, '删除失败'));
      }
    },
  });
}

async function onSave() {
  if (!props.projectId) return false;
  const roleKey = form.value.role_key.trim();
  const label = form.value.label.trim();
  if (!roleKey || !label) {
    message.warning('请填写角色标识和显示名');
    return false;
  }
  try {
    if (editing.value) {
      await updateRequirementRole(props.projectId, editing.value.id, { label });
    } else {
      await createRequirementRole(props.projectId, {
        role_key: roleKey,
        label,
        sort: roles.value.length,
      });
    }
    invalidateRequirementProjectConfig(props.projectId);
    showModal.value = false;
    message.success('已保存');
    await load();
    return true;
  } catch (e) {
    message.error(apiErrorMessage(e, '保存失败'));
    return false;
  }
}

onMounted(load);
watch(() => props.projectId, load);
</script>

<style scoped>
.settings-empty {
  padding: 24px;
}
</style>
