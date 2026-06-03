import type { TagProps } from 'naive-ui';
import type { RequirementNodeState } from '@/types/business';

export interface WorkflowNodeSource {
  node_key: string;
  label: string;
  role_keys: string[];
  lane_index: number;
  lane_indexes?: number[];
  blocks_lane_gate?: boolean;
  sort_in_lane: number;
  enabled: boolean;
  state: RequirementNodeState;
}

export interface WorkflowCanvasNode extends WorkflowNodeSource {
  render_key: string;
  span_lanes: number[];
  display_lane: number;
  is_span_positioned: boolean;
}

export interface WorkflowLaneColumn {
  lane_index: number;
  nodes: WorkflowCanvasNode[];
}

export function nodeLaneIndexes(n: WorkflowNodeSource): number[] {
  return n.lane_indexes?.length ? [...n.lane_indexes].sort((a, b) => a - b) : [n.lane_index];
}

export function computeDisplayLane(span_lanes: number[]): number {
  if (span_lanes.length <= 1) return span_lanes[0] ?? 0;
  return (span_lanes[0] + span_lanes[span_lanes.length - 1]) / 2;
}

/** 每个逻辑节点只渲染一张卡片；多阶段节点水平位置取 span 中点。 */
export function expandWorkflowCanvasNodes(nodes: WorkflowNodeSource[]): WorkflowCanvasNode[] {
  return nodes.map((n) => {
    const span_lanes = nodeLaneIndexes(n);
    const is_span_positioned = span_lanes.length > 1;
    return {
      ...n,
      lane_index: span_lanes[0],
      span_lanes,
      display_lane: computeDisplayLane(span_lanes),
      is_span_positioned,
      blocks_lane_gate: n.blocks_lane_gate ?? true,
      render_key: n.node_key,
    };
  });
}

export function collectAllLaneIndexes(nodes: WorkflowCanvasNode[]): number[] {
  const set = new Set<number>();
  for (const n of nodes ?? []) {
    for (const lane of n.span_lanes ?? []) {
      set.add(lane);
    }
  }
  return [...set].sort((a, b) => a - b);
}

export function partitionCanvasNodes(nodes: WorkflowCanvasNode[]): {
  columnNodes: WorkflowCanvasNode[];
  spanNodes: WorkflowCanvasNode[];
} {
  const columnNodes: WorkflowCanvasNode[] = [];
  const spanNodes: WorkflowCanvasNode[] = [];
  for (const n of nodes ?? []) {
    if (n.is_span_positioned) spanNodes.push(n);
    else columnNodes.push(n);
  }
  return { columnNodes, spanNodes };
}

export function columnNodesForLane(laneIndex: number, columnNodes: WorkflowCanvasNode[] | undefined): WorkflowCanvasNode[] {
  return (columnNodes ?? [])
    .filter((n) => n.span_lanes[0] === laneIndex)
    .sort((a, b) => a.sort_in_lane - b.sort_in_lane);
}

/** 该列是否只有一个列内节点（不含 span 跨列节点）。 */
export function isSingleColumnNodeLane(laneIndex: number, columnNodes: WorkflowCanvasNode[]): boolean {
  return columnNodesForLane(laneIndex, columnNodes).length === 1;
}

/** 列内节点的布局行索引：单列节点列始终为 0（垂直居中），多节点列用 sort_in_lane。 */
export function rowIndexInLane(node: WorkflowCanvasNode, columnNodes: WorkflowCanvasNode[]): number {
  if (isSingleColumnNodeLane(node.span_lanes[0], columnNodes)) return 0;
  return node.sort_in_lane;
}

/** 参与某列行高计算的节点（不含跨列 span，按起始列 sort 堆叠）。 */
export function laneRowNodes(laneIndex: number, nodes: WorkflowCanvasNode[]): WorkflowCanvasNode[] {
  return nodes
    .filter((n) => !n.is_span_positioned && n.span_lanes[0] === laneIndex)
    .sort((a, b) => a.sort_in_lane - b.sort_in_lane);
}

/** 全画布统一行网格行数（含 span 节点的 sort_in_lane）。 */
export function layoutRowCount(nodes: WorkflowCanvasNode[]): number {
  if (!nodes.length) return 1;
  return Math.max(1, ...nodes.map((n) => n.sort_in_lane + 1));
}

/** 某列布局行数：多行 fork 列用全局网格，单列节点列保持单行居中。 */
export function layoutRowCountForLane(
  laneIndex: number,
  nodes: WorkflowCanvasNode[],
  columnNodes?: WorkflowCanvasNode[],
): number {
  const global = layoutRowCount(nodes);
  const cols = columnNodes ?? nodes.filter((n) => !n.is_span_positioned);
  if (isSingleColumnNodeLane(laneIndex, cols) && global > 1) return 1;
  return global;
}

