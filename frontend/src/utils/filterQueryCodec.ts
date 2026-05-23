/** 列表筛选 query 编解码：逗号分隔，兼容旧单值 URL。 */

type RouteQueryRaw = string | string[] | null | undefined | (string | null)[];

export function decodeFilterQuery(raw: RouteQueryRaw): string[] {
  if (raw == null) return [];
  const parts = Array.isArray(raw) ? raw : [raw];
  const seen = new Set<string>();
  const out: string[] = [];
  for (const item of parts) {
    if (typeof item !== 'string' || !item.trim()) continue;
    for (const piece of item.split(',')) {
      const v = piece.trim();
      if (v && !seen.has(v)) {
        seen.add(v);
        out.push(v);
      }
    }
  }
  return out;
}

export function encodeFilterValues(values: string[] | null | undefined): string | undefined {
  if (!values?.length) return undefined;
  const seen = new Set<string>();
  const out: string[] = [];
  for (const v of values) {
    const s = v?.trim();
    if (s && !seen.has(s)) {
      seen.add(s);
      out.push(s);
    }
  }
  return out.length ? out.join(',') : undefined;
}

export function hasFilterValues(values: string[] | null | undefined): boolean {
  return (values?.length ?? 0) > 0;
}

/** 将 URL 中的 status_key / exclude_status_key 解析为筛选项展示用的状态 key 列表 */
export function resolveStatusKeysFromRouteQuery(
  statusRaw: RouteQueryRaw,
  excludeRaw: RouteQueryRaw,
  allStatusKeys: string[]
): string[] {
  const fromStatus = decodeFilterQuery(statusRaw);
  if (fromStatus.length) return fromStatus;
  const excluded = new Set(decodeFilterQuery(excludeRaw));
  if (!excluded.size) return [];
  return allStatusKeys.filter((key) => !excluded.has(key));
}
