"""Workbench todo status filters (aligned with product terminology)."""

MEMBER_FOLLOWER_TODO_STATUS_KEYS = ("pending_confirm", "in_progress", "suspended")

TESTER_FIXED_BUG_STATUS_KEY = "fixed"

TESTER_TODO_REQUIREMENT_STATUS_KEYS = ("not_tested", "testing")

# 概览「缺陷维度」：全项目统计，不含终态
BUG_OVERVIEW_EXCLUDED_STATUS_KEYS = ("accepted", "rejected", "to_requirement")
