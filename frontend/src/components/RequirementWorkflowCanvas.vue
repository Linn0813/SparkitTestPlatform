<template>
  <div class="workflow-canvas" :class="`workflow-canvas--${mode}`">
    <div ref="scrollRef" class="workflow-scroll">
      <div ref="trackRef" class="workflow-track" :style="{ minWidth: trackMinWidth }">
        <svg class="workflow-lines" :width="svgWidth" :height="svgHeight">
          <path
            v-for="(d, i) in connectorPaths"
            :key="`conn-${i}`"
            :d="d"
            fill="none"
            stroke="var(--wf-line-color, #dcdcdc)"
            stroke-width="1.5"
          />
        </svg>
        <div class="workflow-lanes">
          <div
            v-for="laneIdx in allLaneIndexes"
            :key="laneIdx"
            :ref="(el) => setLaneRef(laneIdx, el as HTMLElement | null)"
            class="workflow-lane"
            :data-lane="laneIdx"
          >
            <div
              v-for="node in nodesInLane(laneIdx)"
              :key="node.render_key"
              :ref="(el) => setNodeRef(node.render_key, el as HTMLElement | null)"
            class="workflow-node workflow-node--column"
            :class="nodeClass(node)"
            :style="columnStyles[node.render_key]"
            @click="onNodeClick(node, $event)"
            >
              <div class="workflow-node-inner">
                <span class="workflow-dot" :class="nodeStateDotClass(node.state, node.enabled)" />
                <div class="workflow-node-text">
                  <n-text strong class="workflow-node-label">{{ node.label }}</n-text>
                  <n-text depth="3" class="workflow-node-meta">
                    {{ requirementRoleLabels(node.role_keys) }}
                    <template v-if="mode !== 'preview'"> · {{ nodeStateLabel(node.state) }}</template>
                  </n-text>
                </div>
                <n-checkbox
                  v-if="mode === 'edit' && editable"
                  :checked="node.enabled"
                  @click.stop
                  @update:checked="(v: boolean) => emit('toggle-enabled', node.node_key, v)"
                />
              </div>
            </div>
          </div>
        </div>
        <div class="workflow-overlay">
          <div
            v-for="node in layoutSpanNodes"
            :key="node.render_key"
            :ref="(el) => setNodeRef(node.render_key, el as HTMLElement | null)"
            class="workflow-node workflow-node--span"
            :class="nodeClass(node)"
            :style="spanStyles[node.render_key]"
            @click="onNodeClick(node, $event)"
          >
            <div class="workflow-node-inner">
              <span class="workflow-dot" :class="nodeStateDotClass(node.state, node.enabled)" />
              <div class="workflow-node-text">
                <n-text strong class="workflow-node-label">{{ node.label }}</n-text>
                <n-text depth="3" class="workflow-node-meta">
                  {{ requirementRoleLabels(node.role_keys) }}
                  <template v-if="mode !== 'preview'"> · {{ nodeStateLabel(node.state) }}</template>
                </n-text>
              </div>
              <n-checkbox
                v-if="mode === 'edit' && editable"
                :checked="node.enabled"
                @click.stop
                @update:checked="(v: boolean) => emit('toggle-enabled', node.node_key, v)"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';
import { NCheckbox, NText } from 'naive-ui';
import { requirementRoleLabels } from '@/constants/requirementNodes';
import type { RequirementType } from '@/types/business';
import {
  collectAllLaneIndexes,
  collectBlockingConnectorPairs,
  columnNodesForLane,
  connectorAnchorPoint,
  layoutRowCount,
  layoutRowCountForLane,
  nodeStateDotClass,
  nodeStateLabel,
  partitionCanvasNodes,
  rowIndexInLane,
  rowTopForLayoutGrid,
  spanNodeLeftX,
  type WorkflowCanvasNode,
} from '@/utils/requirementWorkflowLayout';

const ROW_GAP = 10;

const props = withDefaults(
  defineProps<{
    nodes?: WorkflowCanvasNode[];
    mode?: 'preview' | 'view' | 'edit';
    editable?: boolean;
    reqType?: RequirementType;
    workflowFrozen?: boolean;
    selectedNodeKey?: string | null;
  }>(),
  {
    nodes: () => [],
    mode: 'view',
    editable: true,
    reqType: 'feature',
    workflowFrozen: false,
  }
);

const emit = defineEmits<{
  'toggle-enabled': [nodeKey: string, enabled: boolean];
  'node-select': [nodeKey: string];
}>();

const scrollRef = ref<HTMLElement | null>(null);
const trackRef = ref<HTMLElement | null>(null);
const nodeRefs = ref<Record<string, HTMLElement | null>>({});
const laneRefs = ref<Record<number, HTMLElement | null>>({});
const svgWidth = ref(800);
const svgHeight = ref(200);
const connectorPaths = ref<string[]>([]);
const spanStyles = ref<Record<string, { left: string; top: string }>>({});
const columnStyles = ref<Record<string, { top: string }>>({});

