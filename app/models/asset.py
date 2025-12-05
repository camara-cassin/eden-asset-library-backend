import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Index, Text, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import TypeDecorator

from app.db.database import Base


class JSONBType(TypeDecorator):
    """A type that uses JSONB on PostgreSQL and JSON on other databases."""
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())


class EdenAsset(Base):
    __tablename__ = "eden_assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id = Column(String(255), unique=True, nullable=False, index=True)
    asset_type = Column(String(50), nullable=False, index=True)
    status = Column(String(50), nullable=False, index=True, default="draft")
    submission_status = Column(String(50), nullable=True, index=True)
    category = Column(String(255), nullable=True, index=True)
    scaling_potential = Column(String(50), nullable=True, index=True)
    company_name = Column(String(255), nullable=True, index=True)
    creator_name = Column(String(255), nullable=True, index=True)
    contributor_id = Column(String(255), nullable=True, index=True)
    data = Column(JSONBType, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(String(255), nullable=True)  # User ID or email of creator
    updated_by = Column(String(255), nullable=True)  # User ID or email of last updater
