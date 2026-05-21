/** 版本展示：名称已像版本号时不再加 #num 前缀 */
export function formatVersionDisplay(v: { num: number; name: string }): string {
  const n = v.name.trim();
  if (/^v?\d[\d.]*$/i.test(n)) return n;
  return `#${v.num} · ${n}`;
}
