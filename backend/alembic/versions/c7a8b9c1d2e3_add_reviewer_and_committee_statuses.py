"""add reviewer and committee statuses

Revision ID: c7a8b9c1d2e3
Revises: e4e3b1c6d6f2
Create Date: 2026-06-30 20:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7a8b9c1d2e3'
down_revision: Union[str, Sequence[str], None] = 'e4e3b1c6d6f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PostgreSQL-specific: ALTER TYPE ... ADD VALUE cannot run inside a transaction.
    # We use autocommit_block() to run outside of the main transaction block.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE submissionstatus ADD VALUE 'reviewer_review'")
        op.execute("ALTER TYPE submissionstatus ADD VALUE 'committee_review'")


def downgrade() -> None:
    # PostgreSQL doesn't support removing values from an ENUM type easily.
    # Typically, a downgrade would require recreating the type, which is high-risk.
    # Since we are just adding values, we can leave them in the enum or do a pass-through.
    pass
