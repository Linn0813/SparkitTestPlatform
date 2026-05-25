import { fieldTypeLabel, sortTemplateFields } from '@/constants/fieldTypes';
import type { TemplateField } from '@/types/business';

export type FieldConfigSource = 'system' | 'template';

export type RequirementOptionCategory = 'priority' | 'req_type';

export interface FieldConfigRow {
  id: string;
  name: string;
  type: string;
  typeLabel: string;
  required: boolean;
  source: FieldConfigSource;
  sort: number;
  optionCategory?: RequirementOptionCategory;
}

const SYSTEM_CASE_FIELDS: FieldConfigRow[] = [
  { id: '__title', name: '用例标题', type: 'text', typeLabel: '文本', required: true, source: 'system', sort: 0 },
  { id: '__module', name: '模块', type: 'module', typeLabel: '模块', required: true, source: 'system', sort: 1 },
  { id: '__priority', name: '优先级', type: 'select', typeLabel: '单选', required: false, source: 'system', sort: 2 },
  { id: '__precondition', name: '前置条件', type: 'text', typeLabel: '文本', required: false, source: 'system', sort: 3 },
  { id: '__step_text', name: '步骤', type: 'text', typeLabel: '文本', required: false, source: 'system', sort: 4 },
  { id: '__expected_result', name: '预期结果', type: 'text', typeLabel: '文本', required: false, source: 'system', sort: 5 },
  { id: '__requirements', name: '关联需求', type: 'requirement_link', typeLabel: '关联', required: false, source: 'system', sort: 6 },
];

const SYSTEM_BUG_FIELDS: FieldConfigRow[] = [
  { id: '__title', name: '缺陷标题', type: 'text', typeLabel: '文本', required: true, source: 'system', sort: 0 },
  { id: '__status', name: '状态', type: 'status', typeLabel: '单选', required: true, source: 'system', sort: 1 },
  { id: '__reporter', name: '提出人', type: 'member', typeLabel: '人员', required: true, source: 'system', sort: 2 },
  { id: '__followers', name: '跟进人', type: 'member_multi', typeLabel: '人员', required: false, source: 'system', sort: 3 },
  { id: '__description', name: '描述', type: 'text', typeLabel: '文本', required: false, source: 'system', sort: 4 },
  { id: '__attachments', name: '附件', type: 'attachment', typeLabel: '附件', required: false, source: 'system', sort: 5 },
  { id: '__requirements', name: '关联需求', type: 'requirement_link', typeLabel: '关联', required: false, source: 'system', sort: 6 },
  { id: '__plans', name: '关联测试计划', type: 'plan_link', typeLabel: '关联', required: false, source: 'system', sort: 7 },
  { id: '__plan_version', name: '规划迭代', type: 'version_link', typeLabel: '版本', required: false, source: 'system', sort: 8 },
  { id: '__found_version', name: '发现版本', type: 'version_link', typeLabel: '版本', required: false, source: 'system', sort: 9 },
];

const SYSTEM_REQUIREMENT_FIELDS: FieldConfigRow[] = [
  { id: '__title', name: '需求标题', type: 'text', typeLabel: '文本', required: true, source: 'system', sort: 0 },
  { id: '__priority', name: '优先级', type: 'select', typeLabel: '单选', required: false, source: 'system', sort: 1, optionCategory: 'priority' },
  { id: '__req_type', name: '需求类型', type: 'select', typeLabel: '单选', required: false, source: 'system', sort: 2, optionCategory: 'req_type' },
  { id: '__external_url', name: 'PRD 链接', type: 'text', typeLabel: '文本', required: false, source: 'system', sort: 3 },
  { id: '__version', name: '关联版本', type: 'version_link', typeLabel: '版本', required: false, source: 'system', sort: 4 },
];

export function buildFieldConfigRows(
  scene: 'case' | 'bug' | 'requirement',
  templateFields: TemplateField[]
): FieldConfigRow[] {
  const system =
    scene === 'case'
      ? SYSTEM_CASE_FIELDS
      : scene === 'bug'
        ? SYSTEM_BUG_FIELDS
        : SYSTEM_REQUIREMENT_FIELDS;
  const custom = sortTemplateFields(templateFields).map((f, i) => ({
    id: f.id,
    name: f.name,
    type: f.type,
    typeLabel: fieldTypeLabel(f.type),
    required: f.required,
    source: 'template' as const,
    sort: system.length + i,
  }));
  return [...system, ...custom];
}

export function isSystemFieldRow(row: FieldConfigRow): boolean {
  return row.source === 'system';
}
