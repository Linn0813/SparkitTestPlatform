import type { TemplateField } from '@/types/business';

/** 新建字段可选类型 */
export type FieldTypeValue =
  | 'text'
  | 'richtext'
  | 'number'
  | 'date'
  | 'switch'
  | 'select'
  | 'multi_select'
  | 'member';

/** 兼容历史模板 */
export type StoredFieldType = FieldTypeValue | 'textarea';

export interface RichTextFile {
  object_key: string;
  filename: string;
  kind: 'image' | 'video' | 'file';
  url?: string;
}

export interface RichTextFieldValue {
  text: string;
  files: RichTextFile[];
}

export const FIELD_TYPE_LABELS: Record<FieldTypeValue | 'textarea', string> = {
  text: '文本',
  textarea: '文本',
  richtext: '图文',
  number: '数字',
  date: '日期',
  switch: '是/否',
  select: '单选',
  multi_select: '多选',
  member: '人员',
};

export const FIELD_TYPE_OPTIONS = (
  ['text', 'richtext', 'number', 'date', 'switch', 'select', 'multi_select', 'member'] as const
).map((value) => ({
  label: FIELD_TYPE_LABELS[value],
  value,
}));

export function fieldTypeLabel(type: string): string {
  return FIELD_TYPE_LABELS[type as keyof typeof FIELD_TYPE_LABELS] ?? type;
}

export function isTextLikeType(type: string): boolean {
  return type === 'text' || type === 'textarea';
}

export function isRichtextType(type: string): boolean {
  return type === 'richtext';
}

/** 与 PRD 链接等系统字段一致的 URL/链接类自定义字段 */
export function isLinkLikeTemplateField(field: TemplateField): boolean {
  return field.name.includes('链接');
}

/** 描述类长文本字段（双列表单中占满整行） */
export function isDescriptionLikeTemplateField(field: TemplateField): boolean {
  return field.name === '描述' || field.name.includes('描述');
}

export function isOptionFieldType(type: string): boolean {
  return type === 'select' || type === 'multi_select';
}

export function isMemberType(type: string): boolean {
  return type === 'member';
}

export function normalizeRichTextValue(value: unknown): RichTextFieldValue {
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    const obj = value as Record<string, unknown>;
    const text = obj.text === undefined || obj.text === null ? '' : String(obj.text);
    const rawFiles = Array.isArray(obj.files) ? obj.files : [];
    const files: RichTextFile[] = rawFiles
      .filter((f): f is Record<string, unknown> => !!f && typeof f === 'object')
      .map((f) => ({
        object_key: String(f.object_key ?? ''),
        filename: String(f.filename ?? 'file'),
        kind: (f.kind === 'image' || f.kind === 'video' ? f.kind : 'file') as RichTextFile['kind'],
        url: f.url ? String(f.url) : undefined,
      }))
      .filter((f) => f.object_key);
    return { text, files };
  }
  if (typeof value === 'string' && value) {
    return { text: value, files: [] };
  }
  return { text: '', files: [] };
}

export function fieldDefaultValue(type: string): unknown {
  switch (type) {
    case 'select':
    case 'member':
    case 'number':
    case 'date':
      return null;
    case 'switch':
      return false;
    case 'multi_select':
      return [];
    case 'richtext':
      return { text: '', files: [] } satisfies RichTextFieldValue;
    default:
      return '';
  }
}

export function sortTemplateFields(fields: TemplateField[]): TemplateField[] {
  return [...fields].sort((a, b) => (a.sort ?? 0) - (b.sort ?? 0));
}

export function emptyCustomFields(fields: TemplateField[]): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const f of sortTemplateFields(fields)) {
    out[f.id] = fieldDefaultValue(f.type);
  }
  return out;
}

export function mergeCustomFields(
  fields: TemplateField[],
  existing?: Record<string, unknown> | null
): Record<string, unknown> {
  const base = emptyCustomFields(fields);
  if (!existing) return base;
  for (const f of fields) {
    if (existing[f.id] !== undefined && existing[f.id] !== null) {
      if (isRichtextType(f.type)) {
        base[f.id] = normalizeRichTextValue(existing[f.id]);
      } else {
        base[f.id] = existing[f.id];
      }
    }
  }
  return base;
}

export const BUILTIN_FIELD_IDS = new Set<string>();

export function isBuiltinField(id: string): boolean {
  return BUILTIN_FIELD_IDS.has(id);
}

export function generateFieldId(): string {
  return `field_${Date.now()}`;
}

export function normalizeFieldSort(fields: TemplateField[]): TemplateField[] {
  return fields.map((f, i) => ({ ...f, sort: i }));
}

function isEmptyRequiredValue(type: string, v: unknown): boolean {
  if (v === undefined || v === null) return true;
  if (type === 'multi_select') return !Array.isArray(v) || v.length === 0;
  if (type === 'switch') return false;
  if (type === 'member') return typeof v !== 'string' || !v.trim();
  if (type === 'richtext') {
    const rt = normalizeRichTextValue(v);
    return !rt.text.trim() && rt.files.length === 0;
  }
  if (type === 'number') return v === '';
  if (typeof v === 'string') return !v.trim();
  return v === '';
}

export function validateCustomFields(
  fields: TemplateField[],
  values: Record<string, unknown>
): string | null {
  for (const f of sortTemplateFields(fields)) {
    if (!f.required) continue;
    if (isEmptyRequiredValue(f.type, values[f.id])) {
      return `请填写「${f.name}」`;
    }
  }
  return null;
}
