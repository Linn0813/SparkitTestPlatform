<template>
  <n-space vertical size="large">
    <!-- Tab 切换 -->
    <n-tabs v-model:value="activeTab" type="line" animated>
      <!-- ── 用例管理 ── -->
      <n-tab-pane name="cases" tab="用例管理">
        <div style="display: flex; justify-content: flex-end; gap: 8px; margin: 8px 0">
          <n-select
            v-model:value="casePlatformFilter"
            :options="platformOptions"
            placeholder="全部平台"
            clearable
            style="width: 120px"
            @update:value="loadCases"
          />
          <n-button type="primary" @click="showCaseModal = true">新建用例</n-button>
        </div>
        <n-data-table
          :columns="caseColumns"
          :data="cases"
          :loading="casesLoading"
          :row-key="(r: UITestCaseListItem) => r.id"
          :row-props="caseRowProps"
        />
      </n-tab-pane>

      <!-- ── App 包管理 ── -->
      <n-tab-pane name="apps" tab="App 包">
        <div style="display: flex; justify-content: flex-end; margin: 8px 0">
          <n-button type="primary" @click="showAppModal = true">上传 App</n-button>
        </div>
        <n-data-table
          :columns="appColumns"
          :data="apps"
          :loading="appsLoading"
          :row-key="(r: MobileApp) => r.id"
        />
      </n-tab-pane>

      <!-- ── Runner 管理 ── -->
      <n-tab-pane name="runners" tab="Runner">
        <div style="display: flex; justify-content: flex-end; margin: 8px 0">
          <n-button type="primary" @click="showRunnerModal = true">注册 Runner</n-button>
        </div>
        <n-data-table
          :columns="runnerColumns"
          :data="runners"
          :loading="runnersLoading"
          :row-key="(r: UIRunner) => r.id"
        />
      </n-tab-pane>

      <!-- ── 元素库 ── -->
      <n-tab-pane name="elements" tab="元素库">
        <div style="display: flex; justify-content: flex-end; gap: 8px; margin: 8px 0">
          <n-select
            v-model:value="elementPlatformFilter"
            :options="platformOptions"
            placeholder="全部平台"
            clearable
            style="width: 120px"
            @update:value="loadElements"
          />
          <n-button type="primary" @click="showElementModal = true">添加元素</n-button>
        </div>
        <n-data-table
          :columns="elementColumns"
          :data="elements"
          :loading="elementsLoading"
          :row-key="(r: UIElement) => r.id"
        />
      </n-tab-pane>

      <!-- ── 执行记录 ── -->
      <n-tab-pane name="runs" tab="执行记录">
        <div style="display: flex; gap: 8px; margin: 8px 0">
          <n-select
            v-model:value="runStatusFilter"
            :options="runStatusOptions"
            placeholder="全部状态"
            clearable
            style="width: 130px"
            @update:value="loadAllRuns"
          />
        </div>
        <n-data-table
          :columns="allRunColumns"
          :data="allRuns"
          :loading="allRunsLoading"
          :row-key="(r: UITestRunListItem) => r.id"
          :row-props="runRowProps"
        />
      </n-tab-pane>
    </n-tabs>

    <!-- ── 添加元素 Modal ── -->
    <n-modal
      v-model:show="showElementModal"
      preset="dialog"
      :title="editingElementId ? '编辑元素' : '添加元素'"
      positive-text="保存"
      negative-text="取消"
      style="width: 560px"
      @positive-click="onSaveElement"
      @after-leave="editingElementId = null"
    >
      <n-form label-placement="top" style="margin-top: 8px">
        <n-form-item label="元素名称">
          <n-input v-model:value="elementForm.name" placeholder="例：登录按钮、邮箱输入框" />
        </n-form-item>
        <n-form-item label="平台">
          <n-select v-model:value="elementForm.platform" :options="platformOptions" style="width: 100%" :disabled="!!editingElementId" />
        </n-form-item>
        <n-form-item label="Selector">
          <n-input
            v-model:value="elementForm.selector"
            placeholder="例：~Next 或 android=new UiSelector().className(...)"
            style="font-family: monospace; font-size: 12px"
          />
        </n-form-item>
        <n-form-item label="备注（可粘贴截图）">
          <PasteImageTextarea
            v-model="elementForm.description"
            :project-id="ctx.projectId"
            placeholder="说明元素位置，支持 Ctrl+V 粘贴截图"
            :rows="3"
          />
        </n-form-item>
      </n-form>
    </n-modal>
    <n-modal
      v-model:show="showCaseModal"
      preset="card"
      title="新建 UI 用例"
      style="width: 720px"
      :segmented="{ content: true }"
    >
      <n-form label-placement="top">
        <n-grid :cols="2" :x-gap="16">
          <n-gi>
            <n-form-item label="用例名称">
              <n-input v-model:value="caseForm.name" placeholder="例：邮箱登录流程" />
            </n-form-item>
          </n-gi>
          <n-gi>
            <n-form-item label="平台">
              <n-select v-model:value="caseForm.platform" :options="platformOptions" style="width: 100%" />
            </n-form-item>
          </n-gi>
        </n-grid>

        <!-- Selectors -->
        <n-form-item>
          <template #label>
            <n-space align="center" size="small">
              使用元素库中的元素
              <n-text depth="3" style="font-size: 12px">从元素库选择，或在步骤中直接选</n-text>
            </n-space>
          </template>
          <n-select
            v-model:value="caseForm.selectedElementIds"
            multiple
            :options="elementOptionsForPlatform"
            placeholder="选择要用到的元素（可多选）"
            style="width: 100%"
          />
        </n-form-item>

        <!-- Steps -->
        <n-form-item label="执行步骤">
          <div style="width: 100%">
            <div v-for="(step, i) in caseForm.steps" :key="i" style="display: flex; gap: 8px; margin-bottom: 8px; align-items: center">
              <n-text depth="3" style="width: 24px; text-align: center; flex-shrink: 0">{{ i + 1 }}</n-text>
              <n-select v-model:value="step.action" :options="actionOptions" style="width: 130px; flex-shrink: 0" @update:value="onStepActionChange(step)" />
              <n-select
                v-if="step.action !== 'wait'"
                v-model:value="step.selector_key"
                :options="selectedElementOptions"
                placeholder="选择元素"
                clearable
                style="width: 160px; flex-shrink: 0"
              />
              <n-select
                v-if="step.action === 'swipe'"
                v-model:value="step.value"
                :options="swipeOptions"
                placeholder="方向"
                style="width: 100px; flex-shrink: 0"
              />
              <n-input
                v-else-if="step.action === 'type'"
                v-model:value="step.value"
                placeholder="输入内容"
                style="flex: 1"
              />
              <n-input-number
                v-else-if="step.action === 'wait'"
                v-model:value="step.waitMs"
                placeholder="毫秒"
                :min="100"
                :step="500"
                style="flex: 1"
              >
                <template #suffix>ms</template>
              </n-input-number>
              <div v-else style="flex: 1" />
              <n-button quaternary type="error" style="flex-shrink: 0" @click="caseForm.steps.splice(i, 1)">×</n-button>
            </div>
            <n-button dashed size="small" @click="addStep">+ 添加步骤</n-button>
          </div>
        </n-form-item>

        <!-- Assertion -->
        <n-form-item label="成功条件（执行完后验证哪个元素可见）">
          <n-select
            v-model:value="caseForm.assertionSelectorKey"
            :options="selectedElementOptions"
            placeholder="选择元素（不填则不验证）"
            clearable
            style="width: 100%"
          />
        </n-form-item>
      </n-form>

      <template #action>
        <n-space justify="end">
          <n-button @click="showCaseModal = false">取消</n-button>
          <n-button type="primary" @click="onCreateCase">创建</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- ── 上传 App Modal ── -->
    <n-modal
      v-model:show="showAppModal"
      preset="dialog"
      title="上传 App 包"
      positive-text="上传"
      negative-text="取消"
      @positive-click="onUploadApp"
    >
      <n-form label-placement="top" style="margin-top: 8px">
        <n-form-item label="平台">
          <n-select v-model:value="appForm.platform" :options="platformOptions" style="width: 100%" />
        </n-form-item>
        <n-form-item label="版本号">
          <n-input v-model:value="appForm.version" placeholder="例：1.5.0-dev-418" />
        </n-form-item>
        <n-form-item label="文件">
          <n-upload :max="1" :default-upload="false" @change="onAppFileChange">
            <n-button>选择 APK / IPA</n-button>
          </n-upload>
        </n-form-item>
      </n-form>
    </n-modal>

    <!-- ── 注册 Runner Modal ── -->
    <n-modal
      v-model:show="showRunnerModal"
      preset="dialog"
      title="注册 Runner"
      positive-text="注册"
      negative-text="取消"
      @positive-click="onCreateRunner"
    >
      <n-form label-placement="top" style="margin-top: 8px">
        <n-form-item label="名称">
          <n-input v-model:value="runnerForm.name" placeholder="例：我的 Mac" />
        </n-form-item>
        <n-form-item label="平台">
          <n-select v-model:value="runnerForm.platform" :options="platformOptions" style="width: 100%" />
        </n-form-item>
      </n-form>
    </n-modal>

    <!-- ── Token 展示 Modal（注册后一次性） ── -->
    <n-modal v-model:show="showTokenModal" preset="dialog" title="Runner Token" :show-close="false">
      <n-alert type="warning" style="margin-bottom: 12px">
        Token 只显示一次，请立即复制并填入 runner/.env 的 RUNNER_TOKEN。
      </n-alert>
      <n-input :value="newToken" readonly style="font-family: monospace" />
      <template #action>
        <n-button type="primary" @click="copyToken">复制</n-button>
        <n-button style="margin-left: 8px" @click="showTokenModal = false">关闭</n-button>
      </template>
    </n-modal>

    <!-- ── 触发执行 Modal ── -->
    <n-modal
      v-model:show="showRunModal"
      preset="dialog"
      title="执行用例"
      positive-text="执行"
      negative-text="取消"
      @positive-click="onTriggerRun"
    >
      <n-form label-placement="top" style="margin-top: 8px">
        <n-form-item label="选择 App 包">
          <n-select
            v-model:value="runForm.app_id"
            :options="appOptionsForRun"
            placeholder="选择要安装的 App"
            style="width: 100%"
          />
        </n-form-item>
      </n-form>
    </n-modal>
  </n-space>
