"""project_versions: add optional build_number column

Revision ID: 003_project_versions_build_number
Revises: 002_stored_files_drop_content
Create Date: 2026-06-11

"""
from typing import Sequence, Union

from alembic import op

revision: str = "003_project_versions_build_number"
down_revision: Union[str, None] = "002_stored_files_drop_content"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE project_versions ADD COLUMN build_number VARCHAR(64) NULL AFTER name")


def downgrade() -> None:
    op.execute("ALTER TABLE project_versions DROP COLUMN build_number")