const allLaneIndexes = computed(() => collectAllLaneIndexes(props.nodes ?? []));
const partitioned = computed(() => partitionCanvasNodes(props.nodes ?? []));
const layoutColumnNodes = computed(() => partitioned.value.columnNodes);
const layoutSpanNodes = computed(() => partitioned.value.spanNodes);

const trackMinWidth = computed(() => {
  const n = allLaneIndexes.value.length;
  if (n === 0) return '100%';
  return `${n * 140 + Math.max(0, n - 1) * 48}px`;
});

function nodesInLane(laneIdx: number) {
  return columnNodesForLane(laneIdx, layoutColumnNodes.value);
}

function setNodeRef(key: string, el: HTMLElement | null) {
  if (el) nodeRefs.value[key] = el;
  else delete nodeRefs.value[key];
}

function setLaneRef(laneIndex: number, el: HTMLElement | null) {
  if (el) laneRefs.value[laneIndex] = el;
  else delete laneRefs.value[laneIndex];
}

function nodeClass(node: WorkflowCanvasNode) {
  return {
    'workflow-node--disabled': !node.enabled,
    'workflow-node--active': node.state === 'in_progress',
    'workflow-node--selected': props.selectedNodeKey === node.node_key,
  };
}

function onNodeClick(node: WorkflowCanvasNode, event: MouseEvent) {
  if (props.mode === 'edit' && props.editable) {
    const target = event.target as HTMLElement;
    if (target.closest('.n-checkbox')) return;
    emit('toggle-enabled', node.node_key, !node.enabled);
    return;
  }
  if (props.mode === 'view') {
    emit('node-select', node.node_key);
  }
}

function bezier(x1: number, y1: number, x2: number, y2: number): string {
  const mx = (x1 + x2) / 2;
  return `M ${x1} ${y1} C ${mx} ${y1}, ${mx} ${y2}, ${x2} ${y2}`;
}

function sampleNodeHeight(): number {
  for (const node of layoutColumnNodes.value) {
    const el = nodeRefs.value[node.render_key];
    if (el) return el.offsetHeight;
  }
  for (const el of Object.values(nodeRefs.value)) {
    if (el) return el.offsetHeight;
  }
  return 52;
}

function rowTopInLane(
  rowIndex: number,
  nodeHeight: number,
  laneHeight: number,
  rowCount: number,
): number | null {
  return rowTopForLayoutGrid(rowIndex, nodeHeight, laneHeight, rowCount, ROW_GAP);
}

function rowTopOnTrack(
  rowIndex: number,
  nodeHeight: number,
  rowCount: number,
  trackRect: DOMRect,
): number | null {
  const laneIdx = allLaneIndexes.value[0];
  if (laneIdx == null) return null;
  const laneEl = laneRefs.value[laneIdx];
  if (!laneEl) return null;
  const rel = rowTopInLane(rowIndex, nodeHeight, laneEl.offsetHeight, rowCount);
  if (rel == null) return null;
  return laneEl.getBoundingClientRect().top - trackRect.top + rel;
}

function canvasNodeByRenderKey(renderKey: string): WorkflowCanvasNode | undefined {
  return props.nodes.find((n) => n.render_key === renderKey);
}

async function updateLayout() {
  await nextTick();
  await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
  const trackEl = trackRef.value;
  if (!trackEl) return;

  const nodeHeight = sampleNodeHeight();
  const gridRowCount = layoutRowCount(props.nodes ?? []);
  const minLaneHeight = gridRowCount * nodeHeight + (gridRowCount - 1) * ROW_GAP;
  for (const laneIdx of allLaneIndexes.value) {
    const laneEl = laneRefs.value[laneIdx];
    if (laneEl) laneEl.style.minHeight = `${minLaneHeight}px`;
  }

  await nextTick();
  await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));

  const trackRect = trackEl.getBoundingClientRect();
  svgWidth.value = trackEl.offsetWidth;
  svgHeight.value = Math.max(trackEl.offsetHeight, 160);

  const laneRects = new Map<number, DOMRect>();
  for (const laneIdx of allLaneIndexes.value) {
    const el = laneRefs.value[laneIdx];
    if (el) laneRects.set(laneIdx, el.getBoundingClientRect());
  }

  const measuredHeight = sampleNodeHeight();
  const colStyles: Record<string, { top: string }> = {};
  const styles: Record<string, { left: string; top: string }> = {};

  for (const node of layoutColumnNodes.value) {
    const laneEl = laneRefs.value[node.span_lanes[0]];
    if (!laneEl) continue;
    const laneRowCount = layoutRowCountForLane(
      node.span_lanes[0],
      props.nodes ?? [],
      layoutColumnNodes.value,
    );
    const topY = rowTopInLane(
      rowIndexInLane(node, layoutColumnNodes.value),
      measuredHeight,
      laneEl.offsetHeight,
      laneRowCount,
    );
    if (topY == null) continue;
    colStyles[node.render_key] = { top: `${topY}px` };
  }

  for (const node of layoutSpanNodes.value) {
    const leftX = spanNodeLeftX(node, laneRects, trackRect);
    const topY = rowTopOnTrack(node.sort_in_lane, measuredHeight, gridRowCount, trackRect);
    if (leftX == null || topY == null) continue;
    styles[node.render_key] = {
      left: `${leftX}px`,
      top: `${topY}px`,
    };
  }
  columnStyles.value = colStyles;
  spanStyles.value = styles;

  await nextTick();
  await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
  drawConnectors(trackEl);
}

