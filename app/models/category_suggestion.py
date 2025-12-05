from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.database import Base
import uuid
from datetime import datetime


class CategorySuggestion(Base):
    __tablename__ = "category_suggestions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    suggestion_type = Column(String(50), nullable=False)  # 'primary_category' | 'subcategory'
    primary_category = Column(String(255), nullable=True)  # Only for subcategory suggestions
    suggested_name = Column(String(255), nullable=False)
    reason = Column(Text, nullable=False)
    suggested_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("eden_assets.id"), nullable=True)
    status = Column(String(50), nullable=False, default="pending")
    admin_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Relationships
    suggested_by = relationship("User", foreign_keys=[suggested_by_user_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_user_id])
    asset = relationship("EdenAsset", foreign_keys=[asset_id])
