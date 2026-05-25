import type { DataTableColumns } from 'naive-ui';
import type { BugListFilterState } from '@/composables/useBugListFilters';
import type { CaseListFilterState } from '@/composables/useCaseListFilters';
import {
  fieldTypeLabel,
  isMemberType,
  isOptionFieldType,
  isRichtextType,
  normalizeRichTextValue,
  sortTemplateFields,
} from '@/constants/fieldTypes';
import type { TemplateField } from '@/types/business';

export type EntityScene = 'bug' | 'functional_case' | 'requirement';

/** 与后端 bug_filters.FILTER_EMPTY 一致 */
export const FILTER_EMPTY_VALUE = '__empty__';

export const FILTER_EMPTY_OPTION = { label: '（空）', value: FILTER_EMPTY_VALUE };

export type FieldCatalogKind = 'system' | 'template';

export interface FieldCatalogItem {
  key: string;
  label: string;
  kind: FieldCatalogKind;
  fieldId?: string;
  field?: TemplateField;
}

export interface TemplateFieldFormatContext {
  memberLabel?: (userId: string) => string;
}

/** 保存模板时禁止与系统字段重名（与后端 RESERVED_FIELD_NAMES_BY_SCENE 对齐） */
export const RESERVED_TEMPLATE_FIELD_NAMES: Record<EntityScene, readonly string[]> = {
  bug: [
    '缺陷标题',
    '标题',
    '状态',
    '提出人',
    '跟进人',
    '描述',
    '附件',
    '关联需求',
    '关联测试计划',
    '规划迭代',
    '发现版本',
    '关联计划',
  ],
  functional_case: [
    '用例标题',
    '标题',
    '模块',
    '优先级',
    '前置条件',
    '步骤',
    '预期结果',
    '关联需求',
  ],
  requirement: [
    '需求标题',
    '标题',
    '优先级',
    '需求类型',
    'PRD',
    'PRD 链接',
    '关联版本',
    '版本上线时间',
  ],
};

const BUG_FILTER_SYSTEM_DEFS: FieldCatalogItem[] = [
  { key: 'q', label: '标题', kind: 'system' },
  { key: 'status', label: '状态', kind: 'system' },
  { key: 'reporter', label: '提出人', kind: 'system' },
  { key: 'follower', label: '跟进人', kind: 'system' },
  { key: 'plan_version', label: '规划迭代', kind: 'system' },
  { key: 'found_version', label: '发现版本', kind: 'system' },
  { key: 'requirement', label: '关联需求', kind: 'system' },
  { key: 'plan', label: '关联计划', kind: 'system' },
];

const BUG_DEDUPE_LABELS = new Set(BUG_FILTER_SYSTEM_DEFS.map((d) => d.label));

const CASE_DEDUPE_LABELS = new Set([
  '用例标题',
  '标题',
  '模块',
  '优先级',
  '前置条件',
  '步骤',
  '预期结果',
  '关联需求',
]);

export const DEFAULT_BUG_FILTER_VISIBLE_KEYS = ['q'];

const CASE_FILTER_SYSTEM_DEFS: FieldCatalogItem[] = [
  { key: 'module', label: '模块', kind: 'system' },
  { key: 'q', label: '标题', kind: 'system' },
  { key: 'priority', label: '优先级', kind: 'system' },
  { key: 'requirement', label: '关联需求', kind: 'system' },
];

export const DEFAULT_CASE_FILTER_VISIBLE_KEYS = ['module', 'q'];

export const CASE_PRIORITY_FILTER_OPTIONS = ['P0', 'P1', 'P2', 'P3'].map((v) => ({
  label: v,
  value: v,
}));

const FILTERABLE_TEMPLATE_TYPES = new Set([
  'select',
  'multi_select',
  'member',
  'switch',
  'number',
  'date',
  'text',
  'textarea',
]);

export function getReservedTemplateFieldNames(scene: EntityScene): Set<string> {
  return new Set(RESERVED_TEMPLATE_FIELD_NAMES[scene]);
}

export function validateTemplateFieldNames(
  scene: EntityScene,
  fields: TemplateField[]
): string | null {
  const reserved = getReservedTemplateFieldNames(scene);
  for (const f of fields) {
    if (reserved.has(f.name.trim())) {
      return `字段名「${f.name}」与系统字段重复，请改名`;
    }
  }
  return null;
}

