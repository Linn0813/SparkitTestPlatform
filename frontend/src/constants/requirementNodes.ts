export const REQUIREMENT_ROLE_FIELDS = [
  { key: 'frontend_rd', label: '前端RD', idField: 'frontend_rd_id' as const },
  { key: 'backend_rd', label: '后端RD', idField: 'backend_rd_id' as const },
  { key: 'pm', label: 'PM', idField: 'pm_id' as const },
  { key: 'tech_owner', label: '技术Owner', idField: 'tech_owner_id' as const },
  { key: 'qa', label: '测试QA', idField: 'qa_id' as const },
  { key: 'designer', label: '设计', idField: 'designer_id' as const },
] as const;

export const LEGACY_ROLE_ID_FIELDS: Record<string, string> = {
  frontend_rd: 'frontend_rd_id',
  backend_rd: 'backend_rd_id',
  pm: 'pm_id',
  tech_owner: 'tech_owner_id',
  qa: 'qa_id',
  designer: 'designer_id',
};

export const REQUIREMENT_NODE_KEYS = [
  'prd_output',
  'req_design',
  'req_review',
  'frontend_dev',
  'backend_dev',
  'integration',
  'req_test',
  'product_experience',
  'ui_restoration',
  'released',
] as const;

export type RequirementNodeKey = (typeof REQUIREMENT_NODE_KEYS)[number];

export const REQUIREMENT_NODE_LABELS: Record<RequirementNodeKey, string> = {
  prd_output: 'PRD输出',
  req_design: '需求设计',
  req_review: '需求评审',
  frontend_dev: '前端开发',
  backend_dev: '后端开发',
  integration: '联调',
  req_test: '需求测试',
  product_experience: '产品体验',
  ui_restoration: 'UI还原',
  released: '已发版',
};

export const REQUIREMENT_NODE_PHASES: RequirementNodeKey[][] = [
  ['prd_output', 'req_design'],
  ['req_review'],
  ['frontend_dev', 'backend_dev'],
  ['integration'],
  ['req_test', 'product_experience', 'ui_restoration'],
  ['released'],
];

/** 技术优化类需求默认不启用的节点（与后端 TECH_OPTIMIZATION_DEFAULT_DISABLED_NODES 一致） */
export const TECH_OPTIMIZATION_DEFAULT_DISABLED_NODES = new Set<RequirementNodeKey>([
  'product_experience',
  'ui_restoration',
  'req_design',
]);

export function defaultWorkflowNodeEnabled(nodeKey: string, reqType: string): boolean {
  if (reqType === 'tech_optimization' && TECH_OPTIMIZATION_DEFAULT_DISABLED_NODES.has(nodeKey as RequirementNodeKey)) {
    return false;
  }
  return true;
}

export const REQUIREMENT_NODE_ROLE_KEYS: Record<RequirementNodeKey, string[]> = {
  prd_output: ['pm'],
  req_design: ['pm'],
  req_review: ['tech_owner'],
  frontend_dev: ['frontend_rd'],
  backend_dev: ['backend_rd'],
  integration: ['frontend_rd', 'backend_rd'],
  req_test: ['qa'],
  product_experience: ['pm'],
  ui_restoration: ['designer'],
  released: ['pm'],
};

export const NODE_STATE_LABELS: Record<string, string> = {
  pending: '未开始',
  in_progress: '进行中',
  completed: '已完成',
  skipped: '已跳过',
};

export function requirementNodeLabel(key: string): string {
  return REQUIREMENT_NODE_LABELS[key as RequirementNodeKey] ?? key;
}

export function requirementRoleLabel(key: string): string {
  return REQUIREMENT_ROLE_FIELDS.find((r) => r.key === key)?.label ?? key;
}

export function requirementRoleLabels(keys: string[]): string {
  return keys.map(requirementRoleLabel).join('、');
}
