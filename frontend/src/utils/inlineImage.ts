/** 内联图片占位：![alt](sparkit:object_key) */
export const SPARKIT_IMAGE_SCHEME = 'sparkit:';

const IMAGE_MARKDOWN_RE = /!\[([^\]]*)\]\((sparkit:[^)]+)\)/g;

export function imageMarkdown(objectKey: string, alt = '图片'): string {
  return `![${alt}](${SPARKIT_IMAGE_SCHEME}${objectKey})`;
}

export function insertTextAtCursor(
  value: string,
  insertion: string,
  selectionStart: number,
  selectionEnd: number
): { text: string; cursor: number } {
  const text = value.slice(0, selectionStart) + insertion + value.slice(selectionEnd);
  return { text, cursor: selectionStart + insertion.length };
}

export function extractSparkitObjectKeys(text: string): string[] {
  const keys: string[] = [];
  let m: RegExpExecArray | null;
  const re = /!\[[^\]]*\]\(sparkit:([^)]+)\)/g;
  while ((m = re.exec(text)) !== null) {
    keys.push(m[1]);
  }
  return keys;
}

/** 将 sparkit: 引用替换为可访问 URL（用于展示） */
export function replaceSparkitImages(text: string, urlByKey: Record<string, string>): string {
  return text.replace(IMAGE_MARKDOWN_RE, (_, alt: string, ref: string) => {
    const key = ref.startsWith(SPARKIT_IMAGE_SCHEME) ? ref.slice(SPARKIT_IMAGE_SCHEME.length) : ref;
    const url = urlByKey[key];
    if (!url) return `![${alt}](${ref})`;
    return `![${alt}](${url})`;
  });
}

const INLINE_IMAGE_URL_RE = /\/api\/v1\/files\/raw\?[^)]+|https?:\/\/[^)]+/;

/** 将已 escape 的 Markdown 图片语法转为 img 标签（支持相对 API 路径与绝对 URL） */
export function renderInlineImageHtml(escapedText: string): string {
  return escapedText.replace(
    new RegExp(`!\\[([^\\]]*)\\]\\((${INLINE_IMAGE_URL_RE.source})\\)`, 'g'),
    '<img src="$2" alt="$1" class="inline-md-img" loading="lazy" />'
  );
}
