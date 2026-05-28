import http from './http';
import type { VersionType, VersionWorkflowNodeDef } from '@/types/business';

export function listVersionWorkflowNodes(projectId: string, versionType: VersionType) {
  return http.get<VersionWorkflowNodeDef[]>(
    `/projects/${projectId}/version-workflow-nodes`,
    { params: { version_type: versionType } }
  );
}

export function createVersionWorkflowNode(
  projectId: string,
  versionType: VersionType,
  data: {
    node_key: string;
    label: string;
    lane_indexes: number[];
    sort_in_lane?: number;
  }
) {
  return http.post<VersionWorkflowNodeDef>(
    `/projects/${projectId}/version-workflow-nodes`,
    data,
    { params: { version_type: versionType } }
  );
}

export function updateVersionWorkflowNode(
  projectId: string,
  defId: string,
  data: Partial<{
    label: string;
    lane_indexes: number[];
    sort_in_lane: number;
  }>
) {
  return http.patch<VersionWorkflowNodeDef>(
    `/projects/${projectId}/version-workflow-nodes/${defId}`,
    data
  );
}

export function deleteVersionWorkflowNode(projectId: string, defId: string) {
  return http.delete(`/projects/${projectId}/version-workflow-nodes/${defId}`);
}

export function reorderVersionWorkflowNodes(
  projectId: string,
  versionType: VersionType,
  items: { id: string; lane_index: number; sort_in_lane: number }[]
) {
  return http.put<VersionWorkflowNodeDef[]>(
    `/projects/${projectId}/version-workflow-nodes/reorder`,
    { items },
    { params: { version_type: versionType } }
  );
}
