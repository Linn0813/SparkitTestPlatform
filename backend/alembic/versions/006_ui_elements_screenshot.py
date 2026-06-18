"""add screenshot_key to ui_elements

Revision ID: 006_ui_elements_screenshot
Revises: 005_ui_elements
Create Date: 2026-06-18
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006_ui_elements_screenshot"
down_revision: Union[str, None] = "005_ui_elements"
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
    if not _column_exists("ui_elements", "screenshot_key"):
        op.add_column("ui_elements", sa.Column("screenshot_key", sa.String(512), nullable=True))


def downgrade() -> None:
    if _column_exists("ui_elements", "screenshot_key"):
        op.drop_column("ui_elements", "screenshot_key")
