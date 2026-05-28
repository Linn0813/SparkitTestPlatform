import type { RequirementNodeState, VersionNodeProgress, VersionWorkflowNodeDef } from '@/types/business';
import {
  columnNodesForLane,
  expandWorkflowCanvasNodes,
  type WorkflowCanvasNode,
  type WorkflowNodeSource,
} from '@/utils/requirementWorkflowLayout';

function buildLanesMap(defs: VersionWorkflowNodeDef[]): Map<number, VersionWorkflowNodeDef[]> {
  const byLane = new Map<number, VersionWorkflowNodeDef[]>();
  for (const d of defs) {
    const lanes = d.lane_indexes?.length ? d.lane_indexes : [d.lane_index];
    for (const lane of lanes) {
      if (!byLane.has(lane)) byLane.set(lane, []);
      const list = byLane.get(lane)!;
      if (!list.some((x) => x.node_key === d.node_key)) list.push(d);
    }
  }
  for (const [lane, nodes] of byLane) {
    byLane.set(lane, [...nodes].sort((a, b) => a.sort_in_lane - b.sort_in_lane));
  }
  return byLane;
}

function trackPredecessorFromMap(
  lanesMap: Map<number, VersionWorkflowNodeDef[]>,
  laneNum: number,
  sortInLane: number
): string | null {
  for (let i = laneNum - 1; i >= 0; i--) {
    const lane = lanesMap.get(i);
    if (!lane) continue;
    const match = lane.find((d) => d.sort_in_lane === sortInLane);
    if (match) return match.node_key;
  }
  for (let i = laneNum - 1; i >= 0; i--) {
    const lane = lanesMap.get(i);
    if (lane?.length === 1) return lane[0].node_key;
  }
  return null;
}

function livePrerequisitesFromMap(
  lanesMap: Map<number, VersionWorkflowNodeDef[]>,
  liveLane: number
): string[] {
  const tracks = new Set<number>();
  for (const laneNum of [...lanesMap.keys()].sort((a, b) => a - b)) {
    if (laneNum >= liveLane) break;
    for (const d of lanesMap.get(laneNum) ?? []) tracks.add(d.sort_in_lane);
  }
  const deps: string[] = [];
  for (const track of [...tracks].sort((a, b) => a - b)) {
    let terminal: string | null = null;
    for (const laneNum of [...lanesMap.keys()].filter((n) => n < liveLane).sort((a, b) => b - a)) {
      const found = lanesMap.get(laneNum)?.find((d) => d.sort_in_lane === track);
      if (found) {
        terminal = found.node_key;
        break;
      }
    }
    if (terminal) deps.push(terminal);
  }
  return deps;
}

export function buildVersionPrerequisites(defs: VersionWorkflowNodeDef[]): Record<string, string[]> {
  const lanesMap = buildLanesMap(defs);
  const liveDef = defs.find((d) => d.node_key === 'live');
  const liveLane = liveDef
    ? Math.min(...(liveDef.lane_indexes?.length ? liveDef.lane_indexes : [liveDef.lane_index]))
    : null;

  const prereqs: Record<string, string[]> = {};
  for (const d of defs) {
    if (d.node_key === 'live' && liveLane != null) {
      prereqs[d.node_key] = livePrerequisitesFromMap(lanesMap, liveLane);
      continue;
    }
    const minLane = Math.min(...(d.lane_indexes?.length ? d.lane_indexes : [d.lane_index]));
    const pred = trackPredecessorFromMap(lanesMap, minLane, d.sort_in_lane);
    prereqs[d.node_key] = pred ? [pred] : [];
  }
  return prereqs;
}

export function canCompleteVersionNode(
  nodeKey: string,
  nodes: VersionNodeProgress[],
  defs: VersionWorkflowNodeDef[]
): boolean {
  const node = nodes.find((n) => n.node_key === nodeKey);
  if (!node || node.state === 'completed') return false;
  const byKey = new Map(nodes.map((n) => [n.node_key, n.state]));
  const prereqs = buildVersionPrerequisites(defs);
  return (prereqs[nodeKey] ?? []).every((k) => byKey.get(k) === 'completed');
}

