import { computed } from 'vue';
import { useAuthStore } from '@/stores/auth';

const TESTER_ROLE = 'tester';
const PRODUCT_ROLE = 'product';
const DEVELOPER_ROLE = 'developer';
const ADMIN_ROLE = 'project_admin';

export function usePermissions() {
  const auth = useAuthStore();

  const isSystemAdmin = computed(() => !!auth.user?.is_system_admin);

  function projectRoles(projectId: string | null | undefined): string[] {
    if (!projectId) return [];
    if (isSystemAdmin.value) return ['system_admin'];
    const p = auth.me?.projects.find((proj) => proj.id === projectId);
    if (!p) return [];
    const roles = [p.role];
    if (p.is_project_admin) roles.push('project_admin');
    return roles;
  }

  function hasProjectRole(projectId: string | null | undefined, role: string): boolean {
    return projectRoles(projectId).includes(role);
  }

  function hasAnyProjectRole(projectId: string | null | undefined, roles: string[]): boolean {
    const mine = projectRoles(projectId);
    return roles.some((r) => mine.includes(r));
  }

  function isProjectMember(projectId: string | null | undefined): boolean {
    return projectRoles(projectId).length > 0;
  }

  function isProjectAdmin(projectId: string | null | undefined): boolean {
    return isSystemAdmin.value || hasProjectRole(projectId, ADMIN_ROLE);
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

  function canManageProjectConfig(projectId: string | null | undefined): boolean {
    return isSystemAdmin.value || isProjectAdmin(projectId);
  }

  /** @deprecated use canManageProjectConfig */
  function canManageProjectMembers(projectId: string | null | undefined): boolean {
    return canManageProjectConfig(projectId);
  }

  /** 需求、版本、用例模块 */
  function canManageRequirements(projectId: string | null | undefined): boolean {
    return isSystemAdmin.value || isProjectMember(projectId);
  }

  /** @deprecated use canManageRequirements */
  function canManageCatalog(projectId: string | null | undefined): boolean {
    return canManageRequirements(projectId);
  }

  /** 测试用例 */
  function canManageCases(projectId: string | null | undefined): boolean {
    return isSystemAdmin.value || hasProjectRole(projectId, TESTER_ROLE);
  }

  /** 测试计划 */
  function canManagePlans(projectId: string | null | undefined): boolean {
    return canManageCases(projectId);
  }

  /** 缺陷新建、完整编辑、删除 */
  function canManageBugs(projectId: string | null | undefined): boolean {
    return (
      isSystemAdmin.value ||
      hasAnyProjectRole(projectId, [TESTER_ROLE, PRODUCT_ROLE])
    );
  }

  /** 缺陷改状态、评论 */
  function canChangeBugStatus(projectId: string | null | undefined): boolean {
    return (
      isSystemAdmin.value ||
      hasAnyProjectRole(projectId, [TESTER_ROLE, PRODUCT_ROLE, DEVELOPER_ROLE])
    );
  }

  /** 缺陷评论 */
  function canCommentBug(projectId: string | null | undefined): boolean {
    return canChangeBugStatus(projectId);
  }

  /** 缺陷跟进人（开发 / 测试 / 产品） */
  function canEditBugFollowers(projectId: string | null | undefined): boolean {
    return canChangeBugStatus(projectId);
  }

  function canAccessBugsModule(projectId: string | null | undefined): boolean {
    return (
      isSystemAdmin.value ||
      hasAnyProjectRole(projectId, [TESTER_ROLE, PRODUCT_ROLE, DEVELOPER_ROLE])
    );
  }

  function canAccessCasesModule(projectId: string | null | undefined): boolean {
    return isSystemAdmin.value || hasProjectRole(projectId, TESTER_ROLE);
  }

  return {
    isSystemAdmin,
    projectRoles,
    hasProjectRole,
    isProjectMember,
    isProjectAdmin,
    canCreateProject,
    canDeleteProject,
    canEditProject,
    canManageProjectConfig,
    canManageProjectMembers,
    canManageRequirements,
    canManageCatalog,
    canManageCases,
    canManagePlans,
    canManageBugs,
    canChangeBugStatus,
    canCommentBug,
    canEditBugFollowers,
    canAccessBugsModule,
    canAccessCasesModule,
  };
}
