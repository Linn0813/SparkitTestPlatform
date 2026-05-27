/** URL 字符：遇空白、引号、括号或分号（作分隔符）时结束 */
const URL_IN_TEXT_RE = /https?:\/\/[^\s<>"')\];；\]}]+/gi;

const TRAILING_PUNCT_RE = /[.,;；:!?]+$/;

const SEGMENT_SPLIT_RE = /[;；\n,]+/;

export interface ParseUrlsOptions {
  /** 为 false 时保留重复 URL（同一地址粘贴两次仍展示两条） */
  dedupe?: boolean;
}

function extractUrlsFromChunk(chunk: string, seen: Set<string> | null, out: string[]) {
  const trimmed = chunk.trim();
  if (!trimmed) return;
  const matches = trimmed.match(URL_IN_TEXT_RE) ?? [];
  const candidates =
    matches.length > 0 ? matches : /^https?:\/\//i.test(trimmed) ? [trimmed] : [];
  for (const part of candidates) {
    const href = part.replace(TRAILING_PUNCT_RE, '');
    if (!href) continue;
    if (seen?.has(href)) continue;
    seen?.add(href);
    out.push(href);
  }
}

/** 从自由文本中提取 http(s) URL，保持出现顺序。 */
export function parseUrlsFromText(input: string, options: ParseUrlsOptions = {}): string[] {
  const dedupe = options.dedupe !== false;
  const raw = input?.trim() ?? '';
  if (!raw) return [];

  const seen = dedupe ? new Set<string>() : null;
  const urls: string[] = [];

  const segments = raw
    .split(SEGMENT_SPLIT_RE)
    .map((s) => s.trim())
    .filter(Boolean);

  if (segments.length > 1) {
    for (const seg of segments) extractUrlsFromChunk(seg, seen, urls);
  } else {
    extractUrlsFromChunk(raw, seen, urls);
  }

  return urls;
}

export function linkLabel(url: string, maxLen = 48): string {
  if (url.length <= maxLen) return url;
  return `${url.slice(0, maxLen)}…`;
}

export function urlsToLinkItems(urls: string[]): { href: string; label: string }[] {
  return urls.map((href) => ({ href, label: linkLabel(href) }));
}
