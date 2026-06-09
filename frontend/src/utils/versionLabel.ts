import { formatDateOnly } from '@/utils/formatDateOnly';

/** 版本展示：仅显示版本名称 */
export function formatVersionDisplay(v: { num: number; name: string }): string {
  return v.name.trim();
}

/** 版本展示含上线时间，无上线时间则仅展示版本名 */
export function formatVersionWithRelease(
  v: { num: number; name: string; released_at?: string | null } | null | undefined
): string {
  if (!v) return '—';
  const name = formatVersionDisplay(v);
  if (!v.released_at) return name;
  return `${name}（${formatDateOnly(v.released_at)}）`;
}
