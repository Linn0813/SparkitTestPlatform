import { computed } from 'vue';
import { useAuthStore } from '@/stores/auth';

const CATALOG_ROLES = new Set(['member', 'tester', 'project_admin', 'system_admin']);
const TESTER_ROLES = new Set(['tester', 'project_admin', 'system_admin']);

export function usePermissions() {
  const auth = useAuthStore();

  const isSystemAdmin = computed(() => !!auth.user?.is_system_admin);

  function projectRole(projectId: string | null | undefined): string | undefined {
    if (!projectId) return undefined;
    if (isSystemAdmin.value) return 'system_admin';
    return auth.me?.projects.find((p) => p.id === projectId)?.role;
  }

  function hasRole(projectId: string | null | undefined, allowed: Set<string>): boolean {
    if (!projectId) return false;
    const role = projectRole(projectId);
    return role ? allowed.has(role) : false;
  }

  function isProjectAdmin(projectId: string | null | undefined): boolean {
    return hasRole(projectId, new Set(['project_admin', 'system_admin']));
  }

  function canCreateProject(): boolean {
    return isSystemAdmin.value;
  }

  function canDeleteProject(): boolean {
    return isSystemAdmin.value;
  }

  function canEditProject(projectId: string): boolean {
    return isSystemAdmin.value || isProjectAdmin(projectId);
  }

  function canManageProjectMembers(projectId: string | null | undefined): boolean {
    return isSystemAdmin.value || isProjectAdmin(projectId);
  }

  /** 需求、版本、用例模块 */
  function canManageCatalog(projectId: string | null | undefined): boolean {
    return hasRole(projectId, CATALOG_ROLES);
  }

  /** 测试用例 */
  function canManageCases(projectId: string | null | undefined): boolean {
    return hasRole(projectId, TESTER_ROLES);
  }

  /** 测试计划 */
  function canManagePlans(projectId: string | null | undefined): boolean {
    return hasRole(projectId, TESTER_ROLES);
  }

  /** 缺陷新建、完整编辑、删除 */
  function canManageBugs(projectId: string | null | undefined): boolean {
    return hasRole(projectId, TESTER_ROLES);
  }

  /** 缺陷改状态 */
  function canChangeBugStatus(projectId: string | null | undefined): boolean {
    if (!projectId) return false;
    return !!projectRole(projectId);
  }

  /** 缺陷评论 */
  function canCommentBug(projectId: string | null | undefined): boolean {
    return canChangeBugStatus(projectId);
  }

  return {
    isSystemAdmin,
    projectRole,
    isProjectAdmin,
    canCreateProject,
    canDeleteProject,
    canEditProject,
    canManageProjectMembers,
    canManageCatalog,
    canManageCases,
    canManagePlans,
    canManageBugs,
    canChangeBugStatus,
    canCommentBug,
  };
}
