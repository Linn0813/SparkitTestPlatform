/** 项目成员角色（与后端 ProjectRole 枚举值一致） */
export type ProjectRoleValue = 'project_admin' | 'tester' | 'member';

export const PROJECT_ROLE_LABELS: Record<ProjectRoleValue, string> = {
  project_admin: '管理员',
  tester: '测试',
  member: '项目成员',
};

export const PROJECT_ROLE_OPTIONS = [
  {
    label: PROJECT_ROLE_LABELS.project_admin,
    value: 'project_admin' as const,
  },
  {
    label: PROJECT_ROLE_LABELS.tester,
    value: 'tester' as const,
  },
  {
    label: PROJECT_ROLE_LABELS.member,
    value: 'member' as const,
  },
];

export function projectRoleLabel(role: string): string {
  if (role === 'viewer') return PROJECT_ROLE_LABELS.member;
  return PROJECT_ROLE_LABELS[role as ProjectRoleValue] ?? role;
}
