/** 工作台「无规划迭代缺陷」排除的状态 */
export const UNPLANNED_BUG_EXCLUDED_STATUS_KEYS = [
  'accepted',
  'rejected',
  'suspended',
  'to_requirement',
] as const;

export const UNPLANNED_BUG_EXCLUDED_STATUS_QUERY =
  UNPLANNED_BUG_EXCLUDED_STATUS_KEYS.join(',');

/** 与 backend MEMBER_FOLLOWER_TODO_STATUS_KEYS 一致 */
export const MEMBER_FOLLOWER_TODO_STATUS_QUERY = 'pending_confirm,in_progress,suspended';

/** 与 backend TESTER_FIXED_BUG_STATUS_KEY 一致 */
export const TESTER_FIXED_BUG_STATUS_QUERY = 'fixed';

/** 待办「开发中」需求（not_tested_requirements） */
export const TESTER_TODO_REQUIREMENT_STATUS_QUERY = 'developing';

/** 待办「测试中 + 待发版」需求 */
export const TESTER_TODO_TESTING_REQUIREMENT_STATUS_QUERY = 'testing,pending_release';

/** 待办需求区块「查看全部」 */
export const TESTER_TODO_ALL_REQUIREMENT_STATUS_QUERY = `${TESTER_TODO_REQUIREMENT_STATUS_QUERY},${TESTER_TODO_TESTING_REQUIREMENT_STATUS_QUERY}`;

/** 待办计划区块「查看全部」 */
export const TESTER_PLAN_TODO_STATUS_QUERY = 'draft,active';