</template>

<script setup lang="ts">
import { computed, h, onMounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import {
  NAlert,
  NButton,
  NDataTable,
  NForm,
  NFormItem,
  NGi,
  NGrid,
  NInput,
  NInputNumber,
  NModal,
  NSelect,
  NSpace,
  NTag,
  NTabs,
  NTabPane,
  NText,
  NUpload,
  useDialog,
  useMessage,
  type DataTableColumns,
  type UploadFileInfo,
} from 'naive-ui';
import PasteImageTextarea from '@/components/PasteImageTextarea.vue';
import InlineMarkdownContent from '@/components/InlineMarkdownContent.vue';
import {
  createElement,
  createRunner,
  createUICase,
  deleteElement,
  deleteRunner,
  deleteMobileApp,
  deleteUICase,
  listElements,
  listMobileApps,
  listRunners,
  listRuns,
  listUICases,
  triggerRun,
  updateElement,
  uploadMobileApp,
} from '@/api/uiAutomation';
import { useContextStore } from '@/stores/context';
import type { MobileApp, UIElement, UIRunner, UITestCase, UITestCaseListItem, UITestRunListItem } from '@/types/business';

const ctx = useContextStore();
const message = useMessage();
const dialog = useDialog();
const router = useRouter();

const activeTab = ref('cases');

const platformOptions = [
  { label: 'Android', value: 'android' },
  { label: 'iOS', value: 'ios' },
];

function platformTag(platform: string) {
  return h(NTag, { size: 'small', type: platform === 'android' ? 'success' : 'info' }, () =>
    platform === 'android' ? 'Android' : 'iOS'
  );
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  });
}

