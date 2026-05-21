<template>
  <n-modal
    v-model:show="visible"
    preset="card"
    title="导入用例"
    style="width: 520px"
    @update:show="(v) => emit('update:show', v)"
  >
    <n-alert type="info" :bordered="false" style="margin-bottom: 12px">
      在 Excel「模块」列填写完整路径（如「父模块-子模块」，也支持 / 分隔），不存在时将自动创建；留空则归入「未分类」。「关联需求」列填写需求标题或编号（如
      1），多个用逗号分隔。下载的模板仅含表头，从第 2 行起填写数据。
    </n-alert>
    <n-space vertical :size="12">
      <n-button block @click="onDownloadTemplate" :loading="downloading">下载导入模板 (.xlsx)</n-button>
      <n-upload
        :max="1"
        accept=".xlsx"
        :disabled="importing"
        :custom-request="onUpload"
        @remove="clearFile"
      >
        <n-button block :disabled="importing">选择 Excel 文件</n-button>
      </n-upload>
    </n-space>

    <template v-if="result">
      <n-divider />
      <n-text>成功导入 {{ result.created }} 条</n-text>
      <n-alert
        v-if="result.errors.length"
        type="warning"
        :bordered="false"
        style="margin-top: 8px"
        title="以下行未导入"
      >
        <ul class="error-list">
          <li v-for="(e, i) in result.errors" :key="i">第 {{ e.row }} 行：{{ e.message }}</li>
        </ul>
      </n-alert>
    </template>

    <template #footer>
      <n-button @click="visible = false">关闭</n-button>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import {
  NAlert,
  NButton,
  NDivider,
  NModal,
  NSpace,
  NText,
  NUpload,
  useMessage,
  type UploadCustomRequestOptions,
} from 'naive-ui';
import {
  downloadCaseImportTemplate,
  importCases,
  type CaseImportResult,
} from '@/api/cases';

const props = defineProps<{
  show: boolean;
}>();

const emit = defineEmits<{
  'update:show': [value: boolean];
  imported: [];
}>();

const message = useMessage();
const visible = ref(props.show);
const downloading = ref(false);
const importing = ref(false);
const result = ref<CaseImportResult | null>(null);

watch(
  () => props.show,
  (v) => {
    visible.value = v;
    if (v) result.value = null;
  }
);

watch(visible, (v) => emit('update:show', v));

function clearFile() {
  result.value = null;
}

async function onDownloadTemplate() {
  downloading.value = true;
  try {
    await downloadCaseImportTemplate();
    message.success('模板已下载');
  } catch {
    message.error('下载模板失败');
  } finally {
    downloading.value = false;
  }
}

async function onUpload({ file, onFinish, onError }: UploadCustomRequestOptions) {
  if (!file.file) {
    onError();
    return;
  }
  importing.value = true;
  result.value = null;
  try {
    const { data } = await importCases(file.file as File);
    result.value = data;
    if (data.created > 0) {
      message.success(`已导入 ${data.created} 条用例`);
      emit('imported');
    } else if (!data.errors.length) {
      message.warning('文件中没有可导入的数据行');
    } else {
      message.warning('导入完成，但无成功记录');
    }
    onFinish();
  } catch (e: unknown) {
    const detail =
      e && typeof e === 'object' && 'response' in e
        ? (e as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : undefined;
    message.error(typeof detail === 'string' ? detail : '导入失败');
    onError();
  } finally {
    importing.value = false;
  }
}
</script>

<style scoped>
.error-list {
  margin: 8px 0 0;
  padding-left: 1.2em;
  max-height: 200px;
  overflow: auto;
  font-size: 13px;
}
</style>
