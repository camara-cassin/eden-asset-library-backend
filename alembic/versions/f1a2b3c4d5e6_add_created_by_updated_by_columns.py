"""add_created_by_updated_by_columns

Revision ID: f1a2b3c4d5e6
Revises: a1b2c3d4e5f6
Create Date: 2025-12-05 16:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add created_by and updated_by columns to eden_assets table."""
    op.add_column('eden_assets', sa.Column('created_by', sa.String(255), nullable=True))
    op.add_column('eden_assets', sa.Column('updated_by', sa.String(255), nullable=True))


def downgrade() -> None:
    """Remove created_by and updated_by columns from eden_assets table."""
    op.drop_column('eden_assets', 'updated_by')
    op.drop_column('eden_assets', 'created_by')
