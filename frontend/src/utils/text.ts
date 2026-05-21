/** 表格单元格单行展示用截断 */
export function truncateForTable(text: string | null | undefined, max = 72): string {
  if (!text) return '—';
  const s = text.replace(/\s+/g, ' ').trim();
  if (s.length <= max) return s;
  return `${s.slice(0, max)}…`;
}
