<template>
  <div v-if="loading && !version" class="panel-loading">
    <n-spin size="medium" />
  </div>
  <div v-else-if="version" class="version-detail-panel">
    <div class="header-block">
      <div class="panel-toolbar">
        <n-space :size="4" align="center">
          <n-button quaternary size="small" :disabled="!hasPrev" @click="emit('prev')">上一条</n-button>
          <n-button quaternary size="small" :disabled="!hasNext" @click="emit('next')">下一条</n-button>
        </n-space>
        <n-space
          :size="4"
          align="center"
          :class="{ 'toolbar-actions--locked': saving || toolbarActionLocked }"
        >
          <template v-if="editMode">
            <n-button quaternary size="small" @click="cancelEdit">取消</n-button>
            <n-button size="small" type="primary" :loading="saving" @click.stop="saveVersion">保存</n-button>
          </template>
          <template v-else-if="canEdit">
            <n-button quaternary size="small" @click="enterEdit">编辑</n-button>
            <n-button
              quaternary
              size="small"
              type="error"
              :disabled="toolbarActionLocked"
              @click="onDelete"
            >
              删除
            </n-button>
          </template>
          <n-button quaternary size="small" @click="emit('close')">关闭</n-button>
        </n-space>
      </div>

      <div v-if="!editMode" class="panel-title-row">
        <n-text strong>{{ version.name }}</n-text>
        <n-tag :type="versionStatusTagType(version.status)" size="small" round :bordered="false">
          {{ versionStatusLabel(version.status) }}
        </n-tag>
        <n-tag size="small" round :bordered="false">
          {{ versionTypeLabel(version.version_type) }}
        </n-tag>
        <n-text depth="3" style="font-size: 13px">
          需求 {{ requirements.length }} · 规划缺陷 {{ bugs.length }}
        </n-text>
      </div>
    </div>

    <div class="panel-body">
      <template v-if="!editMode">
        <div class="workflow-block" @click.self="clearNodeSelection">
          <VersionWorkflowCanvas
            :nodes="canvasNodes"
            :defs="version.workflow_defs"
            :progress="version.nodes"
            :selected-node-key="selectedNodeKey"
            :assignee-label="memberLabel"
            @node-select="onNodeSelect"
          />
        </div>

        <VersionNodeActionPanel
          v-if="selectedNodeKey && version"
          :version-id="version.id"
          :node-key="selectedNodeKey"
          :nodes="version.nodes"
          :defs="version.workflow_defs"
          :can-edit="canEdit"
          :acting="actingKey === selectedNodeKey"
          :member-options="memberSelectOptions"
          :assignee-label="memberLabel"
          @complete="onCompleteSelected"
          @reopen="onReopenSelected"
          @updated="onNodeMetaUpdated"
        />

        <n-tabs v-model:value="activeTab" type="line" animated class="tabs-block">
          <n-tab-pane name="info" tab="版本信息">
            <n-descriptions :column="1" label-placement="left" style="margin-top: 8px">
              <n-descriptions-item label="版本编号">{{ version.num }}</n-descriptions-item>
              <n-descriptions-item label="类型">
                {{ versionTypeLabel(version.version_type) }}
              </n-descriptions-item>
              <n-descriptions-item label="构建号">
                {{ version.build_number || '—' }}
              </n-descriptions-item>
              <n-descriptions-item label="上线时间">
                {{ version.released_at ? formatDateOnly(version.released_at) : '—' }}
              </n-descriptions-item>
            </n-descriptions>
          </n-tab-pane>
          <n-tab-pane name="requirements" tab="需求">
            <n-data-table
              :columns="requirementColumns"
              :data="requirements"
              :loading="loadingReqs"
              :scroll-x="700"
              style="margin-top: 8px"
            />
          </n-tab-pane>
          <n-tab-pane name="bugs" tab="缺陷（规划版本）">
            <n-data-table
              :columns="bugColumns"
              :data="bugs"
              :loading="loadingBugs"
              :scroll-x="600"
              :row-key="(row: BugItem) => row.id"
              :row-props="bugRowProps"
              style="margin-top: 8px"
            />
          </n-tab-pane>
        </n-tabs>
      </template>

      <template v-else>
        <n-form label-placement="top" style="max-width: 480px; margin-top: 8px">
          <n-form-item label="版本名称" required>
            <n-input v-model:value="editForm.name" />
          </n-form-item>
          <n-form-item label="构建号">
            <n-input
              v-model:value="editForm.build_number"
              placeholder="选填，如 1234 或 1.2.0.456"
              :maxlength="64"
            />
          </n-form-item>
          <n-form-item label="上线时间">
            <n-date-picker
              v-model:formatted-value="editForm.released_at"
              value-format="yyyy-MM-dd"
              type="date"
              clearable
              style="width: 100%"
            />
          </n-form-item>
          <n-form-item label="类型">
            <n-select v-model:value="editForm.version_type" :options="versionTypeOptions" />
            <n-text depth="3" style="display: block; font-size: 12px; margin-top: 4px">
              修改类型将重置该版本工作流进度
            </n-text>
          </n-form-item>
        </n-form>
      </template>
    </div>

    <n-drawer
      v-model:show="bugDrawerVisible"
      :width="'50%'"
      placement="right"
      :trap-focus="false"
      @update:show="onBugDrawerShowChange"
    >
      <n-drawer-content :closable="false" body-content-style="padding: 0">
        <BugDetailPanel
          v-if="activeBugId"
          :bug-id="activeBugId"
          :has-prev="activeBugIndex > 0"
          :has-next="activeBugIndex >= 0 && activeBugIndex < bugs.length - 1"
          @prev="goPrevBug"
          @next="goNextBug"
          @close="closeBugDrawer"
          @deleted="onBugDeleted"
          @updated="onBugUpdated"
        />
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, h, onMounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import {
  NButton,
  NDataTable,
  NDatePicker,
  NDescriptions,
  NDescriptionsItem,
  NDrawer,
  NDrawerContent,
  NForm,
  NFormItem,
  NInput,
  NSelect,
  NSpace,
  NSpin,
  NTabPane,
  NTabs,
  NTag,
  NText,
  NTooltip,
  useDialog,
  useMessage,
  type DataTableColumns,
} from 'naive-ui';
import { listBugs } from '@/api/bugs';
import { fetchRequirementOptions } from '@/api/requirements';
import { listBugStatuses } from '@/api/templates';
import { completeVersionNode, deleteVersion, getVersion, reopenVersionNode, updateVersion } from '@/api/versions';
import BugDetailPanel from '@/components/BugDetailPanel.vue';
import VersionWorkflowCanvas from '@/components/VersionWorkflowCanvas.vue';
import VersionNodeActionPanel from '@/components/VersionNodeActionPanel.vue';
import { VERSION_TYPE_OPTIONS, versionTypeLabel } from '@/constants/versionTypes';
import { useProjectMemberOptions } from '@/composables/useProjectMemberOptions';
import { versionStatusLabel, versionStatusTagType } from '@/constants/versionStatus';
import { requirementStatusLabel, requirementStatusTagType } from '@/constants/requirementStatus';
import { usePermissions } from '@/composables/usePermissions';
import { useToolbarActionLock } from '@/composables/useToolbarActionLock';
import { useContextStore } from '@/stores/context';
import type { BugItem, BugStatusDef, ProjectVersion, VersionType } from '@/types/business';
import type { RequirementSelectOption } from '@/api/requirements';
import { NUM_TABLE_COLUMN } from '@/utils/entityNum';
import { formatDateOnly } from '@/utils/formatDateOnly';
import { linkLabel, parseUrlsFromText } from '@/utils/parseUrls';
import { versionDefsToCanvasNodes } from '@/utils/versionWorkflowLayout';

