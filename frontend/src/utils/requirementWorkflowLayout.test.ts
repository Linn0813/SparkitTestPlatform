import { describe, expect, it } from 'vitest';
import {
  expandWorkflowCanvasNodes,
  layoutRowCount,
  layoutRowCountForLane,
  rowIndexInLane,
  rowTopForLayoutGrid,
  type WorkflowNodeSource,
} from './requirementWorkflowLayout';

function source(
  node_key: string,
  lane_index: number,
  sort_in_lane: number,
  lane_indexes?: number[],
): WorkflowNodeSource {
  return {
    node_key,
    label: node_key,
    role_keys: [],
    lane_index,
    lane_indexes,
    sort_in_lane,
    enabled: true,
    state: 'pending',
  };
}

describe('layoutRowCountForLane', () => {
  it('uses single row for a lone column node even when sort_in_lane is non-zero', () => {
    const nodes = expandWorkflowCanvasNodes([
      source('tech_doc', 0, 2),
      source('fe', 1, 0),
      source('be', 1, 1),
      source('qa', 1, 2),
      source('integration', 2, 0),
    ]);
    const columnNodes = nodes.filter((n) => !n.is_span_positioned);

    expect(layoutRowCount(nodes)).toBe(3);
    expect(layoutRowCountForLane(0, nodes, columnNodes)).toBe(1);
    expect(layoutRowCountForLane(1, nodes, columnNodes)).toBe(3);
    expect(layoutRowCountForLane(2, nodes, columnNodes)).toBe(1);
  });
});

describe('rowIndexInLane', () => {
  it('returns 0 for a single-node column regardless of sort_in_lane', () => {
    const nodes = expandWorkflowCanvasNodes([
      source('tech_doc', 0, 2),
      source('fe', 1, 0),
      source('be', 1, 1),
      source('qa', 1, 2),
    ]);
    const columnNodes = nodes.filter((n) => !n.is_span_positioned);
    const single = columnNodes.find((n) => n.node_key === 'tech_doc')!;

    expect(rowIndexInLane(single, columnNodes)).toBe(0);
  });

  it('keeps sort_in_lane for multi-node columns', () => {
    const nodes = expandWorkflowCanvasNodes([
      source('fe', 1, 0),
      source('be', 1, 1),
      source('qa', 1, 2),
    ]);
    const columnNodes = nodes.filter((n) => !n.is_span_positioned);
    const qa = columnNodes.find((n) => n.node_key === 'qa')!;

    expect(rowIndexInLane(qa, columnNodes)).toBe(2);
  });
});

describe('rowTopForLayoutGrid', () => {
  it('centers a single row within the lane', () => {
    const nodeHeight = 52;
    const laneHeight = 176;
    const top = rowTopForLayoutGrid(0, nodeHeight, laneHeight, 1);

    expect(top).toBe((laneHeight - nodeHeight) / 2);
  });
});
