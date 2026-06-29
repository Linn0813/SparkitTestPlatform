/** 由 vite.config.ts 在 npm run build / dev 启动时写入 */
export function formatAppBuildTime(iso = import.meta.env.VITE_APP_BUILD_TIME): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });
}

export const appBuildTimeLabel = formatAppBuildTime();
