import type { TreeOption } from 'naive-ui';
import type { CaseModule } from '@/types/business';

export type ModuleTableRow = CaseModule & { children?: ModuleTableRow[] };

/** 模块路径分隔符：根模块-子模块-子模块 */
export const MODULE_PATH_SEP = '-';

export type ModuleDropPosition = 'before' | 'inside' | 'after';

/** 将各级模块名拼为路径 */
export function formatModulePath(parts: string[]): string {
  return parts.filter(Boolean).join(MODULE_PATH_SEP);
}

function sortModules(list: CaseModule[]) {
  return [...list].sort((a, b) => a.sort - b.sort || a.name.localeCompare(b.name, 'zh-CN'));
}

/** 上级模块名称 */
export function parentModuleLabel(modules: CaseModule[], parentId: string | null | undefined): string {
  if (!parentId) return '—';
  return modules.find((m) => m.id === parentId)?.name ?? '—';
}

/** 树形表格数据（与 buildModuleTree 同序） */
export function buildModuleTableTree(modules: CaseModule[]): ModuleTableRow[] {
  const byParent = new Map<string | null, CaseModule[]>();
  for (const m of modules) {
    const pid = m.parent_id ?? null;
    const bucket = byParent.get(pid);
    if (bucket) bucket.push(m);
    else byParent.set(pid, [m]);
  }
  for (const list of byParent.values()) {
    sortModules(list);
  }

  function walk(parentId: string | null): ModuleTableRow[] {
    return (byParent.get(parentId) ?? []).map((m) => {
      const children = walk(m.id);
      return children.length ? { ...m, children } : { ...m };
    });
  }
  return walk(null);
}

/** 树形表格默认展开：所有含子节点的模块 id */
export function collectModuleTableExpandKeys(rows: ModuleTableRow[]): string[] {
  const keys: string[] = [];
  for (const row of rows) {
    if (row.children?.length) {
      keys.push(row.id);
      keys.push(...collectModuleTableExpandKeys(row.children));
    }
  }
  return keys;
}

/** 将扁平模块列表转为 NTree 数据 */
export function buildModuleTree(modules: CaseModule[]): TreeOption[] {
  const byParent = new Map<string | null, CaseModule[]>();
  for (const m of modules) {
    const pid = m.parent_id ?? null;
    const bucket = byParent.get(pid);
    if (bucket) bucket.push(m);
    else byParent.set(pid, [m]);
  }
  for (const list of byParent.values()) {
    sortModules(list);
  }

  function walk(parentId: string | null): TreeOption[] {
    return (byParent.get(parentId) ?? []).map((m) => {
      const children = walk(m.id);
      return {
        key: m.id,
        id: m.id,
        label: m.name,
        name: m.name,
        ...(children.length ? { children } : {}),
      };
    });
  }
  return walk(null);
}

/** 下拉选项：完整路径「模块-子模块-子模块」 */
export function moduleSelectOptions(modules: CaseModule[]): { label: string; value: string }[] {
  const out: { label: string; value: string }[] = [];

  function walk(nodes: TreeOption[]) {
    for (const n of nodes) {
      const id = String(n.key);
      out.push({ label: modulePathLabel(modules, id), value: id });
      if (n.children?.length) walk(n.children as TreeOption[]);
    }
  }
  walk(buildModuleTree(modules));
  return out;
}

/** 模块层级路径，如「登录-账号密码」 */
export function modulePathLabel(modules: CaseModule[], moduleId: string): string {
  const byId = new Map(modules.map((m) => [m.id, m]));
  const parts: string[] = [];
  let cur: string | null = moduleId;
  const seen = new Set<string>();
  while (cur && !seen.has(cur)) {
    seen.add(cur);
    const mod = byId.get(cur);
    if (!mod) break;
    parts.unshift(mod.name);
    cur = mod.parent_id ?? null;
  }
  return formatModulePath(parts);
}

/** 收集某模块的全部子孙 id（用于禁止把父级设到自己子树下） */
export function collectDescendantIds(modules: CaseModule[], rootId: string): Set<string> {
  const ids = new Set<string>();
  function walk(parentId: string) {
    for (const m of modules) {
      if (m.parent_id === parentId) {
        ids.add(m.id);
        walk(m.id);
      }
    }
  }
  walk(rootId);
  return ids;
}

function siblingsOf(modules: CaseModule[], parentId: string | null, excludeId?: string): CaseModule[] {
  return sortModules(
    modules.filter((m) => (m.parent_id ?? null) === parentId && m.id !== excludeId)
  );
}

/** 是否允许拖拽落点 */
export function allowModuleDrop(
  modules: CaseModule[],
  dragId: string,
  targetId: string,
  dropPosition: ModuleDropPosition
): boolean {
  if (dragId === targetId) return false;
  const descendants = collectDescendantIds(modules, dragId);
  if (descendants.has(targetId)) return false;
  const target = modules.find((m) => m.id === targetId);
  if (!target) return false;
  if (dropPosition === 'inside') return true;
  return true;
}

export interface ModuleSortUpdate {
  id: string;
  parent_id: string | null;
  sort: number;
}

/** 根据落点计算需 PATCH 的 parent_id / sort（含同级重排） */
export function resolveModuleDropUpdates(
  modules: CaseModule[],
  dragId: string,
  targetId: string,
  dropPosition: ModuleDropPosition
): ModuleSortUpdate[] {
  const dragMod = modules.find((m) => m.id === dragId);
  const targetMod = modules.find((m) => m.id === targetId);
  if (!dragMod || !targetMod) return [];

  const updates: ModuleSortUpdate[] = [];

  if (dropPosition === 'inside') {
    const parentId = targetId;
    const children = siblingsOf(modules, parentId, dragId);
    const sort = children.length;
    for (let i = 0; i < children.length; i++) {
      updates.push({ id: children[i].id, parent_id: parentId, sort: i });
    }
    updates.push({ id: dragId, parent_id: parentId, sort });
    return updates;
  }

  const parentId = targetMod.parent_id ?? null;
  const siblings = siblingsOf(modules, parentId, dragId);
  const targetIndex = siblings.findIndex((m) => m.id === targetId);
  const insertIndex = dropPosition === 'before' ? targetIndex : targetIndex + 1;
  const reordered = [...siblings];
  reordered.splice(insertIndex, 0, dragMod);

  for (let i = 0; i < reordered.length; i++) {
    updates.push({
      id: reordered[i].id,
      parent_id: parentId,
      sort: i,
    });
  }
  return updates;
}
