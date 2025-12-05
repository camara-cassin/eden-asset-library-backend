"""add_category_suggestions_table

Revision ID: a1b2c3d4e5f6
Revises: 682f67f0d218
Create Date: 2025-12-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '682f67f0d218'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'category_suggestions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('suggestion_type', sa.String(50), nullable=False),  # 'primary_category' | 'subcategory'
        sa.Column('primary_category', sa.String(255), nullable=True),  # null if suggesting new primary, populated if suggesting subcategory
        sa.Column('suggested_name', sa.String(255), nullable=False),  # the actual suggestion
        sa.Column('reason', sa.Text, nullable=False),
        sa.Column('suggested_by_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('asset_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('eden_assets.id'), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),  # pending | approved | rejected
        sa.Column('admin_notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reviewed_by_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
    )
    
    # Add indexes for common queries
    op.create_index('ix_category_suggestions_status', 'category_suggestions', ['status'])
    op.create_index('ix_category_suggestions_type', 'category_suggestions', ['suggestion_type'])
    op.create_index('ix_category_suggestions_primary_category', 'category_suggestions', ['primary_category'])


def downgrade() -> None:
    op.drop_index('ix_category_suggestions_primary_category')
    op.drop_index('ix_category_suggestions_type')
    op.drop_index('ix_category_suggestions_status')
    op.drop_table('category_suggestions')