const props = defineProps<{
  versionId: string;
  hasPrev?: boolean;
  hasNext?: boolean;
}>();

const emit = defineEmits<{
  prev: [];
  next: [];
  close: [];
  deleted: [];
  updated: [version: ProjectVersion];
}>();

const router = useRouter();
const ctx = useContextStore();
const { canManageCatalog } = usePermissions();
const canEdit = computed(() => canManageCatalog(ctx.projectId));
const message = useMessage();
const dialog = useDialog();
const { options: memberSelectOptions, labelByUserId: memberLabelByUserId } = useProjectMemberOptions(
  computed(() => ctx.projectId)
);
const memberLabel = (userId: string | null | undefined) =>
  userId ? memberLabelByUserId.value.get(userId) || userId : '';
const versionTypeOptions = VERSION_TYPE_OPTIONS;

const version = ref<ProjectVersion | null>(null);
const requirements = ref<RequirementSelectOption[]>([]);
const bugs = ref<BugItem[]>([]);
const statuses = ref<BugStatusDef[]>([]);
const loading = ref(false);
const loadingReqs = ref(false);
const loadingBugs = ref(false);
const activeTab = ref('info');
const selectedNodeKey = ref<string | null>(null);
const actingKey = ref<string | null>(null);
const editMode = ref(false);
const saving = ref(false);
const { toolbarActionLocked, lockToolbarActions, stopToolbarActionLock } = useToolbarActionLock();
const editForm = ref({
  name: '',
  build_number: '' as string,
  released_at: null as string | null,
  version_type: 'app_release' as VersionType,
});

const bugDrawerVisible = ref(false);
const activeBugId = ref<string | null>(null);

const canvasNodes = computed(() =>
  version.value
    ? versionDefsToCanvasNodes(version.value.workflow_defs, version.value.nodes)
    : []
);

