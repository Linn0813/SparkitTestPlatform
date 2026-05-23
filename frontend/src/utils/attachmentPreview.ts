const IMAGE_RE = /\.(png|jpe?g|gif|webp|bmp|svg)$/i;
const VIDEO_RE = /\.(mov|mp4|webm|ogg|m4v|avi|mkv)$/i;

export function isImageAttachment(filename: string): boolean {
  return IMAGE_RE.test(filename);
}

export function isVideoAttachment(filename: string): boolean {
  return VIDEO_RE.test(filename);
}

export function isPreviewableAttachment(filename: string): boolean {
  return isImageAttachment(filename) || isVideoAttachment(filename);
}

/** 带 download=1 的签名链接，用于显式下载并保留中文文件名 */
export function attachmentDownloadUrl(url: string): string {
  if (/([?&])download=1(?:&|$)/.test(url)) return url;
  return `${url}${url.includes('?') ? '&' : '?'}download=1`;
}
