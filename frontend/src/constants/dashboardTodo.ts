/** 工作台「无规划迭代缺陷」排除的状态 */
export const UNPLANNED_BUG_EXCLUDED_STATUS_KEYS = [
  'accepted',
  'rejected',
  'suspended',
  'to_requirement',
] as const;

export const UNPLANNED_BUG_EXCLUDED_STATUS_QUERY =
  UNPLANNED_BUG_EXCLUDED_STATUS_KEYS.join(',');
