"""add ui_elements table

Revision ID: 005_ui_elements
Revises: 004_ui_automation_tables
Create Date: 2026-06-18
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_ui_elements"
down_revision: Union[str, None] = "004_ui_automation_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT COUNT(*) FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table"
        ),
        {"table": table},
    )
    return result.scalar_one() > 0


def upgrade() -> None:
    if not _table_exists("ui_elements"):
        op.create_table(
            "ui_elements",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=False, index=True),
            sa.Column("platform", sa.Enum("android", "ios", name="mobileplatform"), nullable=False, index=True),
            sa.Column("name", sa.String(128), nullable=False),
            sa.Column("selector", sa.String(512), nullable=False),
            sa.Column("description", sa.Text, nullable=True),
            sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
            sa.Column(
                "updated_at",
                sa.DateTime,
                server_default=sa.func.now(),
                onupdate=sa.func.now(),
                nullable=False,
            ),
        )


def downgrade() -> None:
    if _table_exists("ui_elements"):
        op.drop_table("ui_elements")