export function collectPrerequisiteConnectorPairs(
  nodes: WorkflowCanvasNode[],
  prereqs: Record<string, string[]>
): { from: string; to: string }[] {
  const renderKeyByNodeKey = new Map(nodes.map((n) => [n.node_key, n.render_key]));
  const pairs: { from: string; to: string }[] = [];
  const seen = new Set<string>();

  for (const [toKey, fromKeys] of Object.entries(prereqs)) {
    const toRender = renderKeyByNodeKey.get(toKey);
    if (!toRender) continue;
    for (const fromKey of fromKeys) {
      const fromRender = renderKeyByNodeKey.get(fromKey);
      if (!fromRender || fromRender === toRender) continue;
      const key = `${fromRender}->${toRender}`;
      if (seen.has(key)) continue;
      seen.add(key);
      pairs.push({ from: fromRender, to: toRender });
    }
  }
  return pairs;
}

export function collectVersionConnectorPairs(
  _nodes: WorkflowCanvasNode[],
  allLaneIndexes: number[],
  columnNodes: WorkflowCanvasNode[]
): { from: string; to: string }[] {
  const pairs: { from: string; to: string }[] = [];
  const seen = new Set<string>();

  function addPair(from: string, to: string) {
    const key = `${from}->${to}`;
    if (seen.has(key) || from === to) return;
    seen.add(key);
    pairs.push({ from, to });
  }

  for (let i = 0; i < allLaneIndexes.length - 1; i++) {
    const leftLane = allLaneIndexes[i];
    const rightLane = allLaneIndexes[i + 1];
    const sources = columnNodesForLane(leftLane, columnNodes);
    const targets = columnNodesForLane(rightLane, columnNodes);
    if (!sources.length || !targets.length) continue;

    const liveTarget = targets.find((t) => t.node_key === 'live');
    if (liveTarget && i === allLaneIndexes.length - 2) {
      const liveLaneIdx = allLaneIndexes.indexOf(rightLane);
      const tracks = new Set<number>();
      for (let j = 0; j < liveLaneIdx; j++) {
        for (const n of columnNodesForLane(allLaneIndexes[j], columnNodes)) {
          tracks.add(n.sort_in_lane);
        }
      }
      for (const track of [...tracks].sort((a, b) => a - b)) {
        let terminal: WorkflowCanvasNode | undefined;
        for (let j = liveLaneIdx - 1; j >= 0; j--) {
          const found = columnNodesForLane(allLaneIndexes[j], columnNodes).find(
            (n) => n.sort_in_lane === track
          );
          if (found) {
            terminal = found;
            break;
          }
        }
        if (terminal) addPair(terminal.render_key, liveTarget.render_key);
      }
      continue;
    }

    if (sources.length === 1) {
      for (const t of targets) addPair(sources[0].render_key, t.render_key);
    } else if (targets.length === 1) {
      for (const s of sources) addPair(s.render_key, targets[0].render_key);
    } else {
      for (const t of targets) {
        const match = sources.find((s) => s.sort_in_lane === t.sort_in_lane);
        if (match) addPair(match.render_key, t.render_key);
      }
    }
  }
  return pairs;
}

export function versionDefsToCanvasNodes(
  defs: VersionWorkflowNodeDef[],
  progress: VersionNodeProgress[]
): WorkflowCanvasNode[] {
  const stateByKey = new Map(progress.map((p) => [p.node_key, p.state]));
  const sources: WorkflowNodeSource[] = defs.map((d) => ({
    node_key: d.node_key,
    label: d.label,
    role_keys: [],
    lane_index: d.lane_index,
    lane_indexes: d.lane_indexes,
    blocks_lane_gate: true,
    sort_in_lane: d.sort_in_lane,
    enabled: true,
    state: (stateByKey.get(d.node_key) === 'completed' ? 'completed' : 'pending') as RequirementNodeState,
  }));
  return expandWorkflowCanvasNodes(sources);
}

export function formatVersionNodeSchedule(node: VersionNodeProgress): string {
  const start = node.scheduled_start?.slice(0, 10);
  const end = node.scheduled_end?.slice(0, 10);
  if (start && end) return `${start} ~ ${end}`;
  if (start) return `${start} 起`;
  if (end) return `至 ${end}`;
  return '';
}
