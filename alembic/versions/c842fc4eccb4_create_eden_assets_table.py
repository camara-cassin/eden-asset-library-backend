"""create_eden_assets_table

Revision ID: c842fc4eccb4
Revises: 
Create Date: 2025-12-04 00:09:58.975245

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c842fc4eccb4'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create eden_assets table with all columns and indexes."""
    op.create_table(
        'eden_assets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('asset_id', sa.String(255), unique=True, nullable=False),
        sa.Column('asset_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='draft'),
        sa.Column('submission_status', sa.String(50), nullable=True),
        sa.Column('category', sa.String(255), nullable=True),
        sa.Column('scaling_potential', sa.String(50), nullable=True),
        sa.Column('company_name', sa.String(255), nullable=True),
        sa.Column('creator_name', sa.String(255), nullable=True),
        sa.Column('contributor_id', sa.String(255), nullable=True),
        sa.Column('data', postgresql.JSONB, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    
    # Create indexes for efficient querying
    op.create_index('ix_eden_assets_asset_id', 'eden_assets', ['asset_id'])
    op.create_index('ix_eden_assets_asset_type', 'eden_assets', ['asset_type'])
    op.create_index('ix_eden_assets_status', 'eden_assets', ['status'])
    op.create_index('ix_eden_assets_submission_status', 'eden_assets', ['submission_status'])
    op.create_index('ix_eden_assets_category', 'eden_assets', ['category'])
    op.create_index('ix_eden_assets_scaling_potential', 'eden_assets', ['scaling_potential'])
    op.create_index('ix_eden_assets_company_name', 'eden_assets', ['company_name'])
    op.create_index('ix_eden_assets_creator_name', 'eden_assets', ['creator_name'])
    op.create_index('ix_eden_assets_contributor_id', 'eden_assets', ['contributor_id'])


def downgrade() -> None:
    """Drop eden_assets table and all indexes."""
    op.drop_index('ix_eden_assets_contributor_id', table_name='eden_assets')
    op.drop_index('ix_eden_assets_creator_name', table_name='eden_assets')
    op.drop_index('ix_eden_assets_company_name', table_name='eden_assets')
    op.drop_index('ix_eden_assets_scaling_potential', table_name='eden_assets')
    op.drop_index('ix_eden_assets_category', table_name='eden_assets')
    op.drop_index('ix_eden_assets_submission_status', table_name='eden_assets')
    op.drop_index('ix_eden_assets_status', table_name='eden_assets')
    op.drop_index('ix_eden_assets_asset_type', table_name='eden_assets')
    op.drop_index('ix_eden_assets_asset_id', table_name='eden_assets')
    op.drop_table('eden_assets')
