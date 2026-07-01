"""add composite indexes for schedule date range queries

Revision ID: 009_schedule_indexes
Revises: 008_ui_test_runs_video
Create Date: 2026-07-01
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009_schedule_indexes"
down_revision: Union[str, None] = "008_ui_test_runs_video"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _index_exists(index_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT COUNT(*) FROM information_schema.STATISTICS "
            "WHERE TABLE_SCHEMA = DATABASE() AND INDEX_NAME = :index_name"
        ),
        {"index_name": index_name},
    )
    return result.scalar_one() > 0


def upgrade() -> None:
    # requirement_node_tasks: (assignee_id, scheduled_start, scheduled_end)
    # 加速人员排期按日期范围过滤任务的查询
    if not _index_exists("ix_rnt_assignee_schedule"):
        op.create_index(
            "ix_rnt_assignee_schedule",
            "requirement_node_tasks",
            ["assignee_id", "scheduled_start", "scheduled_end"],
        )

    # bug_follower_links: (user_id, scheduled_start, scheduled_end)
    # 加速人员排期按日期范围过滤缺陷跟进记录的查询
    if not _index_exists("ix_bfl_user_schedule"):
        op.create_index(
            "ix_bfl_user_schedule",
            "bug_follower_links",
            ["user_id", "scheduled_start", "scheduled_end"],
        )


def downgrade() -> None:
    if _index_exists("ix_bfl_user_schedule"):
        op.drop_index("ix_bfl_user_schedule", table_name="bug_follower_links")

    if _index_exists("ix_rnt_assignee_schedule"):
        op.drop_index("ix_rnt_assignee_schedule", table_name="requirement_node_tasks")
