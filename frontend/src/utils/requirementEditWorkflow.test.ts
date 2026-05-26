import { describe, expect, it } from 'vitest';
import type { WorkflowNodeSource } from '@/utils/requirementWorkflowLayout';
import {
  applyRolesChecked,
  assigneeFieldsForSelectedRoles,
  buildFullEnabledMap,
  mergeRolesForEnabledNode,
  syncEnabledDraftWithSelectedRoles,
} from './requirementEditWorkflow';

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

describe('applyRolesChecked', () => {
  const workflowNodes = [
    node('prd_output', ['pm']),
    node('req_design', ['pm', 'designer']),
    node('case_design', ['qa']),
  ];

  it('enables all nodes containing the checked role', () => {
    const result = applyRolesChecked(workflowNodes, { prd_output: false, case_design: false }, ['pm']);
    expect(result.prd_output).toBe(true);
    expect(result.req_design).toBe(true);
    expect(result.case_design).toBe(false);
  });
});

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

  it('keeps req_design disabled when pm+designer selected but user turned it off', () => {
    const result = syncEnabledDraftWithSelectedRoles(workflowNodes, ['pm', 'designer'], {
      req_design: false,
    });
    expect(result.req_design).toBe(false);
  });

  it('disables pm-only nodes when pm is unchecked but designer remains', () => {
    const result = syncEnabledDraftWithSelectedRoles(workflowNodes, ['designer'], {
      prd_output: true,
      req_design: true,
    });
    expect(result.prd_output).toBe(false);
    expect(result.req_design).toBe(true);
  });
});

describe('mergeRolesForEnabledNode', () => {
  it('adds node roles without removing existing selection', () => {
    const n = node('prd_output', ['pm']);
    expect(mergeRolesForEnabledNode(n, ['qa'])).toEqual(['qa', 'pm']);
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

describe('assigneeFieldsForSelectedRoles', () => {
  const projectRoles = [
    { key: 'pm', label: 'PM' },
    { key: 'qa', label: '测试' },
    { key: 'designer', label: '设计' },
  ];

  it('returns fields for all selected roles regardless of node enabled state', () => {
    const fields = assigneeFieldsForSelectedRoles(projectRoles, ['pm', 'qa']);
    expect(fields.map((r) => r.key)).toEqual(['pm', 'qa']);
  });

  it('returns empty when no roles selected', () => {
    expect(assigneeFieldsForSelectedRoles(projectRoles, [])).toEqual([]);
  });
});

describe('role selection independent of all nodes off', () => {
  it('sync does not change selectedRoles (caller keeps roles)', () => {
    const selectedRoles = ['pm'];
    const draft = syncEnabledDraftWithSelectedRoles(
      [node('prd_output', ['pm']), node('req_design', ['pm'])],
      selectedRoles,
      { prd_output: false, req_design: false }
    );
    expect(draft.prd_output).toBe(false);
    expect(draft.req_design).toBe(false);
    expect(selectedRoles).toEqual(['pm']);
  });
});