function dedupeLabelsForScene(scene: EntityScene): Set<string> {
  if (scene === 'bug') return BUG_DEDUPE_LABELS;
  if (scene === 'functional_case') return CASE_DEDUPE_LABELS;
  return new Set<string>();
}

export function dedupeTemplateFields(scene: EntityScene, fields: TemplateField[]): TemplateField[] {
  const labels = dedupeLabelsForScene(scene);
  return sortTemplateFields(fields).filter((f) => !labels.has(f.name));
}

export function templateFilterKey(fieldId: string): string {
  return `cf:${fieldId}`;
}

export function parseTemplateFilterKey(key: string): string | null {
  return key.startsWith('cf:') ? key.slice(3) : null;
}

export function withEmptyFilterOption<T extends { label: string; value: string }>(
  options: T[]
): (T | typeof FILTER_EMPTY_OPTION)[] {
  return [FILTER_EMPTY_OPTION, ...options];
}

export function filterableTemplateFields(scene: EntityScene, fields: TemplateField[]): TemplateField[] {
  const list = dedupeTemplateFields(scene, fields).filter((f) => FILTERABLE_TEMPLATE_TYPES.has(f.type));
  if (scene === 'bug') {
    const severityIdx = list.findIndex((f) => f.name.includes('严重'));
    if (severityIdx > 0) {
      const [severity] = list.splice(severityIdx, 1);
      return [severity, ...list];
    }
  }
  return list;
}

const BUG_LIST_TABLE_EXCLUDED_FIELD_IDS = new Set(['field_source']);

function isBugListTableExcludedField(field: TemplateField): boolean {
  if (BUG_LIST_TABLE_EXCLUDED_FIELD_IDS.has(field.id)) return true;
  if (field.name.includes('平台')) return true;
  if (field.name === '来源') return true;
  return false;
}

export function listTableTemplateFields(scene: EntityScene, fields: TemplateField[]): TemplateField[] {
  let list = dedupeTemplateFields(scene, fields).filter((f) => isOptionFieldType(f.type));
  if (scene === 'bug') {
    list = list.filter((f) => !isBugListTableExcludedField(f));
    const severityIdx = list.findIndex((f) => f.name.includes('严重'));
    if (severityIdx > 0) {
      const [severity] = list.splice(severityIdx, 1);
      return [severity, ...list];
    }
  }
  return list;
}

/** 详情/编辑：展示全部可配置模板字段（去重后）；缺陷场景将「严重程度」类字段置顶 */
export function detailTemplateFields(scene: EntityScene, fields: TemplateField[]): TemplateField[] {
  const list = dedupeTemplateFields(scene, fields);
  if (scene === 'bug') {
    const severityIdx = list.findIndex((f) => f.name.includes('严重'));
    if (severityIdx > 0) {
      const [severity] = list.splice(severityIdx, 1);
      return [severity, ...list];
    }
  }
  return list;
}

/** 缺陷表单：适合 Radio 平铺的单选模板字段（严重程度、平台等） */
export function isPromotedRadioSelectField(field: TemplateField): boolean {
  if (field.type !== 'select') return false;
  const name = field.name;
  if (name.includes('严重') || name.includes('平台')) return true;
  return (field.options?.length ?? 0) <= 8;
}

export function splitPromotedTemplateFields(fields: TemplateField[]): {
  promoted: TemplateField[];
  rest: TemplateField[];
} {
  const promoted: TemplateField[] = [];
  const rest: TemplateField[] = [];
  for (const f of fields) {
    (isPromotedRadioSelectField(f) ? promoted : rest).push(f);
  }
  return { promoted, rest };
}

export function buildFieldCatalog(scene: EntityScene, templateFields: TemplateField[]): FieldCatalogItem[] {
  const templateDefs: FieldCatalogItem[] = filterableTemplateFields(scene, templateFields).map((f) => ({
    key: templateFilterKey(f.id),
    label: f.name,
    kind: 'template' as const,
    fieldId: f.id,
    field: f,
  }));
  const systemDefs = scene === 'bug' ? BUG_FILTER_SYSTEM_DEFS : CASE_FILTER_SYSTEM_DEFS;
  return [...systemDefs, ...templateDefs];
}

export function catalogKeys(catalog: FieldCatalogItem[]): Set<string> {
  return new Set(catalog.map((d) => d.key));
}