const statusLabelMap = computed(() => {
  const m = new Map<string, string>();
  for (const s of statuses.value) m.set(s.key, s.label);
  return m;
});

const activeBugIndex = computed(() =>
  activeBugId.value ? bugs.value.findIndex((b) => b.id === activeBugId.value) : -1
);

function clearNodeSelection() {
  selectedNodeKey.value = null;
}

function onNodeSelect(key: string | null) {
  selectedNodeKey.value = key;
}

async function onCompleteSelected() {
  if (!version.value || !selectedNodeKey.value) return;
  actingKey.value = selectedNodeKey.value;
  try {
    const { data } = await completeVersionNode(version.value.id, selectedNodeKey.value);
    version.value = data.version;
    emit('updated', data.version);
    message.success('节点已完成');
  } catch (e: unknown) {
    const detail =
      (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? '操作失败';
    message.error(typeof detail === 'string' ? detail : '操作失败');
  } finally {
    actingKey.value = null;
  }
}

async function onReopenSelected() {
  if (!version.value || !selectedNodeKey.value) return;
  actingKey.value = selectedNodeKey.value;
  try {
    const { data } = await reopenVersionNode(version.value.id, selectedNodeKey.value);
    version.value = data;
    emit('updated', data);
    message.success('节点已重开');
  } catch (e: unknown) {
    const detail =
      (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? '操作失败';
    message.error(typeof detail === 'string' ? detail : '操作失败');
  } finally {
    actingKey.value = null;
  }
}

async function onNodeMetaUpdated(updated: ProjectVersion) {
  version.value = updated;
  emit('updated', updated);
}

function enterEdit() {
  if (!version.value) return;
  editForm.value = {
    name: version.value.name,
    build_number: version.value.build_number ?? '',
    released_at: version.value.released_at?.slice(0, 10) ?? null,
    version_type: version.value.version_type,
  };
  editMode.value = true;
}

function cancelEdit() {
  editMode.value = false;
}

async function saveVersion() {
  if (!version.value || !editForm.value.name.trim()) {
    message.warning('请填写版本名称');
    return;
  }
  const typeChanged = editForm.value.version_type !== version.value.version_type;
  if (typeChanged) {
    const confirmed = await new Promise<boolean>((resolve) => {
      dialog.warning({
        title: '修改版本类型',
        content: '修改类型将重置该版本全部工作流进度，是否继续？',
        positiveText: '继续',
        negativeText: '取消',
        onPositiveClick: () => resolve(true),
        onNegativeClick: () => resolve(false),
        onClose: () => resolve(false),
      });
    });
    if (!confirmed) return;
  }
  saving.value = true;
  lockToolbarActions();
  try {
    const { data } = await updateVersion(version.value.id, {
      name: editForm.value.name.trim(),
      build_number: editForm.value.build_number.trim() || null,
      released_at: editForm.value.released_at || null,
      version_type: editForm.value.version_type,
    });
    version.value = data;
    lockToolbarActions();
    editMode.value = false;
    emit('updated', data);
    message.success('已保存');
  } catch (e: unknown) {
    const detail =
      (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? '保存失败';
    message.error(typeof detail === 'string' ? detail : '保存失败');
  } finally {
    saving.value = false;
  }
}

function onDelete() {
  if (!version.value || toolbarActionLocked.value || saving.value) return;
  dialog.warning({
    title: '删除版本',
    content: `确定删除「${version.value.name}」？`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await deleteVersion(version.value!.id);
        message.success('已删除');
        emit('deleted');
      } catch (e: unknown) {
        const detail =
          (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? '删除失败';
        message.error(typeof detail === 'string' ? detail : '删除失败');
      }
    },
  });
}

function prdLinkAnchor(url: string) {
  return h(
    'a',
    {
      href: url,
      target: '_blank',
      rel: 'noopener',
      class: 'prd-link',
      onClick: (e: MouseEvent) => e.stopPropagation(),
    },
    linkLabel(url, 32)
  );
}

function renderPrdLinks(externalUrl: string | null | undefined) {
  const raw = externalUrl?.trim();
  if (!raw) return '—';
  const urls = parseUrlsFromText(raw, { dedupe: false });
  if (urls.length === 0) return raw;
  const tooltipWrap = (url: string) =>
    h(
      NTooltip,
      { placement: 'top-start', contentStyle: { maxWidth: '400px', wordBreak: 'break-all' } },
      { trigger: () => prdLinkAnchor(url), default: () => url }
    );
  if (urls.length === 1) return tooltipWrap(urls[0]);
  return h('div', { class: 'prd-links-stack' }, urls.map((url) => tooltipWrap(url)));
}

const requirementColumns: DataTableColumns<RequirementSelectOption> = [
  { ...NUM_TABLE_COLUMN },
  {
    title: '标题',
    key: 'title',
    width: 220,
    ellipsis: { tooltip: true },
  },
  {
    title: '状态',
    key: 'status',
    width: 90,
    render: (r) =>
      h(
        NTag,
        { size: 'small', type: requirementStatusTagType(r.status), bordered: false },
        () => requirementStatusLabel(r.status)
      ),
  },
  {
    title: 'PRD 链接',
    key: 'external_url',
    width: 200,
    render: (r) => renderPrdLinks(r.external_url),
  },
  {
    title: '操作',
    key: 'a',
    width: 120,
    render: (row) =>
      h(
        NButton,
        { size: 'small', quaternary: true, onClick: () => goCases(row.id) },
        () => '查看用例'
      ),
  },
];

const bugColumns = computed<DataTableColumns<BugItem>>(() => [
  { ...NUM_TABLE_COLUMN, width: 56 },
  {
    title: '标题',
    key: 'title',
    width: 220,
    ellipsis: { tooltip: true },
    render: (row) =>
      h(
        NButton,
        {
          text: true,
          type: 'primary',
          onClick: (e: Event) => {
            e.stopPropagation();
            openBug(row.id);
          },
        },
        () => row.title
      ),
  },
  {
    title: '状态',
    key: 'status_key',
    width: 96,
    render: (row) => statusLabelMap.value.get(row.status_key) ?? row.status_key,
  },
]);

function goCases(requirementId: string) {
  router.push({ name: 'cases', query: { requirement_id: requirementId } });
}

function bugRowProps(row: BugItem) {
  return { style: 'cursor: pointer', onClick: () => openBug(row.id) };
}

function openBug(id: string) {
  activeBugId.value = id;
  bugDrawerVisible.value = true;
}

function closeBugDrawer() {
  bugDrawerVisible.value = false;
  activeBugId.value = null;
}

function onBugDrawerShowChange(show: boolean) {
  if (!show) closeBugDrawer();
}

function goPrevBug() {
  const idx = activeBugIndex.value;
  if (idx > 0) openBug(bugs.value[idx - 1].id);
}

function goNextBug() {
  const idx = activeBugIndex.value;
  if (idx >= 0 && idx < bugs.value.length - 1) openBug(bugs.value[idx + 1].id);
}

async function onBugDeleted() {
  closeBugDrawer();
  await loadBugs();
}

async function onBugUpdated() {
  await loadBugs();
}

async function loadVersion() {
  if (!ctx.projectId) {
    version.value = null;
    return;
  }
  loading.value = true;
  try {
    const { data } = await getVersion(props.versionId);
    version.value = data;
    selectedNodeKey.value = null;
  } catch {
    message.error('版本不存在或无权访问');
    emit('close');
  } finally {
    loading.value = false;
  }
}

async function loadRequirements() {
  if (!ctx.projectId || !props.versionId) {
    requirements.value = [];
    return;
  }
  loadingReqs.value = true;
  try {
    requirements.value = await fetchRequirementOptions({
      version_id: props.versionId,
      limit: 100,
    });
  } finally {
    loadingReqs.value = false;
  }
}

async function loadBugs() {
  if (!ctx.projectId || !props.versionId) {
    bugs.value = [];
    return;
  }
  loadingBugs.value = true;
  try {
    const { data } = await listBugs({ plan_version_id: props.versionId, page_size: 100 });
    bugs.value = data.items;
    if (activeBugId.value && !data.items.some((b) => b.id === activeBugId.value)) {
      closeBugDrawer();
    }
  } finally {
    loadingBugs.value = false;
  }
}

async function loadStatuses() {
  if (!ctx.projectId) {
    statuses.value = [];
    return;
  }
  const { data } = await listBugStatuses(ctx.projectId);
  statuses.value = data;
}

async function load() {
  await Promise.all([loadVersion(), loadRequirements(), loadBugs(), loadStatuses()]);
}

watch(() => props.versionId, () => {
  stopToolbarActionLock();
  editMode.value = false;
  load();
});
watch(() => ctx.projectId, load);

onMounted(load);
</script>

<style scoped>
.panel-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
}
.version-detail-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}
.header-block {
  position: sticky;
  top: 0;
  z-index: 20;
  flex-shrink: 0;
  padding: 12px 16px 0;
  border-bottom: 1px solid var(--n-border-color);
  background: var(--n-color);
  isolation: isolate;
}
.panel-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.toolbar-actions--locked {
  pointer-events: none;
}
.panel-title-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding-bottom: 12px;
}
.panel-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 12px 16px 16px;
}
.workflow-block {
  margin-bottom: 12px;
}
.tabs-block {
  margin-top: 8px;
}
.prd-link {
  color: var(--n-primary-color);
  text-decoration: none;
}
.prd-link:hover {
  text-decoration: underline;
}
.prd-links-stack {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
</style>
