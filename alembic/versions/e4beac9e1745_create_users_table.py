"""create_users_table

Revision ID: e4beac9e1745
Revises: c842fc4eccb4
Create Date: 2025-12-04 02:31:29.647393

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'e4beac9e1745'
down_revision: Union[str, Sequence[str], None] = 'c842fc4eccb4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create users table."""
    bind = op.get_bind()
    
    # Create the role enum type if it doesn't exist
    result = bind.execute(sa.text(
        "SELECT 1 FROM pg_type WHERE typname = 'userrole'"
    ))
    enum_exists = result.fetchone() is not None
    
    if not enum_exists:
        bind.execute(sa.text(
            "CREATE TYPE userrole AS ENUM ('admin', 'contributor', 'viewer')"
        ))
    
    # Check if table exists
    result = bind.execute(sa.text(
        "SELECT 1 FROM information_schema.tables WHERE table_name = 'users'"
    ))
    table_exists = result.fetchone() is not None
    
    if not table_exists:
        # Use raw SQL to avoid SQLAlchemy trying to create the enum again
        bind.execute(sa.text("""
            CREATE TABLE users (
                id UUID PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                role userrole NOT NULL DEFAULT 'contributor',
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            )
        """))
        bind.execute(sa.text("CREATE INDEX ix_users_email ON users (email)"))


def downgrade() -> None:
    """Drop users table."""
    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')
    
    # Drop the role enum type
    role_enum = sa.Enum('admin', 'contributor', 'viewer', name='userrole')
    role_enum.drop(op.get_bind(), checkfirst=True)
