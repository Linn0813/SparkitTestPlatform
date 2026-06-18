"""add video_key to ui_test_runs

Revision ID: 008_ui_test_runs_video
Revises: 007_ui_elements_drop_screenshot
Create Date: 2026-06-18
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008_ui_test_runs_video"
down_revision: Union[str, None] = "007_ui_elements_drop_screenshot"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT COUNT(*) FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table "
            "AND COLUMN_NAME = :column"
        ),
        {"table": table, "column": column},
    )
    return result.scalar_one() > 0


def upgrade() -> None:
    if not _column_exists("ui_test_runs", "video_key"):
        op.add_column("ui_test_runs", sa.Column("video_key", sa.String(512), nullable=True))


def downgrade() -> None:
    if _column_exists("ui_test_runs", "video_key"):
        op.drop_column("ui_test_runs", "video_key")
