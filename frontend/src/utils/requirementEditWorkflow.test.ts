import { describe, expect, it } from 'vitest';
import type { WorkflowNodeSource } from '@/utils/requirementWorkflowLayout';
import { buildFullEnabledMap, syncEnabledDraftWithSelectedRoles } from './requirementEditWorkflow';

function node(
  node_key: string,
  role_keys: string[],
  enabled = true
): WorkflowNodeSource {
  return {
    node_key,
    label: node_key,
    role_keys,
    lane_index: 0,
    sort_in_lane: 0,
    enabled,
    state: 'pending',
  };
}

describe('syncEnabledDraftWithSelectedRoles', () => {
  const workflowNodes = [
    node('prd_output', ['pm']),
    node('req_design', ['pm', 'designer']),
    node('case_design', ['qa']),
  ];

  it('keeps prd_output disabled when pm is selected but user turned it off', () => {
    const result = syncEnabledDraftWithSelectedRoles(workflowNodes, ['pm'], {
      prd_output: false,
      req_design: true,
    });
    expect(result.prd_output).toBe(false);
  });

  it('disables nodes whose roles do not overlap with selection', () => {
    const result = syncEnabledDraftWithSelectedRoles(workflowNodes, ['pm'], {
      case_design: true,
    });
    expect(result.case_design).toBe(false);
  });

  it('does not force-enable when all node roles are selected', () => {
    const result = syncEnabledDraftWithSelectedRoles(workflowNodes, ['pm', 'designer'], {
      req_design: false,
    });
    expect(result.req_design).toBe(false);
  });
});

describe('buildFullEnabledMap', () => {
  it('persists manual prd_output off through save payload', () => {
    const workflowNodes = [node('prd_output', ['pm']), node('case_design', ['qa'])];
    const payload = buildFullEnabledMap(workflowNodes, ['pm'], { prd_output: false });
    expect(payload.prd_output).toBe(false);
    expect(payload.case_design).toBe(false);
  });
});