function drawConnectors(trackEl: HTMLElement) {
  const trackRect = trackEl.getBoundingClientRect();
  const paths: string[] = [];
  for (const { from, to } of collectBlockingConnectorPairs(
    props.nodes ?? [],
    allLaneIndexes.value,
    layoutColumnNodes.value,
  )) {
    const le = nodeRefs.value[from];
    const re = nodeRefs.value[to];
    const fromNode = canvasNodeByRenderKey(from);
    const toNode = canvasNodeByRenderKey(to);
    if (!le || !re || !fromNode || !toNode) continue;
    const start = connectorAnchorPoint(fromNode, le, 'right', trackRect);
    const end = connectorAnchorPoint(toNode, re, 'left', trackRect);
    if (end.x <= start.x + 4) continue;
    paths.push(bezier(start.x, start.y, end.x, end.y));
  }
  connectorPaths.value = paths;
}

let resizeObserver: ResizeObserver | null = null;

function observeLayout() {
  resizeObserver?.disconnect();
  resizeObserver = new ResizeObserver(() => {
    void updateLayout();
  });
  if (trackRef.value) resizeObserver.observe(trackRef.value);
  if (scrollRef.value) resizeObserver.observe(scrollRef.value);
}

onMounted(async () => {
  await nextTick();
  observeLayout();
  scrollRef.value?.addEventListener('scroll', updateLayout, { passive: true });
  void updateLayout();
});

onUnmounted(() => {
  resizeObserver?.disconnect();
  scrollRef.value?.removeEventListener('scroll', updateLayout);
});

watch(
  () =>
    props.nodes
      .map(
        (n) =>
          `${n.render_key}:${n.sort_in_lane}:${n.span_lanes.join('-')}:${n.blocks_lane_gate}:${n.display_lane}`
      )
      .join('|'),
  () => {
    void updateLayout();
  }
);
watch([allLaneIndexes, layoutSpanNodes], () => {
  void updateLayout();
});
</script>

<style scoped>
.workflow-canvas {
  --wf-line-color: rgba(0, 0, 0, 0.12);
  --wf-node-border: rgba(0, 0, 0, 0.14);
  --wf-node-bg: var(--n-color, #fff);
  border: 1px solid var(--n-border-color);
  border-radius: 8px;
  background: var(--n-color-modal);
  max-width: 100%;
  overflow: hidden;
}
.workflow-scroll {
  width: 100%;
  max-width: 100%;
  overflow-x: auto;
  overflow-y: hidden;
  padding: 16px 12px;
  position: relative;
  box-sizing: border-box;
}
.workflow-track {
  position: relative;
  min-height: 140px;
  width: max-content;
  min-width: 100%;
}
.workflow-lines {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 3;
}
.workflow-lanes {
  display: flex;
  gap: 48px;
  align-items: stretch;
  position: relative;
  z-index: 1;
}
.workflow-lane {
  position: relative;
  width: 140px;
  flex-shrink: 0;
  min-height: 100%;
}
.workflow-overlay {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 2;
}
.workflow-node {
  cursor: default;
}
.workflow-node--column {
  position: absolute;
  left: 0;
  width: 140px;
  box-sizing: border-box;
}
.workflow-node--span {
  position: absolute;
  transform: translateX(-50%);
  pointer-events: auto;
  width: 140px;
  box-sizing: border-box;
}
.workflow-node--disabled {
  opacity: 0.45;
}
.workflow-node-inner {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  width: 100%;
  box-sizing: border-box;
  padding: 8px 10px;
  border: 1px solid var(--wf-node-border, var(--n-border-color));
  border-radius: 8px;
  background: var(--wf-node-bg);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}
.workflow-node--disabled .workflow-node-inner {
  border-color: rgba(0, 0, 0, 0.08);
  background: var(--n-color-modal, #fafafa);
}
.workflow-node--active .workflow-node-inner {
  border-color: var(--n-primary-color);
  box-shadow: 0 0 0 1px rgba(24, 160, 88, 0.15);
}
.workflow-node--selected .workflow-node-inner {
  border-color: var(--n-primary-color);
  box-shadow: 0 0 0 2px rgba(24, 160, 88, 0.25);
}
.workflow-node--view {
  cursor: pointer;
}
.workflow-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-top: 6px;
  flex-shrink: 0;
}
.dot-pending { background: #aeaeb2; }
.dot-active { background: #ffa200; }
.dot-done { background: #00c261; }
.dot-disabled { background: #dcdcdc; }
.workflow-node-text {
  flex: 1;
  min-width: 0;
}
.workflow-node-label {
  display: block;
  font-size: 13px;
}
.workflow-node-meta {
  display: block;
  font-size: 11px;
  margin-top: 2px;
}
</style>