export function sanitizeVisibleFilterKeys(
  visibleKeys: string[],
  catalog: FieldCatalogItem[],
  defaultKeys: string[] = DEFAULT_BUG_FILTER_VISIBLE_KEYS
): string[] {
  const allowed = catalogKeys(catalog);
  const sanitized = visibleKeys.filter((k) => allowed.has(k));
  return sanitized.length ? sanitized : [...defaultKeys];
}

export function clearBugFilterValue(state: BugListFilterState, key: string): BugListFilterState {
  const next = { ...state, custom: { ...state.custom } };
  switch (key) {
    case 'q':
      next.q = '';
      break;
    case 'status':
      next.status_keys = [];
      break;
    case 'reporter':
      next.reporter_ids = [];
      break;
    case 'follower':
      next.follower_ids = [];
      break;
    case 'plan_version':
      next.plan_version_ids = [];
      break;
    case 'found_version':
      next.found_version_ids = [];
      break;
    case 'requirement':
      next.requirement_ids = [];
      break;
    case 'plan':
      next.plan_ids = [];
      break;
    default: {
      const fieldId = parseTemplateFilterKey(key);
      if (fieldId) next.custom[fieldId] = [];
    }
  }
  return next;
}

export function clearCaseFilterValue(state: CaseListFilterState, key: string): CaseListFilterState {
  const next = { ...state, custom: { ...state.custom } };
  switch (key) {
    case 'module':
      next.module_id = null;
      next.include_submodules = false;
      break;
    case 'q':
      next.q = '';
      break;
    case 'priority':
      next.priorities = [];
      break;
    case 'requirement':
      next.requirement_ids = [];
      break;
    default: {
      const fieldId = parseTemplateFilterKey(key);
      if (fieldId) next.custom[fieldId] = [];
    }
  }
  return next;
}

export function isEmptyCustomFieldValue(type: string, value: unknown): boolean {
  if (value === null || value === undefined) return true;
  if (type === 'multi_select') return !Array.isArray(value) || value.length === 0;
  if (type === 'switch') return false;
  if (type === 'member') return typeof value !== 'string' || !value.trim();
  if (type === 'number') return value === '' || value === null;
  if (type === 'richtext') {
    if (typeof value !== 'object' || !value) return true;
    const obj = value as { text?: string; files?: unknown[] };
    return !String(obj.text ?? '').trim() && !(Array.isArray(obj.files) && obj.files.length);
  }
  if (typeof value === 'string') return !value.trim();
  return false;
}

export function formatTemplateFieldValue(
  field: TemplateField,
  value: unknown,
  ctx?: TemplateFieldFormatContext
): string {
  if (isEmptyCustomFieldValue(field.type, value)) return '—';
  if (field.type === 'multi_select' && Array.isArray(value)) return value.join('、');
  if (field.type === 'switch') return value ? '是' : '否';
  if (isMemberType(field.type) && typeof value === 'string') {
    return ctx?.memberLabel?.(value) ?? value;
  }
  if (typeof value === 'number') return String(value);
  return String(value);
}

export function templateFieldFilterOptions(field: TemplateField) {
  if (isOptionFieldType(field.type)) {
    return withEmptyFilterOption(field.options.map((o) => ({ label: o, value: o })));
  }
  if (isMemberType(field.type)) {
    return [FILTER_EMPTY_OPTION];
  }
  if (field.type === 'switch') {
    return [
      FILTER_EMPTY_OPTION,
      { label: '是', value: 'true' },
      { label: '否', value: 'false' },
    ];
  }
  return [FILTER_EMPTY_OPTION];
}

export function templateFieldFilterPlaceholder(field: TemplateField): string {
  if (isOptionFieldType(field.type)) return '全部';
  if (field.type === 'switch') return '全部';
  return fieldTypeLabel(field.type);
}

export function richTextPlain(value: unknown): string {
  return normalizeRichTextValue(value).text;
}

export function richTextHasContent(value: unknown): boolean {
  const rt = normalizeRichTextValue(value);
  return !!rt.text.trim() || rt.files.length > 0;
}

export function buildTemplateTableColumns<T extends { custom_fields?: Record<string, unknown> }>(
  fields: TemplateField[],
  ctx?: TemplateFieldFormatContext
): DataTableColumns<T> {
  return fields.map((field) => ({
    title: field.name,
    key: `cf_${field.id}`,
    width: field.name.length > 4 ? 96 : 80,
    ellipsis: { tooltip: true },
    render: (row: T) => {
      const val = row.custom_fields?.[field.id];
      return formatTemplateFieldValue(field, val, ctx);
    },
  }));
}

export { isRichtextType };
