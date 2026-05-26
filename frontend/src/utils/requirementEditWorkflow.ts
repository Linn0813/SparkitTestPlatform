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

/** 勾选角色时：凡节点 role_keys 含任一给定角色，则启用该节点。 */
export function applyRolesChecked(
  workflowNodes: WorkflowNodeSource[],
  enabledDraft: Record<string, boolean>,
  roleKeys: string[]
): Record<string, boolean> {
  const checked = new Set(roleKeys);
  if (!checked.size) return { ...enabledDraft };

  const next: Record<string, boolean> = { ...enabledDraft };
  for (const node of workflowNodes) {
    if (!node.role_keys.some((rk) => checked.has(rk))) continue;
    next[node.node_key] = true;
  }
  return next;
}

/** 启用节点时：把该节点关联角色并入已选角色（去重）。 */
export function mergeRolesForEnabledNode(
  node: WorkflowNodeSource,
  selectedRoles: string[]
): string[] {
  const merged = new Set(selectedRoles);
  for (const rk of node.role_keys) {
    if (rk) merged.add(rk);
  }
  return [...merged];
}

/** 负责人表单项：与角色勾选一致，不依赖节点是否启用。 */
export function assigneeFieldsForSelectedRoles(
  projectRoles: { key: string; label: string }[],
  selectedRoles: string[]
): { key: string; label: string }[] {
  const selected = new Set(selectedRoles);
  return projectRoles.filter((r) => selected.has(r.key));
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
