/** 项目成员角色（与后端 ProjectRole / BusinessProjectRole 枚举值一致） */
export type ProjectRoleValue =
  | 'project_admin'
  | 'member'
  | 'tester'
  | 'product'
  | 'developer';

/** 可选业务职能（不含 member；member 表示普通项目成员/非管理员默认身份） */
export type SpecialtyBusinessRoleValue = Exclude<ProjectRoleValue, 'project_admin' | 'member'>;

export const PROJECT_ROLE_LABELS: Record<ProjectRoleValue, string> = {
  project_admin: '管理员',
  member: '项目成员',
  tester: '测试',
  product: '产品',
  developer: '开发',
};

/** 弹窗中可选的业务职能（测试/产品/开发）；不选则为普通项目成员 */
export const SPECIALTY_ROLE_OPTIONS = (
  ['tester', 'product', 'developer'] as SpecialtyBusinessRoleValue[]
).map((value) => ({ label: PROJECT_ROLE_LABELS[value], value }));

/** @deprecated 使用 SPECIALTY_ROLE_OPTIONS */
export const BUSINESS_ROLE_OPTIONS = SPECIALTY_ROLE_OPTIONS;
export const PROJECT_ROLE_OPTIONS = SPECIALTY_ROLE_OPTIONS;

export function projectRoleLabel(role: string): string {
  if (role === 'viewer') return PROJECT_ROLE_LABELS.member;
  if (role === 'system_admin') return '系统管理员';
  return PROJECT_ROLE_LABELS[role as ProjectRoleValue] ?? role;
}

/** 列表「角色」列：member 且非管理员 → 项目成员；member 且是管理员 → —；否则显示职能 */
export function memberRoleDisplay(row: { role: string; is_project_admin: boolean }): string {
  if (row.role !== 'member') return projectRoleLabel(row.role);
  if (!row.is_project_admin) return PROJECT_ROLE_LABELS.member;
  return '—';
}

/** 表单：后端 member → null（未指定职能） */
export function specialtyRoleFromMember(role: string): SpecialtyBusinessRoleValue | null {
  if (role === 'tester' || role === 'product' || role === 'developer') return role;
  return null;
}

/** 表单：null → 后端 member */
export function memberRoleFromSpecialty(role: SpecialtyBusinessRoleValue | null): string {
  return role ?? 'member';
}
