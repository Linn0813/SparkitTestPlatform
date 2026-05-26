import type { WorkflowNodeSource } from '@/utils/requirementWorkflowLayout';

/**
 * 按已选角色同步节点启用：与已选角色无交集则自动禁用；有交集时保留用户在 enabledDraft 中的选择。
 */
export function syncEnabledDraftWithSelectedRoles(
  workflowNodes: WorkflowNodeSource[],
  selectedRoles: string[],
  enabledDraft: Record<string, boolean>
): Record<string, boolean> {
  const selected = new Set(selectedRoles);
  const next: Record<string, boolean> = { ...enabledDraft };

  for (const node of workflowNodes) {
    const roleKeys = node.role_keys;
    if (!roleKeys.length) continue;

    const current = enabledDraft[node.node_key] ?? node.enabled;

    if (!roleKeys.some((rk) => selected.has(rk))) {
      next[node.node_key] = false;
      continue;
    }

    next[node.node_key] = current;
  }

  return next;
}

/** 保存前生成完整 enabled 映射（覆盖所有节点 key） */
export function buildFullEnabledMap(
  workflowNodes: WorkflowNodeSource[],
  selectedRoles: string[],
  enabledDraft: Record<string, boolean>
): Record<string, boolean> {
  const synced = syncEnabledDraftWithSelectedRoles(workflowNodes, selectedRoles, enabledDraft);
  const out: Record<string, boolean> = {};
  for (const node of workflowNodes) {
    out[node.node_key] = synced[node.node_key] ?? node.enabled;
  }
  return out;
}
