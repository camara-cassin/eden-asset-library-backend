import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID

from app.db.database import Base


class UserRole(str, Enum):
    admin = "admin"
    contributor = "contributor"
    viewer = "viewer"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.contributor)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
