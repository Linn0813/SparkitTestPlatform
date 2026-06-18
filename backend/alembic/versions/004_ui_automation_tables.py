"""add ui automation tables

Revision ID: 004_ui_automation_tables
Revises: 003_build_number
Create Date: 2026-06-17
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_ui_automation_tables"
down_revision: Union[str, None] = "003_build_number"
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
    if not _table_exists("ui_test_cases"):
        op.create_table(
            "ui_test_cases",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=False, index=True),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("platform", sa.Enum("android", "ios", name="mobileplatform"), nullable=False),
            sa.Column("description", sa.Text, nullable=True),
            sa.Column(
                "status",
                sa.Enum("draft", "active", name="uitestcasestatus"),
                nullable=False,
                server_default="draft",
            ),
            sa.Column("selectors", sa.JSON, nullable=False),
            sa.Column("steps", sa.JSON, nullable=False),
            sa.Column("assertion", sa.JSON, nullable=False),
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

    if not _table_exists("mobile_apps"):
        op.create_table(
            "mobile_apps",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=False, index=True),
            sa.Column("platform", sa.Enum("android", "ios", name="mobileplatform"), nullable=False),
            sa.Column("version", sa.String(128), nullable=False),
            sa.Column("filename", sa.String(255), nullable=False),
            sa.Column("storage_key", sa.String(512), nullable=False),
            sa.Column("size", sa.Integer, nullable=False, server_default="0"),
            sa.Column("uploaded_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("uploaded_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        )

    if not _table_exists("ui_runners"):
        op.create_table(
            "ui_runners",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=False, index=True),
            sa.Column("name", sa.String(128), nullable=False),
            sa.Column("token", sa.String(64), unique=True, nullable=False),
            sa.Column("platform", sa.Enum("android", "ios", name="mobileplatform"), nullable=False),
            sa.Column("last_heartbeat_at", sa.DateTime, nullable=True),
            sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        )

    if not _table_exists("ui_test_runs"):
        op.create_table(
            "ui_test_runs",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=False, index=True),
            sa.Column("case_id", sa.String(36), sa.ForeignKey("ui_test_cases.id"), nullable=False, index=True),
            sa.Column("app_id", sa.String(36), sa.ForeignKey("mobile_apps.id"), nullable=False),
            sa.Column("runner_id", sa.String(36), sa.ForeignKey("ui_runners.id"), nullable=True),
            sa.Column(
                "status",
                sa.Enum("pending", "running", "passed", "failed", "error", name="uirunstatus"),
                nullable=False,
                server_default="pending",
                index=True,
            ),
            sa.Column("error_message", sa.Text, nullable=True),
            sa.Column("triggered_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("started_at", sa.DateTime, nullable=True),
            sa.Column("finished_at", sa.DateTime, nullable=True),
            sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        )

    if not _table_exists("ui_test_step_results"):
        op.create_table(
            "ui_test_step_results",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("run_id", sa.String(36), sa.ForeignKey("ui_test_runs.id"), nullable=False, index=True),
            sa.Column("step_index", sa.Integer, nullable=False),
            sa.Column(
                "status",
                sa.Enum("pending", "passed", "failed", "skipped", name="uistepstatus"),
                nullable=False,
                server_default="pending",
            ),
            sa.Column("error_message", sa.Text, nullable=True),
            sa.Column("screenshot_key", sa.String(512), nullable=True),
            sa.Column("duration_ms", sa.Integer, nullable=True),
            sa.Column("executed_at", sa.DateTime, nullable=True),
        )


def downgrade() -> None:
    for table in ["ui_test_step_results", "ui_test_runs", "ui_runners", "mobile_apps", "ui_test_cases"]:
        if _table_exists(table):
            op.drop_table(table)
