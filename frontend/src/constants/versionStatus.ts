import type { VersionNodeKey, VersionStatus } from '@/types/business';

export const VERSION_STATUS_LABELS: Record<VersionStatus, string> = {
  planning: '规划中',
  developing: '开发中',
  releasing: '发版中',
  reviewing: '提审中',
  ended: '已结束',
};

export const VERSION_STATUS_TAG_TYPES: Record<
  VersionStatus,
  'default' | 'info' | 'warning' | 'success' | 'error'
> = {
  planning: 'default',
  developing: 'info',
  releasing: 'warning',
  reviewing: 'warning',
  ended: 'success',
};

export const VERSION_NODE_LABELS: Record<VersionNodeKey, string> = {
  planning: '版本规划',
  development: '版本开发',
  release_verification: '发版验证',
  gp_review: 'GP提审',
  as_review: 'AS提审',
  website_link: '官网链接',
  live: '已上线',
};

export const SERIAL_VERSION_NODES: VersionNodeKey[] = [
  'planning',
  'development',
  'release_verification',
];

export const REVIEW_VERSION_NODES: VersionNodeKey[] = ['gp_review', 'as_review', 'website_link'];

const PREREQUISITES: Record<VersionNodeKey, VersionNodeKey[]> = {
  planning: [],
  development: ['planning'],
  release_verification: ['development'],
  gp_review: ['release_verification'],
  as_review: ['release_verification'],
  website_link: ['release_verification'],
  live: ['gp_review', 'as_review', 'website_link'],
};

export function canCompleteVersionNode(
  nodeKey: VersionNodeKey,
  nodes: { node_key: VersionNodeKey; state: string }[]
): boolean {
  const node = nodes.find((n) => n.node_key === nodeKey);
  if (!node || node.state === 'completed') return false;
  const byKey = new Map(nodes.map((n) => [n.node_key, n.state]));
  return PREREQUISITES[nodeKey].every((k) => byKey.get(k) === 'completed');
}

export function versionStatusLabel(status: VersionStatus): string {
  return VERSION_STATUS_LABELS[status] ?? status;
}

export function versionStatusTagType(
  status: VersionStatus
): 'default' | 'info' | 'warning' | 'success' | 'error' {
  return VERSION_STATUS_TAG_TYPES[status] ?? 'default';
}
