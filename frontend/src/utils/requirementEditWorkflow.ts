import type { WorkflowNodeSource } from '@/utils/requirementWorkflowLayout';

/**
 * 按已选角色同步节点启用：无交集则禁用；节点所需角色全部选中则启用；否则保持当前值。
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

    if (roleKeys.every((rk) => selected.has(rk))) {
      next[node.node_key] = true;
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
