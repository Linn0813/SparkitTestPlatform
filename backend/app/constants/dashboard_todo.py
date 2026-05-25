"""Workbench todo status filters (aligned with product terminology)."""

MEMBER_FOLLOWER_TODO_STATUS_KEYS = ("pending_confirm", "in_progress", "suspended")

TESTER_FIXED_BUG_STATUS_KEY = "fixed"

# 兼容字段名：not_tested_requirements 展示「开发中」
TESTER_TODO_REQUIREMENT_STATUS_KEYS = ("developing",)

# testing_requirements 展示「测试中 + 待发版」
TESTER_TODO_TESTING_REQUIREMENT_STATUS_KEYS = ("testing", "pending_release")

# 概览「缺陷维度」：全项目统计，不含终态
BUG_OVERVIEW_EXCLUDED_STATUS_KEYS = ("accepted", "rejected", "to_requirement")

# 工作台「无规划迭代缺陷」：不含已验收、已拒绝、挂起、转需求
UNPLANNED_BUG_EXCLUDED_STATUS_KEYS = ("accepted", "rejected", "suspended", "to_requirement")
