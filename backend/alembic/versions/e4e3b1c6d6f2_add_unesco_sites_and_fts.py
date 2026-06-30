"""add unesco sites and fts

Revision ID: e4e3b1c6d6f2
Revises: d1637cbc70cb
Create Date: 2026-06-29 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e4e3b1c6d6f2'
down_revision: Union[str, Sequence[str], None] = 'd1637cbc70cb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # 1. Create unesco_sites table if it does not exist
    if 'unesco_sites' not in tables:
        op.create_table(
            'unesco_sites',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=512), nullable=False),
            sa.Column('country', sa.String(length=256), nullable=False),
            sa.Column('region', sa.String(length=256), nullable=True),
            sa.Column('inscription_year', sa.Integer(), nullable=True),
            sa.Column('criteria', sa.String(length=64), nullable=True),
            sa.Column('description', sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        # Create default indexes on name and country if table was newly created
        op.create_index(op.f('ix_unesco_sites_name'), 'unesco_sites', ['name'], unique=False)
        op.create_index(op.f('ix_unesco_sites_country'), 'unesco_sites', ['country'], unique=False)

    # 2. Add search_vector computed column if it does not exist
    columns = [col['name'] for col in inspector.get_columns('unesco_sites')]
    if 'search_vector' not in columns:
        op.add_column(
            'unesco_sites',
            sa.Column(
                'search_vector',
                postgresql.TSVECTOR(),
                sa.Computed(
                    "to_tsvector('english', coalesce(name, '') || ' ' || coalesce(country, '') || ' ' || coalesce(description, ''))",
                    persisted=True
                ),
                nullable=True
            )
        )

    # 3. Create FTS GIN index if it does not exist
    indexes = [idx['name'] for idx in inspector.get_indexes('unesco_sites')]
    if 'ix_unesco_sites_search_vector' not in indexes:
        op.create_index(
            'ix_unesco_sites_search_vector',
            'unesco_sites',
            ['search_vector'],
            unique=False,
            postgresql_using='gin'
        )

    # 4. Create composite index on (name, country) for exact/fuzzy fast path matching
    if 'ix_unesco_sites_name_country' not in indexes:
        op.create_index(
            'ix_unesco_sites_name_country',
            'unesco_sites',
            ['name', 'country'],
            unique=False
        )


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'unesco_sites' in tables:
        indexes = [idx['name'] for idx in inspector.get_indexes('unesco_sites')]
        if 'ix_unesco_sites_name_country' in indexes:
            op.drop_index('ix_unesco_sites_name_country', table_name='unesco_sites')
        if 'ix_unesco_sites_search_vector' in indexes:
            op.drop_index('ix_unesco_sites_search_vector', table_name='unesco_sites')

        columns = [col['name'] for col in inspector.get_columns('unesco_sites')]
        if 'search_vector' in columns:
            op.drop_column('unesco_sites', 'search_vector')

        # Optional: We don't drop the entire unesco_sites table to prevent data loss
        # unless it was purely created by this migration. Since it's a seed table,
        # we can keep the table itself or drop it. Let's keep it safe.