export function rowTopForLayoutGrid(
  rowIndex: number,
  nodeHeight: number,
  laneHeight: number,
  rowCount: number,
  rowGap = 10,
): number | null {
  if (rowCount <= 0) return null;
  const groupHeight = rowCount * nodeHeight + (rowCount - 1) * rowGap;
  const startY = (laneHeight - groupHeight) / 2;
  return startY + rowIndex * (nodeHeight + rowGap);
}

export function connectorAnchorPoint(
  node: WorkflowCanvasNode,
  el: HTMLElement,
  side: 'left' | 'right',
  trackRect: DOMRect,
): { x: number; y: number } {
  const rect = el.getBoundingClientRect();
  const y = rect.top + rect.height / 2 - trackRect.top;
  const centerX = rect.left + rect.width / 2 - trackRect.left;
  const half = rect.width / 2;
  const x = node.is_span_positioned
    ? side === 'left'
      ? centerX - half
      : centerX + half
    : side === 'left'
      ? rect.left - trackRect.left
      : rect.right - trackRect.left;
  return { x, y };
}

export function maxLaneRowCount(nodes: WorkflowCanvasNode[], _allLaneIndexes: number[]): number {
  return layoutRowCount(nodes);
}

export function buildWorkflowLaneColumns(
  allLaneIndexes: number[],
  columnNodes: WorkflowCanvasNode[],
): WorkflowLaneColumn[] {
  return allLaneIndexes.map((lane_index) => ({
    lane_index,
    nodes: columnNodesForLane(lane_index, columnNodes),
  }));
}

/** @deprecated 使用 buildWorkflowLaneColumns */
export function buildWorkflowLanes(nodes: WorkflowCanvasNode[]): WorkflowLaneColumn[] {
  const { columnNodes } = partitionCanvasNodes(nodes);
  return buildWorkflowLaneColumns(collectAllLaneIndexes(nodes), columnNodes);
}

/** 阻塞节点：连到右侧最近的有卡片的目标列（跳过无卡片的空列）。 */
export function collectBlockingConnectorPairs(
  nodes: WorkflowCanvasNode[],
  allLaneIndexes: number[],
  columnNodes: WorkflowCanvasNode[],
): { from: string; to: string }[] {
  const pairs: { from: string; to: string }[] = [];
  const seen = new Set<string>();

  function nextTargetLane(fromIdx: number): number | null {
    for (let j = fromIdx + 1; j < allLaneIndexes.length; j++) {
      const lane = allLaneIndexes[j];
      if (columnNodesForLane(lane, columnNodes).length > 0) return lane;
    }
    return null;
  }

  for (let i = 0; i < allLaneIndexes.length; i++) {
    const leftLane = allLaneIndexes[i];
    const rightLane = nextTargetLane(i);
    if (rightLane == null) continue;

    const sources = nodes.filter(
      (n) =>
        n.blocks_lane_gate !== false &&
        n.span_lanes[0] === leftLane &&
        Math.max(...n.span_lanes) < rightLane,
    );
    const targets = columnNodesForLane(rightLane, columnNodes);
    for (const ln of sources) {
      for (const rn of targets) {
        if (ln.node_key === rn.node_key) continue;
        const key = `${ln.render_key}->${rn.render_key}`;
        if (seen.has(key)) continue;
        seen.add(key);
        pairs.push({ from: ln.render_key, to: rn.render_key });
      }
    }
  }
  return pairs;
}

export function laneCenterX(
  laneIndex: number,
  laneRects: Map<number, DOMRect>,
  trackRect: DOMRect,
): number | null {
  const rect = laneRects.get(laneIndex);
  if (!rect) return null;
  return rect.left + rect.width / 2 - trackRect.left;
}

export function spanNodeLeftX(
  node: WorkflowCanvasNode,
  laneRects: Map<number, DOMRect>,
  trackRect: DOMRect,
): number | null {
  if (!node.is_span_positioned) return null;
  const minLane = node.span_lanes[0];
  const maxLane = node.span_lanes[node.span_lanes.length - 1];
  const x1 = laneCenterX(minLane, laneRects, trackRect);
  const x2 = laneCenterX(maxLane, laneRects, trackRect);
  if (x1 == null || x2 == null) return null;
  return (x1 + x2) / 2;
}

export function nodeStateDotClass(state: RequirementNodeState, enabled: boolean): string {
  if (!enabled) return 'dot-disabled';
  if (state === 'completed' || state === 'skipped') return 'dot-done';
  if (state === 'in_progress') return 'dot-active';
  return 'dot-pending';
}

export function nodeStateLabel(state: RequirementNodeState): string {
  const map: Record<RequirementNodeState, string> = {
    pending: '未开始',
    in_progress: '进行中',
    completed: '已完成',
    skipped: '已跳过',
  };
  return map[state] ?? state;
}

export function nodeStateTagType(state: RequirementNodeState, enabled: boolean): TagProps['type'] {
  if (!enabled) return 'default';
  if (state === 'completed') return 'success';
  if (state === 'in_progress') return 'warning';
  if (state === 'skipped') return 'default';
  return 'default';
}
