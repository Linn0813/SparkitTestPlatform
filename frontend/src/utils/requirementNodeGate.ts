import type { RequirementNodeProgress } from '@/types/business';

export type NodeGateResult = { ok: true } | { ok: false; reason: string };

const GATE_BLOCKED_REASON = '请先完成上一阶段节点';

function nodeLaneIndexes(n: RequirementNodeProgress): number[] {
  return n.lane_indexes?.length ? [...n.lane_indexes].sort((a, b) => a - b) : [n.lane_index];
}

function buildLanesFromNodes(nodes: RequirementNodeProgress[]): RequirementNodeProgress[][] {
  const byLane = new Map<number, RequirementNodeProgress[]>();
  for (const n of nodes) {
    for (const lane of nodeLaneIndexes(n)) {
      const list = byLane.get(lane) ?? [];
      if (!list.some((x) => x.node_key === n.node_key)) list.push(n);
      byLane.set(lane, list);
    }
  }
  return [...byLane.keys()].sort((a, b) => a - b).map((k) => byLane.get(k)!);
}

function nodeMap(nodes: RequirementNodeProgress[]): Map<string, RequirementNodeProgress> {
  return new Map(nodes.map((n) => [n.node_key, n]));
}

function minLaneNumber(nodes: RequirementNodeProgress[], nodeKey: string): number | null {
  const n = nodes.find((x) => x.node_key === nodeKey);
  if (!n) return null;
  return Math.min(...nodeLaneIndexes(n));
}

function findLaneListIndex(nodes: RequirementNodeProgress[], nodeKey: string): number | null {
  const minLane = minLaneNumber(nodes, nodeKey);
  if (minLane === null) return null;
  const sortedLaneNums = [...new Set(nodes.flatMap((n) => nodeLaneIndexes(n)))].sort((a, b) => a - b);
  const idx = sortedLaneNums.indexOf(minLane);
  return idx === -1 ? null : idx;
}

function isDone(node: RequirementNodeProgress | undefined): boolean {
  if (!node || !node.enabled) return true;
  return node.state === 'completed' || node.state === 'skipped';
}

function enabledInLane(
  lane: RequirementNodeProgress[],
  map: Map<string, RequirementNodeProgress>,
): RequirementNodeProgress[] {
  return lane.filter((d) => map.get(d.node_key)?.enabled);
}

function laneGateDone(lane: RequirementNodeProgress[], map: Map<string, RequirementNodeProgress>): boolean {
  const gateNodes = enabledInLane(lane, map).filter((d) => d.blocks_lane_gate !== false);
  if (!gateNodes.length) return true;
  return gateNodes.every((d) => isDone(map.get(d.node_key)));
}

function previousLaneGateOk(
  nodes: RequirementNodeProgress[],
  nodeKey: string,
): NodeGateResult {
  const lanes = buildLanesFromNodes(nodes);
  const laneIdx = findLaneListIndex(nodes, nodeKey);
  if (laneIdx === null) return { ok: false, reason: '未知节点' };
  if (laneIdx === 0) return { ok: true };
  const map = nodeMap(nodes);
  for (const prev of lanes.slice(0, laneIdx)) {
    if (!laneGateDone(prev, map)) {
      return { ok: false, reason: GATE_BLOCKED_REASON };
    }
  }
  return { ok: true };
}

export function canStartNode(
  nodes: RequirementNodeProgress[],
  nodeKey: string,
): NodeGateResult {
  const map = nodeMap(nodes);
  const node = map.get(nodeKey);
  if (!node?.enabled) return { ok: false, reason: '节点未启用或不存在' };
  if (node.state !== 'pending') return { ok: false, reason: '节点当前不可开始' };
  return previousLaneGateOk(nodes, nodeKey);
}

export function canCompleteNode(
  nodes: RequirementNodeProgress[],
  nodeKey: string,
): NodeGateResult {
  const map = nodeMap(nodes);
  const node = map.get(nodeKey);
  if (!node?.enabled) return { ok: false, reason: '节点未启用或不存在' };
  if (node.state !== 'pending' && node.state !== 'in_progress') {
    return { ok: false, reason: '节点当前不可完成' };
  }
  return previousLaneGateOk(nodes, nodeKey);
}

/** 门禁已满足时，未开始节点在服务端会自动变为进行中。 */
export function isNodeActionable(
  nodes: RequirementNodeProgress[],
  node: RequirementNodeProgress,
): boolean {
  if (node.state === 'in_progress') return canCompleteNode(nodes, node.node_key).ok;
  if (node.state === 'pending') return canStartNode(nodes, node.node_key).ok;
  return false;
}

export function gateBlockedReason(
  nodes: RequirementNodeProgress[],
  nodeKey: string,
): string | null {
  const gate = previousLaneGateOk(nodes, nodeKey);
  return gate.ok ? null : gate.reason === GATE_BLOCKED_REASON ? gate.reason : null;
}
