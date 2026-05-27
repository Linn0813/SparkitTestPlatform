<template>
  <n-card v-if="version">
    <template #header>
      <n-space align="center" :size="12">
        <n-button quaternary size="small" @click="goBack">返回列表</n-button>
        <n-text strong style="font-size: 16px">{{ version.name }}</n-text>
        <n-text depth="3" style="font-size: 13px">
          需求 {{ requirements.length }} · 规划缺陷 {{ bugs.length }}
          <template v-if="version.released_at">
            · 上线时间 {{ formatDateOnly(version.released_at) }}
          </template>
        </n-text>
      </n-space>
    </template>

    <n-tabs v-model:value="activeTab" type="line">
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
  </n-card>
  <n-spin v-else :show="loadingVersion" style="min-height: 200px" />

  <n-drawer
    v-model:show="drawerVisible"
    :width="'50%'"
    placement="right"
    :trap-focus="false"
    @update:show="onDrawerShowChange"
  >
    <n-drawer-content :closable="false" body-content-style="padding: 0">
      <BugDetailPanel
        v-if="activeBugId"
        :bug-id="activeBugId"
        :has-prev="activeBugIndex > 0"
        :has-next="activeBugIndex >= 0 && activeBugIndex < bugs.length - 1"
        @prev="goPrevBug"
        @next="goNextBug"
        @close="closeDrawer"
        @deleted="onBugDeleted"
        @updated="onBugUpdated"
      />
    </n-drawer-content>
  </n-drawer>
</template>

<script setup lang="ts">
import { computed, h, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  NButton,
  NCard,
  NDataTable,
  NDrawer,
  NDrawerContent,
  NSpace,
  NSpin,
  NTabPane,
  NTabs,
  NTag,
  NText,
  NTooltip,
  useMessage,
  type DataTableColumns,
} from 'naive-ui';
import { listBugs } from '@/api/bugs';
import { listRequirements } from '@/api/requirements';
import { listBugStatuses } from '@/api/templates';
import { getVersion } from '@/api/versions';
import BugDetailPanel from '@/components/BugDetailPanel.vue';
import { useContextStore } from '@/stores/context';
import type { BugItem, BugStatusDef, ProjectVersion, Requirement } from '@/types/business';
import { requirementStatusLabel, requirementStatusTagType } from '@/constants/requirementStatus';
import { NUM_TABLE_COLUMN } from '@/utils/entityNum';
import { formatDateOnly } from '@/utils/formatDateOnly';
import { linkLabel, parseUrlsFromText } from '@/utils/parseUrls';

const route = useRoute();
const router = useRouter();
const ctx = useContextStore();
const message = useMessage();

const versionId = computed(() => route.params.id as string);
const version = ref<ProjectVersion | null>(null);
const requirements = ref<Requirement[]>([]);
const bugs = ref<BugItem[]>([]);
const statuses = ref<BugStatusDef[]>([]);
const loadingVersion = ref(false);
const loadingReqs = ref(false);
const loadingBugs = ref(false);
const activeTab = ref('requirements');
const drawerVisible = ref(false);
const activeBugId = ref<string | null>(null);

const statusLabelMap = computed(() => {
  const m = new Map<string, string>();
  for (const s of statuses.value) m.set(s.key, s.label);
  return m;
});

const activeBugIndex = computed(() =>
  activeBugId.value ? bugs.value.findIndex((b) => b.id === activeBugId.value) : -1
);

function followersSummary(row: BugItem): string {
  const names = row.followers?.map((f) => f.name).filter(Boolean);
  if (names?.length) return names.join('、');
  if (row.follower_ids?.length) return `${row.follower_ids.length} 人`;
  return '—';
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
      {
        placement: 'top-start',
        contentStyle: { maxWidth: '400px', wordBreak: 'break-all' },
      },
      {
        trigger: () => prdLinkAnchor(url),
        default: () => url,
      }
    );

  if (urls.length === 1) return tooltipWrap(urls[0]);

  return h(
    'div',
    { class: 'prd-links-stack' },
    urls.map((url) => tooltipWrap(url))
  );
}

const requirementColumns: DataTableColumns<Requirement> = [
  { ...NUM_TABLE_COLUMN },
  {
    title: '标题',
    key: 'title',
    width: 220,
    minWidth: 120,
    maxWidth: 280,
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
    minWidth: 120,
    maxWidth: 280,
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
  {
    title: '跟进人',
    key: 'followers',
    width: 120,
    ellipsis: { tooltip: true },
    render: (row) => followersSummary(row),
  },
]);

function goBack() {
  router.push({ name: 'versions' });
}

function goCases(requirementId: string) {
  router.push({ name: 'cases', query: { requirement_id: requirementId } });
}

function bugRowProps(row: BugItem) {
  return {
    style: 'cursor: pointer',
    onClick: () => openBug(row.id),
  };
}

function openBug(id: string) {
  activeBugId.value = id;
  drawerVisible.value = true;
}

function closeDrawer() {
  drawerVisible.value = false;
  activeBugId.value = null;
}

function onDrawerShowChange(show: boolean) {
  if (!show) closeDrawer();
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
  closeDrawer();
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
  loadingVersion.value = true;
  try {
    const { data } = await getVersion(versionId.value);
    version.value = data;
  } catch {
    message.error('版本不存在或无权访问');
    goBack();
  } finally {
    loadingVersion.value = false;
  }
}

async function loadRequirements() {
  if (!ctx.projectId || !versionId.value) {
    requirements.value = [];
    return;
  }
  loadingReqs.value = true;
  try {
    const { data } = await listRequirements({ version_id: versionId.value });
    requirements.value = data;
  } finally {
    loadingReqs.value = false;
  }
}

async function loadBugs() {
  if (!ctx.projectId || !versionId.value) {
    bugs.value = [];
    return;
  }
  loadingBugs.value = true;
  try {
    const { data } = await listBugs({ plan_version_id: versionId.value, page_size: 100 });
    bugs.value = data.items;
    if (activeBugId.value && !data.items.some((b) => b.id === activeBugId.value)) {
      closeDrawer();
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

onMounted(load);
watch(versionId, load);
watch(() => ctx.projectId, load);
</script>

<style scoped>
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