function formatSize(bytes: number) {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

const actionOptions = [
  { label: '点击', value: 'tap' },
  { label: '输入文字', value: 'type' },
  { label: '滑动', value: 'swipe' },
  { label: '等待', value: 'wait' },
  { label: '验证可见', value: 'assert_visible' },
];

const swipeOptions = [
  { label: '向上', value: 'up' },
  { label: '向下', value: 'down' },
  { label: '向左', value: 'left' },
  { label: '向右', value: 'right' },
];

type StepForm = { action: string; selector_key: string; value: string; waitMs: number };

function emptyStep(): StepForm {
  return { action: 'tap', selector_key: '', value: '', waitMs: 1000 };
}

// ── 用例 ──
const cases = ref<UITestCaseListItem[]>([]);
const casesLoading = ref(false);
const casePlatformFilter = ref<string | null>(null);
const showCaseModal = ref(false);
const showRunModal = ref(false);
const pendingCaseId = ref('');

const caseForm = ref({
  name: '',
  platform: 'android',
  selectedElementIds: [] as string[],
  steps: [] as StepForm[],
  assertionSelectorKey: '',
});
const runForm = ref({ app_id: '' });

// 执行记录 Tab
const allRuns = ref<UITestRunListItem[]>([]);
const allRunsLoading = ref(false);
const runStatusFilter = ref<string | null>(null);

const runStatusOptions = [
  { label: '等待中', value: 'pending' },
  { label: '执行中', value: 'running' },
  { label: '通过', value: 'passed' },
  { label: '失败', value: 'failed' },
  { label: '异常', value: 'error' },
];

function runStatusLabel(s: string) {
  return { pending: '等待中', running: '执行中', passed: '通过', failed: '失败', error: '异常' }[s] ?? s;
}
function runStatusType(s: string): 'default' | 'info' | 'success' | 'error' | 'warning' {
  return ({ pending: 'default', running: 'info', passed: 'success', failed: 'error', error: 'warning' }[s] ?? 'default') as 'default' | 'info' | 'success' | 'error' | 'warning';
}

// 用例名映射
const caseNameMap = computed(() => {
  const map: Record<string, string> = {};
  cases.value.forEach((c) => { map[c.id] = c.name; });
  return map;
});

const allRunColumns: DataTableColumns<UITestRunListItem> = [
  {
    title: '状态', key: 'status', width: 100,
    render: (r) => h(NTag, { size: 'small', type: runStatusType(r.status) }, () => runStatusLabel(r.status)),
  },
  {
    title: '用例', key: 'case_id', ellipsis: { tooltip: true },
    render: (r) => caseNameMap.value[r.case_id] ?? r.case_id,
  },
  { title: '开始时间', key: 'started_at', width: 160, render: (r) => r.started_at ? formatDate(r.started_at) : '—' },
  { title: '结束时间', key: 'finished_at', width: 160, render: (r) => r.finished_at ? formatDate(r.finished_at) : '—' },
  {
    title: '操作', key: 'actions', width: 80,
    render: (r) => h(NButton, { size: 'small', onClick: () => router.push({ name: 'ui-run-detail', params: { id: r.id } }) }, () => '详情'),
  },
];

function runRowProps(row: UITestRunListItem) {
  return {
    style: 'cursor: pointer',
    onClick: () => router.push({ name: 'ui-run-detail', params: { id: row.id } }),
  };
}

async function loadAllRuns() {
  if (!ctx.projectId) return;
  allRunsLoading.value = true;
  try {
    const { data } = await listRuns();
    allRuns.value = runStatusFilter.value
      ? data.filter((r) => r.status === runStatusFilter.value)
      : data;
  } finally {
    allRunsLoading.value = false;
  }
}

// 当前平台的元素库选项（用于新建用例的多选）
const elementOptionsForPlatform = computed(() =>
  elements.value
    .filter((e) => e.platform === caseForm.value.platform)
    .map((e) => ({ label: `${e.name}`, value: e.id }))
);

// 已选元素的选项（用于步骤里选择元素）
const selectedElementOptions = computed(() =>
  elements.value
    .filter((e) => caseForm.value.selectedElementIds.includes(e.id))
    .map((e) => ({ label: e.name, value: e.name }))
);

function addStep() {
  caseForm.value.steps.push(emptyStep());
}

function onStepActionChange(step: StepForm) {
  step.selector_key = '';
  step.value = '';
  step.waitMs = 1000;
}

const caseColumns: DataTableColumns<UITestCaseListItem> = [
  { title: '用例名称', key: 'name', ellipsis: { tooltip: true } },
  { title: '平台', key: 'platform', width: 90, render: (r) => platformTag(r.platform) },
  {
    title: '状态', key: 'status', width: 80,
    render: (r) => h(NTag, { size: 'small', bordered: false, type: r.status === 'active' ? 'success' : 'default' }, () => r.status === 'active' ? '启用' : '草稿'),
  },
  { title: '更新时间', key: 'updated_at', width: 150, render: (r) => formatDate(r.updated_at) },
  {
    title: '操作', key: 'actions', width: 140,
    render: (r) => h(NSpace, {}, () => [
      h(NButton, { size: 'small', type: 'primary', onClick: (e: MouseEvent) => { e.stopPropagation(); openRunModal(r.id); } }, () => '执行'),
      h(NButton, { size: 'small', quaternary: true, type: 'error', onClick: (e: MouseEvent) => { e.stopPropagation(); onDeleteCase(r); } }, () => '删除'),
    ]),
  },
];

function caseRowProps(_row: UITestCaseListItem) {
  return {};
}

async function loadCases() {
  if (!ctx.projectId) return;
  casesLoading.value = true;
  try {
    const { data } = await listUICases(casePlatformFilter.value ? { platform: casePlatformFilter.value } : undefined);
    cases.value = data;
  } finally {
    casesLoading.value = false;
  }
}

async function onCreateCase() {
  if (!caseForm.value.name.trim()) { message.warning('请填写用例名称'); return false; }

  // 从元素库构建 selectors map：{ 元素名: selector }
  const selectors: Record<string, string> = {};
  for (const id of caseForm.value.selectedElementIds) {
    const el = elements.value.find((e) => e.id === id);
    if (el) selectors[el.name] = el.selector;
  }

  const steps = caseForm.value.steps.map((s) => {
    const step: Record<string, unknown> = { action: s.action };
    if (s.action !== 'wait' && s.selector_key) step.selector_key = s.selector_key;
    if (s.action === 'type') step.value = s.value;
    if (s.action === 'swipe') step.value = s.value;
    if (s.action === 'wait') step.value = String(s.waitMs ?? 1000);
    return step;
  });

  const assertion: Record<string, string> = {};
  if (caseForm.value.assertionSelectorKey) {
    assertion.type = 'element_visible';
    assertion.selector_key = caseForm.value.assertionSelectorKey;
  }

  await createUICase({
    name: caseForm.value.name.trim(),
    platform: caseForm.value.platform as 'android' | 'ios',
    selectors,
    steps: steps as unknown as UITestCase['steps'],
    assertion,
  });
  message.success('已创建');
  showCaseModal.value = false;
  caseForm.value = { name: '', platform: 'android', selectedElementIds: [], steps: [], assertionSelectorKey: '' };
  await loadCases();
  return true;
}

function onDeleteCase(row: UITestCaseListItem) {
  dialog.warning({
    title: '删除用例',
    content: `确定删除「${row.name}」？`,
    positiveText: '删除', negativeText: '取消',
    onPositiveClick: async () => {
      await deleteUICase(row.id);
      message.success('已删除');
      await loadCases();
    },
  });
}

function openRunModal(caseId: string) {
  pendingCaseId.value = caseId;
  runForm.value.app_id = '';
  showRunModal.value = true;
}

const appOptionsForRun = computed(() =>
  apps.value.map((a) => ({ label: `${a.filename} (${a.version})`, value: a.id }))
);

async function onTriggerRun() {
  if (!runForm.value.app_id) { message.warning('请选择 App 包'); return false; }
  const { data } = await triggerRun({ case_id: pendingCaseId.value, app_id: runForm.value.app_id });
  message.success('已提交执行，Runner 将自动领取');
  showRunModal.value = false;
  router.push({ name: 'ui-run-detail', params: { id: data.id } });
  return true;
}

// ── App 包 ──
const apps = ref<MobileApp[]>([]);
const appsLoading = ref(false);
const showAppModal = ref(false);
const appFile = ref<File | null>(null);
const appForm = ref({ platform: 'android', version: '' });

const appColumns: DataTableColumns<MobileApp> = [
  { title: '文件名', key: 'filename', ellipsis: { tooltip: true } },
  { title: '平台', key: 'platform', width: 90, render: (r) => platformTag(r.platform) },
  { title: '版本', key: 'version', width: 160 },
  { title: '大小', key: 'size', width: 100, render: (r) => formatSize(r.size) },
  { title: '上传时间', key: 'uploaded_at', width: 150, render: (r) => formatDate(r.uploaded_at) },
  {
    title: '操作', key: 'actions', width: 80,
    render: (r) => h(NButton, { size: 'small', quaternary: true, type: 'error', onClick: () => onDeleteApp(r) }, () => '删除'),
  },
];

function onAppFileChange({ fileList }: { fileList: UploadFileInfo[] }) {
  appFile.value = fileList[0]?.file ?? null;
}

async function onUploadApp() {
  if (!appFile.value) { message.warning('请选择文件'); return false; }
  if (!appForm.value.version.trim()) { message.warning('请填写版本号'); return false; }
  try {
    await uploadMobileApp(appForm.value.platform, appForm.value.version.trim(), appFile.value);
    message.success('上传成功');
    showAppModal.value = false;
    appFile.value = null;
    appForm.value = { platform: 'android', version: '' };
    await loadApps();
  } catch {
    message.error('上传失败，请重试');
  }
  return true;
}

function onDeleteApp(row: MobileApp) {
  dialog.warning({
    title: '删除 App 包',
    content: `确定删除「${row.filename}」？`,
    positiveText: '删除', negativeText: '取消',
    onPositiveClick: async () => {
      await deleteMobileApp(row.id);
      message.success('已删除');
      await loadApps();
    },
  });
}

async function loadApps() {
  if (!ctx.projectId) return;
  appsLoading.value = true;
  try {
    const { data } = await listMobileApps();
    apps.value = data;
  } finally {
    appsLoading.value = false;
  }
}

// ── Runner ──
const runners = ref<UIRunner[]>([]);
const runnersLoading = ref(false);
const showRunnerModal = ref(false);
const showTokenModal = ref(false);
const newToken = ref('');
const runnerForm = ref({ name: '', platform: 'android' });

function isOnline(r: UIRunner) {
  if (!r.last_heartbeat_at) return false;
  const ts = r.last_heartbeat_at.endsWith('Z') ? r.last_heartbeat_at : r.last_heartbeat_at + 'Z';
  return Date.now() - new Date(ts).getTime() < 60_000;
}

const runnerColumns: DataTableColumns<UIRunner> = [
  { title: '名称', key: 'name' },
  { title: '平台', key: 'platform', width: 90, render: (r) => platformTag(r.platform) },
  {
    title: '状态', key: 'online', width: 80,
    render: (r) => h(NTag, { size: 'small', type: isOnline(r) ? 'success' : 'default' }, () => isOnline(r) ? '在线' : '离线'),
  },
  {
    title: '最后心跳', key: 'last_heartbeat_at', width: 150,
    render: (r) => r.last_heartbeat_at ? formatDate(r.last_heartbeat_at) : '—',
  },
  {
    title: '操作', key: 'actions', width: 80,
    render: (r) => h(NButton, { size: 'small', quaternary: true, type: 'error', onClick: () => onDeleteRunner(r) }, () => '删除'),
  },
];

async function onCreateRunner() {
  if (!runnerForm.value.name.trim()) { message.warning('请填写名称'); return false; }
  const { data } = await createRunner({ name: runnerForm.value.name.trim(), platform: runnerForm.value.platform });
  newToken.value = (data as UIRunner & { token: string }).token;
  showRunnerModal.value = false;
  showTokenModal.value = true;
  runnerForm.value = { name: '', platform: 'android' };
  await loadRunners();
  return true;
}

function onDeleteRunner(row: UIRunner) {
  dialog.warning({
    title: '删除 Runner',
    content: `确定删除 Runner「${row.name}」？`,
    positiveText: '删除', negativeText: '取消',
    onPositiveClick: async () => {
      await deleteRunner(row.id);
      message.success('已删除');
      await loadRunners();
    },
  });
}

async function copyToken() {
  await navigator.clipboard.writeText(newToken.value);
  message.success('已复制');
}

async function loadRunners() {
  if (!ctx.projectId) return;
  runnersLoading.value = true;
  try {
    const { data } = await listRunners();
    runners.value = data;
  } finally {
    runnersLoading.value = false;
  }
}

// ── 元素库 ──
const elements = ref<UIElement[]>([]);
const elementsLoading = ref(false);
const elementPlatformFilter = ref<string | null>(null);
const showElementModal = ref(false);
const editingElementId = ref<string | null>(null);
const elementForm = ref({ name: '', platform: 'android', selector: '', description: '' });

const elementColumns: DataTableColumns<UIElement> = [
  { title: '名称', key: 'name', width: 160, ellipsis: { tooltip: true } },
  { title: '平台', key: 'platform', width: 90, render: (r) => platformTag(r.platform) },
  { title: 'Selector', key: 'selector', ellipsis: { tooltip: true }, render: (r) => h('span', { style: 'font-family: monospace; font-size: 12px' }, r.selector) },
  {
    title: '备注', key: 'description', width: 200,
    render: (r) => r.description
      ? h(InlineMarkdownContent, { text: r.description, projectId: ctx.projectId })
      : h('span', { style: 'color: #ccc' }, '—'),
  },
  {
    title: '操作', key: 'actions', width: 120,
    render: (r) => h(NSpace, {}, () => [
      h(NButton, { size: 'small', quaternary: true, onClick: () => onEditElement(r) }, () => '编辑'),
      h(NButton, { size: 'small', quaternary: true, type: 'error', onClick: () => onDeleteElement(r) }, () => '删除'),
    ]),
  },
];

function onEditElement(row: UIElement) {
  editingElementId.value = row.id;
  elementForm.value = { name: row.name, platform: row.platform, selector: row.selector, description: row.description ?? '' };
  showElementModal.value = true;
}

function onDeleteElement(row: UIElement) {
  dialog.warning({
    title: '删除元素',
    content: `确定删除「${row.name}」？`,
    positiveText: '删除', negativeText: '取消',
    onPositiveClick: async () => {
      await deleteElement(row.id);
      message.success('已删除');
      await loadElements();
    },
  });
}

async function onSaveElement() {
  if (!elementForm.value.name.trim()) { message.warning('请填写元素名称'); return false; }
  if (!elementForm.value.selector.trim()) { message.warning('请填写 Selector'); return false; }

  if (editingElementId.value) {
    await updateElement(editingElementId.value, {
      name: elementForm.value.name.trim(),
      selector: elementForm.value.selector.trim(),
      description: elementForm.value.description.trim() || undefined,
    });
    message.success('已更新');
  } else {
    await createElement({
      name: elementForm.value.name.trim(),
      platform: elementForm.value.platform as 'android' | 'ios',
      selector: elementForm.value.selector.trim(),
      description: elementForm.value.description.trim() || undefined,
    });
    message.success('已添加');
  }

  showElementModal.value = false;
  editingElementId.value = null;
  elementForm.value = { name: '', platform: 'android', selector: '', description: '' };
  await loadElements();
  return true;
}

async function loadElements() {
  if (!ctx.projectId) return;
  elementsLoading.value = true;
  try {
    const { data } = await listElements(elementPlatformFilter.value ? { platform: elementPlatformFilter.value } : undefined);
    elements.value = data;
  } finally {
    elementsLoading.value = false;
  }
}

function loadAll() {
  loadCases();
  loadApps();
  loadRunners();
  loadElements();
  loadAllRuns();
}

onMounted(loadAll);
watch(() => ctx.projectId, loadAll);
</script>
