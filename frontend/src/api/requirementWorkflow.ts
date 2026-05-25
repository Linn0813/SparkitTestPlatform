import http from './http';
import type {
  RequirementWorkflowNodeDef,
  RequirementWorkflowOut,
} from '@/types/business';

export function listRequirementWorkflowNodes(projectId: string) {
  return http.get<RequirementWorkflowNodeDef[]>(`/projects/${projectId}/requirement-workflow-nodes`);
}

export function createRequirementWorkflowNode(
  projectId: string,
  data: {
    label: string;
    role_keys: string[];
    lane_indexes: number[];
    blocks_lane_gate?: boolean;
    sort_in_lane?: number;
  }
) {
  return http.post<RequirementWorkflowNodeDef>(`/projects/${projectId}/requirement-workflow-nodes`, data);
}

export function updateRequirementWorkflowNode(
  projectId: string,
  defId: string,
  data: Partial<{
    label: string;
    role_keys: string[];
    lane_indexes: number[];
    blocks_lane_gate: boolean;
    sort_in_lane: number;
  }>
) {
  return http.patch<RequirementWorkflowNodeDef>(
    `/projects/${projectId}/requirement-workflow-nodes/${defId}`,
    data
  );
}

export function deleteRequirementWorkflowNode(projectId: string, defId: string) {
  return http.delete(`/projects/${projectId}/requirement-workflow-nodes/${defId}`);
}

export function reorderRequirementWorkflowNodes(
  projectId: string,
  items: { id: string; lane_index: number; sort_in_lane: number }[]
) {
  return http.put<RequirementWorkflowNodeDef[]>(
    `/projects/${projectId}/requirement-workflow-nodes/reorder`,
    { items }
  );
}

export function getRequirementWorkflow(requirementId: string) {
  return http.get<RequirementWorkflowOut>(`/requirements/${requirementId}/workflow`);
}

export function updateRequirementWorkflowEnabled(requirementId: string, enabled: Record<string, boolean>) {
  return http.put<RequirementWorkflowOut>(`/requirements/${requirementId}/workflow`, { enabled });
}
