"""User database model for authentication."""

from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Index
from sqlalchemy.sql import func
import uuid

from webapp.app.database import Base


class User(Base):
    """SQLAlchemy model for user accounts."""

    __tablename__ = "users"

    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Authentication
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)

    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    # Optional link to existing access token
    linked_token = Column(String(64), nullable=True)

    # Indexes
    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_linked_token", "linked_token"),
    )

    def to_dict(self) -> dict:
        """Convert user to dictionary for API response."""
        return {
            "id": self.id,
            "email": self.email,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "linked_token": self.linked_token,
        }
