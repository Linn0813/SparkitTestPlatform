/** 展示日期字段（YYYY-MM-DD 或 ISO 前缀） */
export function formatDateOnly(value: string | null | undefined): string {
  if (!value) return '—';
  const d = value.slice(0, 10);
  const parts = d.split('-').map(Number);
  if (parts.length !== 3 || parts.some((n) => Number.isNaN(n))) return d;
  const [y, m, day] = parts;
  return new Date(y, m - 1, day).toLocaleDateString('zh-CN');
}
